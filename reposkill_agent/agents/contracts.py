"""Structured contracts for role-based agents."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from reposkill_agent.adapters.base import WorkspaceAdapter
from reposkill_agent.core.contracts import TaskSpec
from reposkill_agent.core.task_graph import TaskNode


class AgentContext(BaseModel):
    """Input context shared with role agents."""

    task: TaskSpec
    node: TaskNode
    replan_count: int = 0
    previous_actions: list[dict[str, Any]] = Field(default_factory=list)
    active_skills: list[dict[str, Any]] = Field(default_factory=list)
    memory_hints: list[dict[str, Any]] = Field(default_factory=list)
    expanded_paths: list[str] = Field(default_factory=list)


class AgentResult(BaseModel):
    """Structured output from one role agent execution."""

    success: bool
    payload: dict[str, Any] = Field(default_factory=dict)


class RoleAgent:
    """Base interface for deterministic Phase 3 role agents."""

    role: str = "agent"

    def run(self, context: AgentContext, adapter: WorkspaceAdapter) -> AgentResult:
        raise NotImplementedError
