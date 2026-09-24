"""Tests for baseline runner on tiny benchmark tasks."""

from pathlib import Path

import pytest

from reposkill_agent.eval.runner import BaselineRunner
from reposkill_agent.eval.task_spec import load_tasks

BENCHMARKS_ROOT = Path(__file__).parent.parent / "benchmarks"
TASKS_FILE = BENCHMARKS_ROOT / "tasks" / "tiny_python_tasks.yaml"


@pytest.fixture
def catalog():
    return load_tasks(TASKS_FILE, benchmarks_root=BENCHMARKS_ROOT)


@pytest.mark.parametrize(
    "task_id",
    ["fix_import_error", "fix_off_by_one", "add_greeting_function"],
)
def test_baseline_runner_passes_task(task_id: str, catalog, tmp_path: Path):
    task = catalog.get(task_id)
    assert task is not None

    runner = BaselineRunner(
        adapter="fake",
        trace_dir=tmp_path / "traces",
        work_dir=tmp_path / "work",
    )
    result = runner.run(task)
    assert result.metrics.success, (
        f"Task {task_id} failed: {result.test_result.stderr}\n{result.test_result.stdout}"
    )
    assert result.metrics.steps >= 1
    assert Path(result.metrics.trace_path).exists()
    assert len(result.diff) > 0


def test_load_tasks_count(catalog):
    assert len(catalog.tasks) == 3
