"""Tests for Phase 3 role agents and dispatch."""

from pathlib import Path

from reposkill_agent.adapters.fake_adapter import FakeAdapter
from reposkill_agent.agents import DeveloperAgent, LocatorAgent, ManagerAgent, QAAgent
from reposkill_agent.agents.contracts import AgentContext
from reposkill_agent.core.contracts import TaskSpec
from reposkill_agent.core.task_graph import TaskNode
from reposkill_agent.eval.graph_runner import TaskGraphRunner
from reposkill_agent.eval.scripted_fixes import SCRIPTED_FIXES


def _sample_task(tmp_path: Path) -> TaskSpec:
    app_dir = tmp_path / "app"
    app_dir.mkdir(parents=True, exist_ok=True)
    (app_dir / "calculator.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "tests").mkdir(parents=True, exist_ok=True)
    (tmp_path / "tests" / "test_calc.py").write_text(
        "def test_ok():\n    assert 1 == 1\n",
        encoding="utf-8",
    )
    return TaskSpec(
        id="fix_import_error",
        issue="test",
        repo_path=str(tmp_path),
        test_command="python -m pytest tests -q",
        expected_files=["app/calculator.py"],
        tags=["import"],
    )


def test_role_agents_return_structured_results(tmp_path: Path):
    task = _sample_task(tmp_path)
    adapter = FakeAdapter(tmp_path, scripted_fixes=SCRIPTED_FIXES)

    manager_node = TaskNode(id="inspect", goal="inspect", owner="manager", expected_artifact="x")
    locator_node = TaskNode(id="locate", goal="locate", owner="locator", expected_artifact="x")
    dev_node = TaskNode(id="patch", goal="patch", owner="developer", expected_artifact="x")
    qa_node = TaskNode(id="test", goal="test", owner="qa", expected_artifact="x")

    manager_result = ManagerAgent().run(AgentContext(task=task, node=manager_node), adapter)
    locator_result = LocatorAgent().run(AgentContext(task=task, node=locator_node), adapter)
    developer_result = DeveloperAgent().run(AgentContext(task=task, node=dev_node), adapter)
    qa_result = QAAgent().run(AgentContext(task=task, node=qa_node), adapter)

    assert manager_result.success
    assert "matched_files" in manager_result.payload
    assert "matches" in locator_result.payload
    assert "patches" in developer_result.payload
    assert "test_result" in qa_result.payload


def test_graph_runner_has_role_dispatch_table():
    dispatch = TaskGraphRunner()._build_role_agents()
    assert set(dispatch.keys()) == {"manager", "locator", "developer", "qa"}
