"""Tests for Phase 2 deterministic planner."""

from reposkill_agent.core.contracts import TaskSpec
from reposkill_agent.core.planner import TaskGraphPlanner


def test_planner_creates_expected_node_order():
    planner = TaskGraphPlanner(max_replans=2)
    task = TaskSpec(
        id="t1",
        issue="Fix bug",
        repo_path="repo",
        test_command="pytest -q",
        expected_files=["app/main.py"],
        tags=["bugfix"],
    )
    result = planner.create_plan(task)
    assert [node.id for node in result.graph.nodes] == [
        "inspect",
        "locate",
        "patch",
        "test",
        "summarize",
    ]
    assert result.graph.nodes[2].owner == "developer"


def test_replan_decision_when_tests_fail():
    planner = TaskGraphPlanner(max_replans=1)
    decision = planner.observe_and_decide_replan(
        current_replans=0,
        failed_node_id="test",
        test_passed=False,
    )
    assert decision.should_replan
    assert "node_failed:test" in decision.reason
