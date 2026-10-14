"""OpenHands SDK adapter — wraps SDK behind the unified WorkspaceAdapter interface."""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

from reposkill_agent.adapters.base import WorkspaceAdapter
from reposkill_agent.core.contracts import (
    CommandResult,
    PatchResult,
    PatchSpec,
    RepoInspection,
    TaskSpec,
    TestResult,
)


class OpenHandsAdapter(WorkspaceAdapter):
    """Adapter that delegates agent execution to OpenHands SDK when available.

    File/command operations use local subprocess for determinism.
    Agent-driven task solving uses ``Conversation`` when ``LLM_API_KEY`` is set.
    """

    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root.resolve()
        self._snapshots: dict[str, str] = {}
        self._snapshot_workspace()
        self._conversation = None
        self._agent = None

    @property
    def name(self) -> str:
        return "openhands"

    @staticmethod
    def is_available() -> bool:
        """Return True if OpenHands SDK is installed and API key is configured."""
        try:
            import openhands.sdk  # noqa: F401
        except ImportError:
            return False
        return bool(os.getenv("LLM_API_KEY"))

    def _snapshot_workspace(self) -> None:
        self._snapshots.clear()
        if not self.workspace_root.exists():
            return
        skip_suffixes = {".pdf", ".png", ".jpg", ".jpeg", ".gif", ".zip", ".pyc"}
        for path in self.workspace_root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() in skip_suffixes or "__pycache__" in path.parts:
                continue
            try:
                rel = path.relative_to(self.workspace_root).as_posix()
                self._snapshots[rel] = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue

    def _ensure_agent(self) -> None:
        if self._agent is not None:
            return
        from openhands.sdk import LLM, Agent, Conversation, Tool
        from openhands.tools.file_editor import FileEditorTool
        from openhands.tools.terminal import TerminalTool

        llm = LLM(
            model=os.getenv("LLM_MODEL", "anthropic/claude-sonnet-4-5-20250929"),
            api_key=os.getenv("LLM_API_KEY"),
            base_url=os.getenv("LLM_BASE_URL"),
        )
        self._agent = Agent(
            llm=llm,
            tools=[
                Tool(name=TerminalTool.name),
                Tool(name=FileEditorTool.name),
            ],
        )
        self._conversation = Conversation(
            agent=self._agent,
            workspace=str(self.workspace_root),
        )

    def inspect_repo(self, task: TaskSpec) -> RepoInspection:
        repo_path = self.workspace_root
        entries = sorted(p.name for p in repo_path.iterdir()) if repo_path.exists() else []
        file_count = (
            sum(1 for _ in repo_path.rglob("*") if _.is_file()) if repo_path.exists() else 0
        )
        return RepoInspection(
            task_id=task.id,
            repo_path=str(repo_path),
            file_count=file_count,
            top_level_entries=entries,
            test_command=task.test_command,
            notes=[f"issue: {task.issue}", f"adapter: {self.name}"],
        )

    def run_command(self, command: str) -> CommandResult:
        start = time.perf_counter()
        completed = subprocess.run(
            command,
            shell=True,
            cwd=self.workspace_root,
            capture_output=True,
            text=True,
        )
        duration_ms = (time.perf_counter() - start) * 1000
        return CommandResult(
            command=command,
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            duration_ms=duration_ms,
        )

    def apply_patch(self, patch: PatchSpec) -> PatchResult:
        target = self.workspace_root / patch.path
        target.parent.mkdir(parents=True, exist_ok=True)
        if patch.mode == "append" and target.exists():
            existing = target.read_text(encoding="utf-8")
            target.write_text(existing + patch.content, encoding="utf-8")
        else:
            target.write_text(patch.content, encoding="utf-8")
        return PatchResult(path=patch.path, applied=True, message="patch applied")

    def read_file(self, path: str) -> str:
        target = self.workspace_root / path
        if not target.exists():
            raise FileNotFoundError(path)
        return target.read_text(encoding="utf-8")

    def list_files(self, pattern: str = "**/*") -> list[str]:
        import fnmatch

        if not self.workspace_root.exists():
            return []
        results: list[str] = []
        for path in self.workspace_root.rglob("*"):
            if path.is_file():
                rel = path.relative_to(self.workspace_root).as_posix()
                if fnmatch.fnmatch(rel, pattern) or fnmatch.fnmatch(path.name, pattern):
                    results.append(rel)
        return sorted(results)

    def run_tests(self, test_command: str) -> TestResult:
        adjusted_command = self._normalize_test_command(test_command)
        cmd = self.run_command(adjusted_command)
        return TestResult(
            command=adjusted_command,
            passed=cmd.exit_code == 0,
            exit_code=cmd.exit_code,
            stdout=cmd.stdout,
            stderr=cmd.stderr,
            duration_ms=cmd.duration_ms,
        )

    def produce_diff(self) -> str:
        lines: list[str] = []
        current = self._collect_text_files()

        for rel in sorted(set(self._snapshots) | set(current)):
            before = self._snapshots.get(rel)
            after = current.get(rel)
            if before == after:
                continue
            lines.append(f"--- a/{rel}")
            lines.append(f"+++ b/{rel}")
            if before is None:
                lines.append("@@ new file @@")
                lines.extend(f"+{line}" for line in (after or "").splitlines())
            elif after is None:
                lines.append("@@ deleted @@")
                lines.extend(f"-{line}" for line in before.splitlines())
            else:
                lines.append("@@ modified @@")
                for bline, aline in zip(before.splitlines(), after.splitlines(), strict=False):
                    if bline != aline:
                        lines.append(f"-{bline}")
                        lines.append(f"+{aline}")
        return "\n".join(lines)

    def _collect_text_files(self) -> dict[str, str]:
        skip_suffixes = {".pdf", ".png", ".jpg", ".jpeg", ".gif", ".zip", ".pyc"}
        current: dict[str, str] = {}
        for path in self.workspace_root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() in skip_suffixes or "__pycache__" in path.parts:
                continue
            try:
                rel = path.relative_to(self.workspace_root).as_posix()
                current[rel] = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
        return current

    def run_agent_task(self, issue: str) -> dict[str, str]:
        """Use OpenHands agent to solve a task described by *issue*.

        Requires ``LLM_API_KEY``. Returns a summary dict for tracing.
        """
        if not self.is_available():
            raise RuntimeError(
                "OpenHands SDK not available or LLM_API_KEY not set. "
                "Install with: pip install 'reposkill-agent[openhands]'"
            )
        self._ensure_agent()
        assert self._conversation is not None
        self._conversation.send_message(issue)
        self._conversation.run()
        return {"status": "completed", "issue": issue}

    @staticmethod
    def _normalize_test_command(command: str) -> str:
        if "pytest" in command:
            normalized = command
            if "cache_dir=" not in normalized:
                normalized = f"{normalized} -o cache_dir=.pytest_cache"
            if "--basetemp=" not in normalized:
                normalized = f"{normalized} --basetemp=.pytest_tmp"
            if "no:cacheprovider" not in normalized:
                normalized = f"{normalized} -p no:cacheprovider"
            return normalized
        return command
