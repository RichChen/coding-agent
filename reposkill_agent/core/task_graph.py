"""Task graph models for structured planning and execution."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

NodeStatus = Literal["pending", "running", "passed", "failed", "skipped"]
NodeOwner = Literal["manager", "locator", "developer", "qa", "memory_curator"]


class TaskNode(BaseModel):
    """A single executable node in a structured task graph."""

    id: str
    goal: str
    owner: NodeOwner
    dependencies: list[str] = Field(default_factory=list)
    expected_artifact: str
    verifier: str | None = None
    status: NodeStatus = "pending"


class TaskGraph(BaseModel):
    """A DAG-like task graph used by the graph runner."""

    task_id: str
    nodes: list[TaskNode]
    planner_version: str = "v0-deterministic"

    def get_node(self, node_id: str) -> TaskNode:
        """Return a node by ID."""
        for node in self.nodes:
            if node.id == node_id:
                return node
        raise KeyError(f"node not found: {node_id}")


class PlanResult(BaseModel):
    """Output of the planner."""

    graph: TaskGraph
    rationale: str


class ReplanDecision(BaseModel):
    """Decision emitted after observation to trigger/skip replanning."""

    should_replan: bool = False
    reason: str = "no_replan_needed"
    max_replans: int = 1
