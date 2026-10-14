"""Single-agent baseline runner with structured output and JSONL tracing."""

from __future__ import annotations

import shutil
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from reposkill_agent.adapters.base import WorkspaceAdapter
from reposkill_agent.adapters.fake_adapter import FakeAdapter
from reposkill_agent.adapters.openhands_adapter import OpenHandsAdapter
from reposkill_agent.core.contracts import (
    BaselineMetrics,
    BaselineRunResult,
    TaskSpec,
)
from reposkill_agent.core.trace import TraceWriter
from reposkill_agent.eval.scripted_fixes import SCRIPTED_FIXES

AdapterKind = Literal["fake", "openhands"]


class BaselineRunner:
    """Run a single-agent baseline on a repo task.

    With ``fake`` adapter the runner applies scripted fixes (no LLM).
    With ``openhands`` adapter it delegates to the SDK when ``LLM_API_KEY`` is set.
    """

    def __init__(
        self,
        adapter: AdapterKind = "fake",
        trace_dir: Path | None = None,
        work_dir: Path | None = None,
        allow_prefix_scripted_fixes: bool = True,
    ) -> None:
        self.adapter_kind = adapter
        self.trace_dir = trace_dir or Path("traces")
        self.work_dir = work_dir or self.trace_dir / "workspaces"
        self.allow_prefix_scripted_fixes = allow_prefix_scripted_fixes

    def run(self, task: TaskSpec, use_agent: bool = False) -> BaselineRunResult:
        """Execute baseline for one task and return structured results."""
        run_id = uuid.uuid4().hex[:12]
        trace_path = self.trace_dir / f"{task.id}_{run_id}.jsonl"
        trace = TraceWriter(trace_path, run_id=run_id, task_id=task.id)

        workspace = self._prepare_workspace(task, run_id)
        adapter = self._bind_adapter(workspace)

        started = time.perf_counter()
        trace.emit("run_start", {"task_id": task.id, "adapter": adapter.name,
                                 "protocol_mode": "diagnostic_oracle"})

        inspection = adapter.inspect_repo(task)
        trace.emit("inspect", inspection.model_dump())

        actions: list[dict] = []
        steps = 0

        if use_agent and isinstance(adapter, OpenHandsAdapter) and OpenHandsAdapter.is_available():
            steps += 1
            agent_result = adapter.run_agent_task(task.issue)
            actions.append({"type": "agent_run", **agent_result})
            trace.emit("action", agent_result)
        else:
            steps += 1
            patch_results = []
            if isinstance(adapter, FakeAdapter):
                patch_results = adapter.apply_scripted_fix(task.id)
            else:
                fixes = SCRIPTED_FIXES.get(task.id, [])
                for patch in fixes:
                    patch_results.append(adapter.apply_patch(patch))
            for result in patch_results:
                actions.append({"type": "patch", **result.model_dump()})
                trace.emit("patch", result.model_dump())
                steps += 1

        test_result = adapter.run_tests(task.test_command)
        trace.emit("test", test_result.model_dump())

        diff = adapter.produce_diff()
        trace.emit("diff", {"diff": diff, "length": len(diff)})

        wall_time_ms = (time.perf_counter() - started) * 1000
        success = test_result.passed

        metrics = BaselineMetrics(
            task_id=task.id,
            success=success,
            steps=steps,
            wall_time_ms=wall_time_ms,
            token_estimate=0,
            cost_estimate_usd=0.0,
            test_passed=test_result.passed,
            adapter=adapter.name,
            trace_path=str(trace_path),
            finished_at=datetime.now(UTC),
            extra={"protocol_mode": "diagnostic_oracle"},
        )
        trace.emit("metric", metrics.model_dump(mode="json"))
        trace.emit("run_end", {"success": success})

        return BaselineRunResult(
            task=task,
            metrics=metrics,
            diff=diff,
            inspection=inspection,
            test_result=test_result,
            actions=actions,
        )

    def _prepare_workspace(self, task: TaskSpec, run_id: str) -> Path:
        dest = self.work_dir / f"{task.id}_{run_id}"
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(task.repo_path, dest)
        return dest

    def _bind_adapter(self, workspace: Path) -> WorkspaceAdapter:
        if self.adapter_kind == "fake":
            return FakeAdapter(
                workspace,
                scripted_fixes=SCRIPTED_FIXES,
                allow_prefix_scripted_fixes=self.allow_prefix_scripted_fixes,
            )
        return OpenHandsAdapter(workspace)
