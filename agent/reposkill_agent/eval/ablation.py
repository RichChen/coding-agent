"""Phase 6 ablation runner for A0-A5 configurations."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean, pstdev

from reposkill_agent.eval.graph_runner import TaskGraphRunner
from reposkill_agent.eval.runner import BaselineRunner
from reposkill_agent.eval.task_category import task_category
from reposkill_agent.eval.task_spec import TaskCatalog


@dataclass(frozen=True)
class AblationConfig:
    """One ablation experiment configuration."""

    name: str
    planner: bool
    multi_agent: bool
    skill: bool
    memory: bool


PHASE6_CONFIGS = [
    AblationConfig("A0_baseline", planner=False, multi_agent=False, skill=False, memory=False),
    AblationConfig("A1_planner", planner=True, multi_agent=False, skill=False, memory=False),
    AblationConfig("A2_multi_agent", planner=True, multi_agent=True, skill=False, memory=False),
    AblationConfig("A3_skill", planner=True, multi_agent=True, skill=True, memory=False),
    AblationConfig("A4_memory", planner=True, multi_agent=True, skill=False, memory=True),
    AblationConfig("A5_full", planner=True, multi_agent=True, skill=True, memory=True),
]


class AblationRunner:
    """Run all ablation configs with isolated run directories."""

    def __init__(
        self,
        output_root: Path,
        adapter: str = "fake",
        seed_memory: bool = False,
        seed: int = 42,
    ) -> None:
        self.output_root = output_root
        self.adapter = adapter
        self.seed_memory = seed_memory
        self.seed = seed
        self.run_id = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        self.run_dir = self.output_root / self.run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)

    def run(self, catalog: TaskCatalog, repeats: int = 1) -> dict:
        results: dict[str, dict] = {}
        hard_mode = self._is_hard_catalog(catalog)
        for config in PHASE6_CONFIGS:
            config_dir = self.run_dir / config.name
            trace_dir = config_dir / "traces"
            memory_dir = config_dir / "memory"
            config_dir.mkdir(parents=True, exist_ok=True)
            all_rows: list[dict] = []
            repeat_aggregates: list[dict] = []
            for repeat_idx in range(repeats):
                repeat_memory_dir = (
                    memory_dir / "seed"
                    if self.seed_memory
                    else memory_dir / f"repeat_{repeat_idx}"
                )
                rows = self._run_once(
                    config=config,
                    catalog=catalog,
                    trace_dir=trace_dir / f"repeat_{repeat_idx}",
                    memory_dir=repeat_memory_dir,
                    repeat_idx=repeat_idx,
                    hard_mode=hard_mode,
                )
                all_rows.extend(rows)
                repeat_aggregates.append(self._aggregate(rows))
            results[config.name] = {
                "config": {
                    "planner": config.planner,
                    "multi_agent": config.multi_agent,
                    "skill": config.skill,
                    "memory": config.memory,
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
            "task_count": len(catalog.tasks),
            "repeats": repeats,
            "seed": self.seed,
            "seed_memory": self.seed_memory,
            "hard_mode": hard_mode,
            "protocol_mode": "diagnostic_oracle",
            "results": results,
        }
        (self.run_dir / "ablation-summary.json").write_text(
            json.dumps(summary, indent=2),
            encoding="utf-8",
        )
        return summary

    def _run_once(
        self,
        *,
        config: AblationConfig,
        catalog: TaskCatalog,
        trace_dir: Path,
        memory_dir: Path,
        repeat_idx: int,
        hard_mode: bool,
    ) -> list[dict]:
        rows: list[dict] = []
        rng = random.Random(self.seed + repeat_idx)
        tasks = list(catalog.tasks)
        rng.shuffle(tasks)
        if config.name == "A0_baseline":
            runner = BaselineRunner(
                adapter=self.adapter,
                trace_dir=trace_dir,
                allow_prefix_scripted_fixes=not hard_mode,
            )
            for task in tasks:
                run = runner.run(task)
                category = self._task_category(task.tags)
                rows.append(
                    {
                        "task_id": task.id,
                        "category": category,
                        "success": run.metrics.success,
                        "steps": run.metrics.steps,
                        "wall_time_ms": run.metrics.wall_time_ms,
                        "replan_count": 0,
                        "skill_negative_transfer_count": 0,
                        "memory_retrieval_count": 0,
                        "memory_useful_count": 0,
                        "memory_stale_or_wrong_count": 0,
                        "role_handoff_count": 0,
                        "agent_roles_used": ["single_agent"],
                        "failure_type": self._infer_failure_type(
                            success=run.metrics.success,
                            exit_code=run.test_result.exit_code,
                            diff=run.diff,
                        ),
                    }
                )
            return rows

        graph_runner = TaskGraphRunner(
            adapter=self.adapter,
            trace_dir=trace_dir,
            use_skills=config.skill,
            use_memory=config.memory,
            memory_dir=memory_dir,
            execution_mode=(
                "single_graph" if config.name == "A1_planner" else "role_agents"
            ),
            allow_prefix_scripted_fixes=not hard_mode,
        )
        for task in tasks:
            run = graph_runner.run(task)
            category = self._task_category(task.tags)
            rows.append(
                {
                    "task_id": task.id,
                    "category": category,
                    "success": run.metrics.success,
                    "steps": run.metrics.steps,
                    "wall_time_ms": run.metrics.wall_time_ms,
                    "replan_count": run.metrics.replan_count,
                    "skill_negative_transfer_count": int(
                        run.metrics.extra.get("skill_negative_transfer_count", 0)
                    ),
                    "memory_retrieval_count": int(
                        run.metrics.extra.get("memory_retrieval_count", 0)
                    ),
                    "memory_useful_count": int(run.metrics.extra.get("memory_useful_count", 0)),
                    "memory_stale_or_wrong_count": int(
                        run.metrics.extra.get("memory_stale_or_wrong_count", 0)
                    ),
                    "role_handoff_count": int(run.metrics.extra.get("role_handoff_count", 0)),
                    "agent_roles_used": list(run.metrics.extra.get("agent_roles_used", [])),
                    "failure_type": self._infer_failure_type(
                        success=run.metrics.success,
                        exit_code=run.test_result.exit_code,
                        diff=run.diff,
                    ),
                }
            )
        return rows

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
            "skill_negative_transfer_total": sum(
                row["skill_negative_transfer_count"] for row in rows
            ),
            "memory_retrieval_total": sum(row["memory_retrieval_count"] for row in rows),
            "memory_useful_total": sum(row["memory_useful_count"] for row in rows),
            "memory_stale_or_wrong_total": sum(
                row["memory_stale_or_wrong_count"] for row in rows
            ),
            "avg_role_handoff_count": mean(row["role_handoff_count"] for row in rows),
            "agent_roles_union": sorted(
                {
                    role
                    for row in rows
                    for role in row.get("agent_roles_used", [])
                }
            ),
            "failure_taxonomy_distribution": AblationRunner._failure_distribution(rows),
            "by_category": AblationRunner._aggregate_by_category(rows),
        }

    @staticmethod
    def _variance(repeat_aggregates: list[dict]) -> dict:
        if len(repeat_aggregates) <= 1:
            return {
                "success_rate_std": 0.0,
                "avg_steps_std": 0.0,
                "avg_wall_time_ms_std": 0.0,
                "avg_replan_count_std": 0.0,
            }
        return {
            "success_rate_std": pstdev(item["success_rate"] for item in repeat_aggregates),
            "avg_steps_std": pstdev(item["avg_steps"] for item in repeat_aggregates),
            "avg_wall_time_ms_std": pstdev(item["avg_wall_time_ms"] for item in repeat_aggregates),
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
            failure_dist = AblationRunner._failure_distribution(items)
            main_failure = max(failure_dist, key=failure_dist.get)
            out[category] = {
                "tasks": len(items),
                "success_rate": mean(success_flags),
                "avg_steps": mean(item["steps"] for item in items),
                "avg_replan_count": mean(item["replan_count"] for item in items),
                "failure_taxonomy_distribution": failure_dist,
                "main_failure": main_failure,
            }
        return out

    @staticmethod
    def _is_hard_catalog(catalog: TaskCatalog) -> bool:
        hard_tags = {"rename", "api", "regression", "traceback"}
        for task in catalog.tasks:
            if set(task.tags) & hard_tags:
                return True
        return False
