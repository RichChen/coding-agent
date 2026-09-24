#!/usr/bin/env python3
"""Run deterministic task graph runner on all tiny repo tasks."""

from pathlib import Path

from reposkill_agent.eval.graph_runner import TaskGraphRunner
from reposkill_agent.eval.task_spec import load_tasks

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    catalog = load_tasks(
        ROOT / "benchmarks" / "tasks" / "tiny_python_tasks.yaml",
        benchmarks_root=ROOT / "benchmarks",
    )
    runner = TaskGraphRunner(
        adapter="fake",
        trace_dir=ROOT / "traces",
        max_replans=1,
    )
    passed = 0
    for task in catalog.tasks:
        result = runner.run(task)
        status = "PASS" if result.metrics.success else "FAIL"
        print(
            f"[{status}] {task.id}  "
            f"steps={result.metrics.steps}  "
            f"replans={result.metrics.replan_count}  "
            f"trace={result.metrics.trace_path}"
        )
        if result.metrics.success:
            passed += 1
    print(f"\n{passed}/{len(catalog.tasks)} tasks passed")


if __name__ == "__main__":
    main()
