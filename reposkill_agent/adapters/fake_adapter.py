"""Deterministic fake adapter for unit tests and offline runs."""

from __future__ import annotations

import fnmatch
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


class FakeAdapter(WorkspaceAdapter):
    """In-memory + filesystem adapter with scripted fixes for benchmark tasks.

    For known task IDs it applies predefined patches so tests pass without an LLM.
    """

    def __init__(
        self,
        workspace_root: Path,
        scripted_fixes: dict[str, list[PatchSpec]] | None = None,
        allow_prefix_scripted_fixes: bool = True,
    ) -> None:
        self.workspace_root = workspace_root.resolve()
        self._scripted_fixes = scripted_fixes or {}
        self.allow_prefix_scripted_fixes = allow_prefix_scripted_fixes
        self._snapshots: dict[str, str] = {}
        self._snapshot_workspace()

    @property
    def name(self) -> str:
        return "fake"

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
            notes=[f"issue: {task.issue}"],
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
        if not self.workspace_root.exists():
            return ""
        current = self._collect_text_files()
        all_paths = sorted(set(self._snapshots) | set(current))
        for rel in all_paths:
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
                if len(before.splitlines()) > len(after.splitlines()):
                    for bline in before.splitlines()[len(after.splitlines()) :]:
                        lines.append(f"-{bline}")
                elif len(after.splitlines()) > len(before.splitlines()):
                    for aline in after.splitlines()[len(before.splitlines()) :]:
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

    def apply_scripted_fix(self, task_id: str) -> list[PatchResult]:
        """Apply predefined patches for a benchmark task, if any."""
        patches = self._scripted_fixes.get(task_id, [])
        if not patches and self.allow_prefix_scripted_fixes:
            for key, value in self._scripted_fixes.items():
                if task_id.startswith(f"{key}_"):
                    patches = value
                    break
        return [self.apply_patch(patch) for patch in patches]

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
