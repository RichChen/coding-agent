"""Deterministic task graph planner for Phase 2."""

from __future__ import annotations

from reposkill_agent.core.contracts import TaskSpec
from reposkill_agent.core.task_graph import PlanResult, ReplanDecision, TaskGraph, TaskNode


class TaskGraphPlanner:
    """Build a deterministic graph from task metadata."""

    def __init__(self, max_replans: int = 1) -> None:
        self.max_replans = max_replans

    def create_plan(self, task: TaskSpec) -> PlanResult:
        """Create a simple graph: inspect -> locate -> patch -> test -> summarize."""
        expected_files = ", ".join(task.expected_files) if task.expected_files else "task context"
        tags = ", ".join(task.tags) if task.tags else "generic"
        nodes = [
            TaskNode(
                id="inspect",
                goal="Inspect repository structure and task context",
                owner="manager",
                expected_artifact="RepoInspection",
                verifier="inspection_contains_top_level_entries",
            ),
            TaskNode(
                id="locate",
                goal=f"Locate relevant files and symbols for: {expected_files}",
                owner="locator",
                dependencies=["inspect"],
                expected_artifact="Relevant file list and hypotheses",
                verifier="at_least_one_relevant_file",
            ),
            TaskNode(
                id="patch",
                goal=f"Apply a code patch to satisfy issue (tags: {tags})",
                owner="developer",
                dependencies=["locate"],
                expected_artifact="PatchResult list",
                verifier="diff_is_non_empty",
            ),
            TaskNode(
                id="test",
                goal=f"Run test command: {task.test_command}",
                owner="qa",
                dependencies=["patch"],
                expected_artifact="TestResult",
                verifier="tests_pass",
            ),
            TaskNode(
                id="summarize",
                goal="Summarize execution and persist metrics",
                owner="manager",
                dependencies=["test"],
                expected_artifact="GraphMetrics",
                verifier="metrics_recorded",
            ),
        ]
        graph = TaskGraph(task_id=task.id, nodes=nodes)
        rationale = "Deterministic Phase 2 planner based on expected_files, tags, and test command."
        return PlanResult(graph=graph, rationale=rationale)

    def observe_and_decide_replan(
        self,
        *,
        current_replans: int,
        failed_node_id: str | None,
        test_passed: bool,
    ) -> ReplanDecision:
        """Return replan decision after one execution pass."""
        if test_passed:
            return ReplanDecision(
                should_replan=False,
                reason="tests_passed",
                max_replans=self.max_replans,
            )
        if current_replans >= self.max_replans:
            return ReplanDecision(
                should_replan=False,
                reason="replan_limit_reached",
                max_replans=self.max_replans,
            )
        reason = f"node_failed:{failed_node_id}" if failed_node_id else "tests_failed"
        return ReplanDecision(should_replan=True, reason=reason, max_replans=self.max_replans)
