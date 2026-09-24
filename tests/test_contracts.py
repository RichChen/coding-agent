"""Tests for core contracts."""

from reposkill_agent.core.contracts import TaskSpec
from reposkill_agent.core.trace import TraceEvent, TraceWriter


def test_task_spec_creation():
    task = TaskSpec(
        id="demo",
        issue="Fix the bug",
        repo_path="/tmp/repo",
        test_command="pytest",
    )
    assert task.id == "demo"
    assert task.expected_files == []


def test_trace_event_roundtrip(tmp_path):
    trace_path = tmp_path / "trace.jsonl"
    writer = TraceWriter(trace_path, run_id="run1", task_id="demo")
    event = writer.emit("run_start", {"adapter": "fake"})
    assert event.event_type == "run_start"
    assert trace_path.exists()
    content = trace_path.read_text(encoding="utf-8")
    assert "run_start" in content

    parsed = TraceEvent.model_validate_json(content.strip())
    assert parsed.run_id == "run1"
