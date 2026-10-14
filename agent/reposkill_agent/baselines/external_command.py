"""Generic external-command baseline runner with workspace isolation."""

from __future__ import annotations

import shutil
import subprocess
import time
import uuid
from collections.abc import Callable
from pathlib import Path

from reposkill_agent.baselines.contracts import BaselineRunRequest, BaselineRunResult


class ExternalCommandBaseline:
    """Run an external CLI in an isolated workspace copy, then execute tests."""

    def __init__(
        self,
        name: str,
        command_builder: Callable[..., str | list[str]],
        *,
        timeout_seconds: int = 300,
        availability_check: Callable[[], tuple[bool, str]] | None = None,
    ) -> None:
        self.name = name
        self.command_builder = command_builder
        self.timeout_seconds = timeout_seconds
        self.availability_check = availability_check

    def is_available(self) -> tuple[bool, str]:
        if self.availability_check is not None:
            return self.availability_check()
        return True, ""

    def run(self, request: BaselineRunRequest) -> BaselineRunResult:
        available, reason = self.is_available()
        if not available:
            return BaselineRunResult(
                name=self.name,
                task_id=request.task_id,
                status="skipped",
                skip_reason=reason,
            )

        run_id = uuid.uuid4().hex[:8]
        workspace = request.output_dir / "workspaces" / f"{request.task_id}_{run_id}"
        report_path = request.output_dir / "reports" / f"{self.name}_{request.task_id}.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)

        started = time.perf_counter()
        try:
            if workspace.exists():
                shutil.rmtree(workspace)
            shutil.copytree(request.repo_path, workspace)

            command = self.command_builder(workspace, request)
            proc = subprocess.run(
                command,
                shell=isinstance(command, str),
                cwd=workspace,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
            stdout_preview = proc.stdout[-2000:] if proc.stdout else ""
            stderr_preview = proc.stderr[-2000:] if proc.stderr else ""

            if proc.returncode != 0:
                wall_time_ms = (time.perf_counter() - started) * 1000
                result = BaselineRunResult(
                    name=self.name,
                    task_id=request.task_id,
                    status="error",
                    test_passed=False,
                    wall_time_ms=wall_time_ms,
                    diff_summary=_diff_summary(workspace),
                    report_path=str(report_path),
                    stdout_preview=stdout_preview,
                    stderr_preview=stderr_preview,
                    skip_reason=f"command exited {proc.returncode}",
                )
                report_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                return result

            test_proc = subprocess.run(
                request.test_command,
                shell=True,
                cwd=workspace,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
            wall_time_ms = (time.perf_counter() - started) * 1000
            test_passed = test_proc.returncode == 0
            status = "success" if test_passed else "failure"
            result = BaselineRunResult(
                name=self.name,
                task_id=request.task_id,
                status=status,
                test_passed=test_passed,
                wall_time_ms=wall_time_ms,
                diff_summary=_diff_summary(workspace),
                report_path=str(report_path),
                stdout_preview=stdout_preview,
                stderr_preview=(test_proc.stderr or "")[-2000:],
            )
            report_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
            return result
        except subprocess.TimeoutExpired:
            wall_time_ms = (time.perf_counter() - started) * 1000
            return BaselineRunResult(
                name=self.name,
                task_id=request.task_id,
                status="error",
                wall_time_ms=wall_time_ms,
                skip_reason=f"timeout after {self.timeout_seconds}s",
                report_path=str(report_path),
            )
        except OSError as exc:
            wall_time_ms = (time.perf_counter() - started) * 1000
            return BaselineRunResult(
                name=self.name,
                task_id=request.task_id,
                status="error",
                wall_time_ms=wall_time_ms,
                skip_reason=str(exc),
                report_path=str(report_path),
            )


def _diff_summary(workspace: Path) -> str:
    """Return a short summary of changed Python files (no secrets)."""
    changed: list[str] = []
    for path in sorted(workspace.rglob("*.py")):
        if "__pycache__" in path.parts or path.name == "conftest.py":
            continue
        rel = path.relative_to(workspace).as_posix()
        if rel.startswith("tests/"):
            continue
        changed.append(rel)
    if not changed:
        return "no_python_changes_detected"
    preview = changed[:8]
    suffix = f" (+{len(changed) - 8} more)" if len(changed) > 8 else ""
    return f"python_files_touched={len(changed)}: {', '.join(preview)}{suffix}"
