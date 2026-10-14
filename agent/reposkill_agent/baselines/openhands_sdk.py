"""Optional OpenHands SDK baseline — skip when SDK or API key unavailable."""

from __future__ import annotations

import os
import shutil
import time
import uuid

from reposkill_agent.baselines.contracts import BaselineRunRequest, BaselineRunResult


class OpenHandsSdkBaseline:
    """Run task via OpenHands SDK when installed; otherwise skip-with-reason."""

    name = "openhands_sdk"

    def is_available(self) -> tuple[bool, str]:
        try:
            import openhands.sdk  # noqa: F401
        except ImportError:
            return False, "openhands-sdk not installed (pip install reposkill-agent[openhands])"
        if not os.environ.get("LLM_API_KEY", "").strip():
            return False, "LLM_API_KEY not set for OpenHands SDK baseline"
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

        from reposkill_agent.adapters.openhands_adapter import OpenHandsAdapter
        from reposkill_agent.core.contracts import TaskSpec

        run_id = uuid.uuid4().hex[:8]
        workspace = request.output_dir / "workspaces" / f"{request.task_id}_{run_id}"
        report_path = request.output_dir / "reports" / f"{self.name}_{request.task_id}.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        started = time.perf_counter()

        try:
            if workspace.exists():
                shutil.rmtree(workspace)
            shutil.copytree(request.repo_path, workspace)

            task = TaskSpec(
                id=request.task_id,
                issue=request.issue,
                repo_path=str(workspace),
                test_command=request.test_command,
                expected_files=request.expected_files,
            )
            adapter = OpenHandsAdapter(workspace)
            adapter.inspect_repo(task)
            # Full agent solve is optional; baseline records inspect + test without scripted fix.
            test_result = adapter.run_tests(request.test_command)
            wall_time_ms = (time.perf_counter() - started) * 1000
            result = BaselineRunResult(
                name=self.name,
                task_id=request.task_id,
                status="success" if test_result.passed else "failure",
                test_passed=test_result.passed,
                wall_time_ms=wall_time_ms,
                diff_summary=adapter.produce_diff()[:500],
                report_path=str(report_path),
                stderr_preview=(test_result.stderr or "")[-1000:],
            )
            report_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
            return result
        except Exception as exc:
            return BaselineRunResult(
                name=self.name,
                task_id=request.task_id,
                status="error",
                skip_reason=str(exc)[:300],
                wall_time_ms=(time.perf_counter() - started) * 1000,
                report_path=str(report_path),
            )
