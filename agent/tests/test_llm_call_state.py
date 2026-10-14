"""Regression test for per-task LLM call budget reset."""

from __future__ import annotations

from pathlib import Path

from reposkill_agent.eval.graph_runner import TaskGraphRunner
from reposkill_agent.eval.task_spec import load_tasks
from reposkill_agent.llm.client import MockModelClient

BENCHMARKS_ROOT = Path(__file__).parent.parent / "benchmarks"
TASKS_FILE = BENCHMARKS_ROOT / "tasks" / "phase6_hard_12.yaml"


def test_llm_call_state_resets_between_tasks(tmp_path: Path):
    catalog = load_tasks(TASKS_FILE, benchmarks_root=BENCHMARKS_ROOT)
    tasks = catalog.tasks[:3]
    mock = MockModelClient(
        responses=[
            {
                "summary": "noop",
                "edits": [],
                "confidence": 0.1,
                "needs_more_context": True,
            }
        ]
        * 20
    )
    runner = TaskGraphRunner(
        adapter="fake",
        trace_dir=tmp_path / "traces",
        work_dir=tmp_path / "work",
        developer_mode="llm",
        model_client=mock,
        max_llm_calls_per_task=1,
        allow_prefix_scripted_fixes=False,
    )
    calls_per_task: list[int] = []
    for task in tasks:
        before = len(mock.calls)
        runner.run(task)
        calls_per_task.append(len(mock.calls) - before)

    assert calls_per_task == [1, 1, 1]
