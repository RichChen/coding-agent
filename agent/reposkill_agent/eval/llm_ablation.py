"""LLM mechanism ablation runner (L0-L5)."""

from __future__ import annotations

import json
import random
import shutil
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean, pstdev

from reposkill_agent.agents import AgentContext, LLMDeveloperAgent
from reposkill_agent.core.contracts import GraphMetrics, TaskSpec
from reposkill_agent.core.task_graph import TaskNode
from reposkill_agent.core.trace import TraceWriter
from reposkill_agent.eval.graph_runner import TaskGraphRunner
from reposkill_agent.eval.injection_policy import memory_warmup_tasks_for_eval
from reposkill_agent.eval.task_category import task_category
from reposkill_agent.eval.task_spec import TaskCatalog
from reposkill_agent.llm.client import MockModelClient, ModelClientProtocol


@dataclass(frozen=True)
class LLMAblationConfig:
    """One LLM ablation configuration."""

    name: str
    planner: bool
    multi_agent: bool
    skill: bool
    memory: bool
    developer: str = "llm"


LLM_CONFIGS = [
    LLMAblationConfig("L0_llm_single", planner=False, multi_agent=False, skill=False, memory=False),
    LLMAblationConfig("L1_llm_planner", planner=True, multi_agent=False, skill=False, memory=False),
    LLMAblationConfig("L2_llm_multi", planner=True, multi_agent=True, skill=False, memory=False),
    LLMAblationConfig("L3_llm_skill", planner=True, multi_agent=True, skill=True, memory=False),
    LLMAblationConfig("L4_llm_memory", planner=True, multi_agent=True, skill=False, memory=True),
    LLMAblationConfig("L5_llm_full", planner=True, multi_agent=True, skill=True, memory=True),
]


