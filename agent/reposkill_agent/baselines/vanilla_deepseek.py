"""Vanilla DeepSeek / OpenAI-compatible single-shot LLM baseline (L0-style)."""

from __future__ import annotations

import os
import shutil
import time
import uuid

from reposkill_agent.baselines.contracts import BaselineRunRequest, BaselineRunResult


class VanillaDeepSeekBaseline:
    """Single inspect + LLM patch + test baseline using ModelClient."""

    name = "vanilla_deepseek"

    def __init__(self, model_client=None) -> None:
        self._model_client = model_client

    def is_available(self) -> tuple[bool, str]:
        if self._model_client is not None:
            return True, ""
        if not os.environ.get("LLM_API_KEY", "").strip():
            return False, "LLM_API_KEY not set; use mock client in tests or export key locally"
        return True, ""

    def run(self, request: BaselineRunRequest) -> BaselineRunResult:
        from reposkill_agent.llm.client import (
            LLMConfig,
            MissingLLMConfigError,
            ModelClient,
        )

        available, reason = self.is_available()
        if not available:
            return BaselineRunResult(
                name=self.name,
                task_id=request.task_id,
                status="skipped",
                skip_reason=reason,
            )

        from reposkill_agent.adapters.fake_adapter import FakeAdapter
        from reposkill_agent.agents import AgentContext, LLMDeveloperAgent
        from reposkill_agent.core.contracts import TaskSpec
        from reposkill_agent.core.task_graph import TaskNode
        from reposkill_agent.eval.scripted_fixes import SCRIPTED_FIXES

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
            adapter = FakeAdapter(
                workspace,
                scripted_fixes=SCRIPTED_FIXES,
                allow_prefix_scripted_fixes=False,
            )
            adapter.inspect_repo(task)

            client = self._model_client
            if client is None:
                client = ModelClient(LLMConfig.from_env(require_key=True))

            llm_state: dict[str, object] = {}
            developer = LLMDeveloperAgent(
                client,
                max_calls_per_task=2,
                call_state=llm_state,
            )
            patch_node = TaskNode(
                id="patch",
                goal="apply llm patch",
                owner="developer",
                expected_artifact="PatchResult list",
            )
            context = AgentContext(task=task, node=patch_node)
            patch_result = developer.run(context, adapter)
            test_result = adapter.run_tests(request.test_command)
            wall_time_ms = (time.perf_counter() - started) * 1000
            llm_metrics = patch_result.payload.get("llm_metrics", {})
            llm_calls = int(llm_metrics.get("llm_call_count", 0))

            result = BaselineRunResult(
                name=self.name,
                task_id=request.task_id,
                status="success" if test_result.passed else "failure",
                test_passed=test_result.passed,
                wall_time_ms=wall_time_ms,
                llm_calls=llm_calls,
                diff_summary=adapter.produce_diff()[:500],
                report_path=str(report_path),
                stderr_preview=(test_result.stderr or "")[-1000:],
            )
            report_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
            return result
        except MissingLLMConfigError as exc:
            return BaselineRunResult(
                name=self.name,
                task_id=request.task_id,
                status="skipped",
                skip_reason=str(exc),
                wall_time_ms=(time.perf_counter() - started) * 1000,
                report_path=str(report_path),
            )
        except OSError as exc:
            return BaselineRunResult(
                name=self.name,
                task_id=request.task_id,
                status="error",
                skip_reason=str(exc),
                wall_time_ms=(time.perf_counter() - started) * 1000,
                report_path=str(report_path),
            )
