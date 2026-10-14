"""Tests for task graph runner."""

from pathlib import Path

from reposkill_agent.core.contracts import TaskSpec
from reposkill_agent.eval.graph_runner import TaskGraphRunner
from reposkill_agent.eval.task_spec import load_tasks

BENCHMARKS_ROOT = Path(__file__).parent.parent / "benchmarks"
TASKS_FILE = BENCHMARKS_ROOT / "tasks" / "tiny_python_tasks.yaml"


def test_graph_runner_passes_fake_task(tmp_path: Path):
    catalog = load_tasks(TASKS_FILE, benchmarks_root=BENCHMARKS_ROOT)
    task = catalog.get("fix_import_error")
    assert task is not None
    runner = TaskGraphRunner(
        adapter="fake",
        trace_dir=tmp_path / "traces",
        work_dir=tmp_path / "work",
        max_replans=1,
    )
    result = runner.run(task)
    assert result.metrics.success
    assert result.metrics.replan_count == 0
    assert Path(result.metrics.trace_path).exists()
    trace_text = Path(result.metrics.trace_path).read_text(encoding="utf-8")
    assert '"event_type":"plan_created"' in trace_text
    assert '"event_type":"node_start"' in trace_text
    assert '"event_type":"node_end"' in trace_text
    assert '"event_type":"replan"' in trace_text
    assert '"event_type":"metric","agent_role":"manager"' in trace_text
    assert '"event_type":"run_end","agent_role":"manager"' in trace_text
    assert '"event_type":"diff","agent_role":"developer"' in trace_text


def test_graph_runner_replans_when_tests_fail(tmp_path: Path):
    failing_task = TaskSpec(
        id="fix_import_error",
        issue="same task with wrong test command",
        repo_path=str(BENCHMARKS_ROOT / "repos" / "fix_import_error"),
        test_command="python -m pytest tests/does_not_exist -q",
        expected_files=["app/calculator.py"],
        tags=["import", "bugfix"],
    )
    runner = TaskGraphRunner(
        adapter="fake",
        trace_dir=tmp_path / "traces",
        work_dir=tmp_path / "work",
        max_replans=1,
    )
    result = runner.run(failing_task)
    assert not result.metrics.success
    assert result.metrics.replan_count == 1
    assert result.metrics.steps >= 8
