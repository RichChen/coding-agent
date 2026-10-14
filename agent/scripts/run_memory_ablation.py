#!/usr/bin/env python3
"""Run no-memory vs memory ablation on tiny tasks."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from reposkill_agent.eval.graph_runner import TaskGraphRunner
from reposkill_agent.eval.task_spec import load_tasks

ROOT = Path(__file__).resolve().parent.parent
TASKS_FILE = ROOT / "benchmarks" / "tasks" / "tiny_python_tasks.yaml"
BENCHMARKS_ROOT = ROOT / "benchmarks"
REPORTS_DIR = ROOT / "reports"


def _run_variant(use_memory: bool) -> list[dict]:
    catalog = load_tasks(TASKS_FILE, benchmarks_root=BENCHMARKS_ROOT)
    runner = TaskGraphRunner(
        adapter="fake",
        trace_dir=ROOT / "traces",
        use_skills=True,
        use_memory=use_memory,
        memory_dir=ROOT / "traces" / "memory",
    )
    results: list[dict] = []
    for task in catalog.tasks:
        run = runner.run(task)
        results.append(
            {
                "task_id": task.id,
                "success": run.metrics.success,
                "steps": run.metrics.steps,
                "wall_time_ms": run.metrics.wall_time_ms,
                "replan_count": run.metrics.replan_count,
                "skill_validated_count": int(run.metrics.extra.get("skill_validated_count", 0)),
                "skill_negative_transfer_count": int(
                    run.metrics.extra.get("skill_negative_transfer_count", 0)
                ),
                "memory_retrieval_count": int(run.metrics.extra.get("memory_retrieval_count", 0)),
                "memory_useful_count": int(run.metrics.extra.get("memory_useful_count", 0)),
                "memory_stale_or_wrong_count": int(
                    run.metrics.extra.get("memory_stale_or_wrong_count", 0)
                ),
            }
        )
    return results


def _aggregate(rows: list[dict]) -> dict:
    total = len(rows)
    success_count = sum(1 for row in rows if row["success"])
    return {
        "task_count": total,
        "success_rate": success_count / total if total else 0.0,
        "avg_steps": sum(row["steps"] for row in rows) / total if total else 0.0,
        "avg_wall_time_ms": sum(row["wall_time_ms"] for row in rows) / total if total else 0.0,
        "avg_replan_count": sum(row["replan_count"] for row in rows) / total if total else 0.0,
        "skill_validated_total": sum(row["skill_validated_count"] for row in rows),
        "skill_negative_transfer_total": sum(row["skill_negative_transfer_count"] for row in rows),
        "memory_retrieval_total": sum(row["memory_retrieval_count"] for row in rows),
        "memory_useful_total": sum(row["memory_useful_count"] for row in rows),
        "memory_stale_or_wrong_total": sum(row["memory_stale_or_wrong_count"] for row in rows),
    }


def _write_reports(payload: dict) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    json_path = REPORTS_DIR / "memory-ablation-summary.json"
    md_path = REPORTS_DIR / "memory-ablation-summary.md"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    no_mem = payload["variants"]["no_memory"]["aggregate"]
    with_mem = payload["variants"]["with_memory"]["aggregate"]
    lines = [
        "# Memory Ablation Summary",
        "",
        f"Generated at: {payload['generated_at']}",
        "",
        "## Variants",
        "",
        "- A: `use_memory=false` (no memory)",
        "- B: `use_memory=true` (with memory)",
        "",
        "## Aggregate Metrics",
        "",
        "| Metric | No Memory | With Memory |",
        "| --- | ---: | ---: |",
        f"| success_rate | {no_mem['success_rate']:.2f} | {with_mem['success_rate']:.2f} |",
        f"| avg_steps | {no_mem['avg_steps']:.2f} | {with_mem['avg_steps']:.2f} |",
        (
            f"| avg_wall_time_ms | {no_mem['avg_wall_time_ms']:.2f} | "
            f"{with_mem['avg_wall_time_ms']:.2f} |"
        ),
        (
            f"| avg_replan_count | {no_mem['avg_replan_count']:.2f} | "
            f"{with_mem['avg_replan_count']:.2f} |"
        ),
        (
            f"| skill_validated_total | {no_mem['skill_validated_total']} | "
            f"{with_mem['skill_validated_total']} |"
        ),
        (
            f"| skill_negative_transfer_total | {no_mem['skill_negative_transfer_total']} | "
            f"{with_mem['skill_negative_transfer_total']} |"
        ),
        (
            f"| memory_retrieval_total | {no_mem['memory_retrieval_total']} | "
            f"{with_mem['memory_retrieval_total']} |"
        ),
        (
            f"| memory_useful_total | {no_mem['memory_useful_total']} | "
            f"{with_mem['memory_useful_total']} |"
        ),
        (
            f"| memory_stale_or_wrong_total | {no_mem['memory_stale_or_wrong_total']} | "
            f"{with_mem['memory_stale_or_wrong_total']} |"
        ),
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    no_memory_rows = _run_variant(use_memory=False)
    with_memory_rows = _run_variant(use_memory=True)
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "variants": {
            "no_memory": {
                "config": {"use_memory": False, "use_skills": True, "adapter": "fake"},
                "aggregate": _aggregate(no_memory_rows),
                "rows": no_memory_rows,
            },
            "with_memory": {
                "config": {"use_memory": True, "use_skills": True, "adapter": "fake"},
                "aggregate": _aggregate(with_memory_rows),
                "rows": with_memory_rows,
            },
        },
    }
    _write_reports(payload)
    print("Ablation completed:")
    print(f"  JSON: {REPORTS_DIR / 'memory-ablation-summary.json'}")
    print(f"  MD:   {REPORTS_DIR / 'memory-ablation-summary.md'}")


if __name__ == "__main__":
    main()