class LLMAblationRunner:
    """Run L0-L5 LLM ablations with isolated output directories."""

    def __init__(
        self,
        output_root: Path,
        model_client: ModelClientProtocol,
        *,
        seed: int = 42,
        seed_memory: bool = False,
        max_llm_calls_per_task: int = 3,
    ) -> None:
        self.output_root = output_root
        self.model_client = model_client
        self.seed = seed
        self.seed_memory = seed_memory
        self.max_llm_calls_per_task = max_llm_calls_per_task
        self.run_id = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        self.run_dir = self.output_root / self.run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)

    def run(
        self,
        catalog: TaskCatalog,
        *,
        repeats: int = 1,
        limit: int | None = None,
        config_names: list[str] | None = None,
        full_catalog: TaskCatalog | None = None,
        include_tags: list[str] | None = None,
    ) -> dict:
        tasks = list(catalog.tasks)
        if include_tags:
            required = set(include_tags)
            tasks = [task for task in tasks if required.issubset(set(task.tags))]
        if limit is not None:
            tasks = tasks[:limit]
        limited_catalog = TaskCatalog(tasks=tasks)
        full_catalog_tasks = list((full_catalog or limited_catalog).tasks)
        configs = LLM_CONFIGS
        if config_names:
            allowed = set(config_names)
            configs = [cfg for cfg in LLM_CONFIGS if cfg.name in allowed]
            missing = allowed - {cfg.name for cfg in configs}
            if missing:
                raise ValueError(f"Unknown LLM ablation config(s): {sorted(missing)}")
        results: dict[str, dict] = {}
        for config in configs:
            config_dir = self.run_dir / config.name
            trace_dir = config_dir / "traces"
            memory_dir = config_dir / "memory"
            config_dir.mkdir(parents=True, exist_ok=True)
            all_rows: list[dict] = []
            repeat_aggregates: list[dict] = []
            for repeat_idx in range(repeats):
                repeat_memory_dir = (
                    memory_dir / "seed" if self.seed_memory else memory_dir / f"repeat_{repeat_idx}"
                )
                rows = self._run_once(
                    config=config,
                    catalog=limited_catalog,
                    full_catalog_tasks=full_catalog_tasks,
                    trace_dir=trace_dir / f"repeat_{repeat_idx}",
                    memory_dir=repeat_memory_dir,
                    repeat_idx=repeat_idx,
                )
                all_rows.extend(rows)
                repeat_aggregates.append(self._aggregate(rows))
            results[config.name] = {
                "config": {
                    "planner": config.planner,
                    "multi_agent": config.multi_agent,
                    "skill": config.skill,
                    "memory": config.memory,
                    "developer": config.developer,
                },
                "rows": all_rows,
                "aggregate": self._aggregate(all_rows),
                "repeat_aggregates": repeat_aggregates,
                "variance": self._variance(repeat_aggregates),
            }
            (config_dir / "rows.json").write_text(
                json.dumps(all_rows, indent=2),
                encoding="utf-8",
            )
        summary = {
            "run_id": self.run_id,
            "generated_at": datetime.now(UTC).isoformat(),
            "task_count": len(tasks),
            "repeats": repeats,
            "seed": self.seed,
            "seed_memory": self.seed_memory,
            "max_llm_calls_per_task": self.max_llm_calls_per_task,
            "include_tags": include_tags or [],
            "eval_layer": "llm_mechanism",
            "protocol_mode": "diagnostic_oracle",
            "mock_llm": isinstance(self.model_client, MockModelClient),
            "results": results,
        }
        (self.run_dir / "llm-ablation-summary.json").write_text(
            json.dumps(summary, indent=2),
            encoding="utf-8",
        )
        return summary

    def _run_once(
        self,
        *,
        config: LLMAblationConfig,
        catalog: TaskCatalog,
        full_catalog_tasks: list[TaskSpec],
        trace_dir: Path,
        memory_dir: Path,
        repeat_idx: int,
    ) -> list[dict]:
        rows: list[dict] = []
        rng = random.Random(self.seed + repeat_idx)
        tasks = list(catalog.tasks)
        rng.shuffle(tasks)
        if config.name == "L0_llm_single":
            for task in tasks:
                run = self._run_llm_single(task, trace_dir=trace_dir)
                rows.append(self._row_from_metrics(task, run))
            return rows

        graph_runner = TaskGraphRunner(
            adapter="fake",
            trace_dir=trace_dir,
            use_skills=config.skill,
            use_memory=config.memory,
            memory_dir=memory_dir,
            execution_mode="single_graph" if config.name == "L1_llm_planner" else "role_agents",
            allow_prefix_scripted_fixes=False,
            developer_mode="llm",
            model_client=self.model_client,
            max_llm_calls_per_task=self.max_llm_calls_per_task,
        )
        if config.memory:
            warmup = memory_warmup_tasks_for_eval(tasks, full_catalog_tasks)
            for task in warmup:
                graph_runner.run(task)
        for task in tasks:
            run = graph_runner.run(task)
            rows.append(self._row_from_graph(task, run))
        return rows

    def _run_llm_single(self, task: TaskSpec, trace_dir: Path) -> GraphMetrics:
        run_id = uuid.uuid4().hex[:12]
        trace_path = trace_dir / f"{task.id}_llm_single_{run_id}.jsonl"
        trace = TraceWriter(trace_path, run_id=run_id, task_id=task.id)
        workspace = trace_dir / "workspaces" / f"{task.id}_{run_id}"
        if workspace.exists():
            shutil.rmtree(workspace)
        shutil.copytree(task.repo_path, workspace)
        from reposkill_agent.adapters.fake_adapter import FakeAdapter
        from reposkill_agent.eval.scripted_fixes import SCRIPTED_FIXES

        adapter = FakeAdapter(
            workspace,
            scripted_fixes=SCRIPTED_FIXES,
            allow_prefix_scripted_fixes=False,
        )
        started = time.perf_counter()
        trace.emit("run_start", {"task_id": task.id, "mode": "llm_single",
                                 "protocol_mode": "diagnostic_oracle"})
        adapter.inspect_repo(task)
        llm_state: dict[str, object] = {}
        developer = LLMDeveloperAgent(
            self.model_client,
            max_calls_per_task=self.max_llm_calls_per_task,
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
        trace.emit(
            "action",
            {
                "patch_strategy": patch_result.payload.get("patch_strategy"),
                "llm_metrics": patch_result.payload.get("llm_metrics", {}),
                "patch_plan_summary": patch_result.payload.get("patch_plan_summary", ""),
            },
            agent_role="developer",
        )
        test_result = adapter.run_tests(task.test_command)
        trace.emit("test", test_result.model_dump(), agent_role="qa")
        wall_time_ms = (time.perf_counter() - started) * 1000
        llm_metrics = patch_result.payload.get("llm_metrics", {})
        extra = {
            "protocol_mode": "diagnostic_oracle",
            "developer_mode": "llm",
            "role_handoff_count": 0,
            "agent_roles_used": ["developer"],
            **{k: llm_metrics.get(k, 0) for k in (
                "llm_call_count",
                "llm_parse_error_count",
                "llm_patch_rejected_count",
                "llm_patch_applied_count",
                "llm_prompt_tokens_estimate",
                "llm_completion_tokens_estimate",
                "llm_wall_time_ms",
            )},
            "llm_error_type": llm_metrics.get("llm_error_type", ""),
        }
        metrics = GraphMetrics(
            task_id=task.id,
            success=test_result.passed,
            steps=2,
            wall_time_ms=wall_time_ms,
            replan_count=0,
            test_passed=test_result.passed,
            adapter=adapter.name,
            trace_path=str(trace_path),
            finished_at=datetime.now(UTC),
            extra=extra,
        )
        trace.emit("metric", metrics.model_dump(mode="json"), agent_role="manager")
        trace.emit("run_end", {"success": metrics.success}, agent_role="manager")
        return metrics

    @staticmethod
    def _injection_fields(extra: dict) -> dict:
        return {
            "skill_candidate_count": int(extra.get("skill_candidate_count", 0)),
            "skill_injected_count": int(extra.get("skill_injected_count", 0)),
            "skill_gated_count": int(extra.get("skill_gated_count", 0)),
            "memory_candidate_count": int(extra.get("memory_candidate_count", 0)),
            "memory_injected_count": int(extra.get("memory_injected_count", 0)),
            "context_expansion_count": int(extra.get("context_expansion_count", 0)),
            "allowed_path_added_count": int(extra.get("allowed_path_added_count", 0)),
            "needs_more_context_recovered_count": int(
                extra.get("needs_more_context_recovered_count", 0)
            ),
            "llm_parse_repair_attempt_total": int(extra.get("llm_parse_repair_attempt_total", 0)),
            "llm_parse_repair_success_total": int(extra.get("llm_parse_repair_success_total", 0)),
            "augmentation_policy": str(extra.get("augmentation_policy", "")),
            "skill_suppressed_by_policy": int(extra.get("skill_suppressed_by_policy", 0)),
            "memory_suppressed_by_policy": int(extra.get("memory_suppressed_by_policy", 0)),
        }

    @staticmethod
    def _row_from_graph(task: TaskSpec, run) -> dict:
        extra = run.metrics.extra
        return {
            "task_id": task.id,
            "category": task_category(task.tags),
            "success": run.metrics.success,
            "steps": run.metrics.steps,
            "wall_time_ms": run.metrics.wall_time_ms,
            "replan_count": run.metrics.replan_count,
            "llm_call_count": int(extra.get("llm_call_count", 0)),
            "llm_parse_error_count": int(extra.get("llm_parse_error_count", 0)),
            "llm_patch_rejected_count": int(extra.get("llm_patch_rejected_count", 0)),
            "llm_patch_applied_count": int(extra.get("llm_patch_applied_count", 0)),
            "llm_prompt_tokens_estimate": int(extra.get("llm_prompt_tokens_estimate", 0)),
            "llm_completion_tokens_estimate": int(extra.get("llm_completion_tokens_estimate", 0)),
            "llm_wall_time_ms": float(extra.get("llm_wall_time_ms", 0.0)),
            "llm_error_type": str(extra.get("llm_error_type", "")),
            "skill_negative_transfer_count": int(extra.get("skill_negative_transfer_count", 0)),
            "memory_useful_count": int(extra.get("memory_useful_count", 0)),
            **LLMAblationRunner._injection_fields(extra),
            "failure_type": LLMAblationRunner._infer_failure_type(
                success=run.metrics.success,
                exit_code=run.test_result.exit_code,
                diff=run.diff,
            ),
        }

    @staticmethod
    def _row_from_metrics(task: TaskSpec, metrics: GraphMetrics) -> dict:
        extra = metrics.extra
        return {
            "task_id": task.id,
            "category": task_category(task.tags),
            "success": metrics.success,
            "steps": metrics.steps,
            "wall_time_ms": metrics.wall_time_ms,
            "replan_count": metrics.replan_count,
            "llm_call_count": int(extra.get("llm_call_count", 0)),
            "llm_parse_error_count": int(extra.get("llm_parse_error_count", 0)),
            "llm_patch_rejected_count": int(extra.get("llm_patch_rejected_count", 0)),
            "llm_patch_applied_count": int(extra.get("llm_patch_applied_count", 0)),
            "llm_prompt_tokens_estimate": int(extra.get("llm_prompt_tokens_estimate", 0)),
            "llm_completion_tokens_estimate": int(extra.get("llm_completion_tokens_estimate", 0)),
            "llm_wall_time_ms": float(extra.get("llm_wall_time_ms", 0.0)),
            "llm_error_type": str(extra.get("llm_error_type", "")),
            "skill_negative_transfer_count": 0,
            "memory_useful_count": 0,
            **LLMAblationRunner._injection_fields(extra),
            "failure_type": LLMAblationRunner._infer_failure_type(
                success=metrics.success,
                exit_code=0 if metrics.success else 1,
                diff="",
            ),
        }

    @staticmethod
    def _aggregate(rows: list[dict]) -> dict:
        if not rows:
            return {}
        success_flags = [1 if row["success"] else 0 for row in rows]
        return {
            "success_rate": mean(success_flags),
            "avg_steps": mean(row["steps"] for row in rows),
            "avg_wall_time_ms": mean(row["wall_time_ms"] for row in rows),
            "avg_replan_count": mean(row["replan_count"] for row in rows),
            "llm_call_total": sum(row["llm_call_count"] for row in rows),
            "llm_parse_error_total": sum(row["llm_parse_error_count"] for row in rows),
            "llm_patch_rejected_total": sum(row["llm_patch_rejected_count"] for row in rows),
            "llm_patch_applied_total": sum(row["llm_patch_applied_count"] for row in rows),
            "llm_prompt_tokens_total": sum(row["llm_prompt_tokens_estimate"] for row in rows),
            "llm_completion_tokens_total": sum(
                row["llm_completion_tokens_estimate"] for row in rows
            ),
            "llm_wall_time_ms_total": sum(row["llm_wall_time_ms"] for row in rows),
            "skill_negative_transfer_total": sum(
                row["skill_negative_transfer_count"] for row in rows
            ),
            "memory_useful_total": sum(row["memory_useful_count"] for row in rows),
            "skill_candidate_total": sum(row["skill_candidate_count"] for row in rows),
            "skill_injected_total": sum(row["skill_injected_count"] for row in rows),
            "skill_gated_total": sum(row["skill_gated_count"] for row in rows),
            "memory_candidate_total": sum(row["memory_candidate_count"] for row in rows),
            "memory_injected_total": sum(row["memory_injected_count"] for row in rows),
            "context_expansion_total": sum(row["context_expansion_count"] for row in rows),
            "allowed_path_added_total": sum(row["allowed_path_added_count"] for row in rows),
            "needs_more_context_recovered_total": sum(
                row["needs_more_context_recovered_count"] for row in rows
            ),
            "llm_parse_repair_attempt_total": sum(
                row["llm_parse_repair_attempt_total"] for row in rows
            ),
            "llm_parse_repair_success_total": sum(
                row["llm_parse_repair_success_total"] for row in rows
            ),
            "skill_suppressed_by_policy_total": sum(
                row["skill_suppressed_by_policy"] for row in rows
            ),
            "memory_suppressed_by_policy_total": sum(
                row["memory_suppressed_by_policy"] for row in rows
            ),
            "failure_taxonomy_distribution": LLMAblationRunner._failure_distribution(rows),
            "by_category": LLMAblationRunner._aggregate_by_category(rows),
        }

    @staticmethod
    def _variance(repeat_aggregates: list[dict]) -> dict:
        if len(repeat_aggregates) <= 1:
            return {
                "success_rate_std": 0.0,
                "avg_steps_std": 0.0,
                "avg_replan_count_std": 0.0,
            }
        return {
            "success_rate_std": pstdev(item["success_rate"] for item in repeat_aggregates),
            "avg_steps_std": pstdev(item["avg_steps"] for item in repeat_aggregates),
            "avg_replan_count_std": pstdev(item["avg_replan_count"] for item in repeat_aggregates),
        }

    @staticmethod
    def _infer_failure_type(*, success: bool, exit_code: int, diff: str) -> str:
        if success:
            return "success"
        if exit_code != 0:
            return "test_failure"
        if not diff:
            return "patch_missing"
        return "unknown"

    @staticmethod
    def _failure_distribution(rows: list[dict]) -> dict[str, int]:
        out: dict[str, int] = {}
        for row in rows:
            name = row.get("failure_type", "unknown")
            out[name] = out.get(name, 0) + 1
        return out

    @staticmethod
    def _task_category(tags: list[str]) -> str:
        return task_category(tags)

    @staticmethod
    def _aggregate_by_category(rows: list[dict]) -> dict[str, dict]:
        grouped: dict[str, list[dict]] = {}
        for row in rows:
            grouped.setdefault(row.get("category", "other"), []).append(row)
        out: dict[str, dict] = {}
        for category, items in grouped.items():
            success_flags = [1 if item["success"] else 0 for item in items]
            failure_dist = LLMAblationRunner._failure_distribution(items)
            main_failure = max(failure_dist, key=failure_dist.get)
            out[category] = {
                "tasks": len(items),
                "success_rate": mean(success_flags),
                "avg_steps": mean(item["steps"] for item in items),
                "main_failure": main_failure,
            }
        return out
