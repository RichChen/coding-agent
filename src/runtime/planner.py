"""Lightweight explicit plan support for plan-act mode.

This module intentionally avoids an extra LLM call. The goal for P1-1 is to
make task decomposition visible and traceable without changing default ReAct
behaviour or introducing complex replanning.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any


class PlanStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"


INSPECT_TOOLS = {"read_file", "list_dir", "subagent_task"}
APPLY_TOOLS = {"write_file", "search_replace", "edit_file"}
VERIFY_TOOLS = {"run_command", "read_file", "list_dir"}


@dataclass
class PlanStep:
    id: int
    title: str
    status: PlanStatus = PlanStatus.PENDING
    suggested_tools: list[str] = field(default_factory=list)
    replanned: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "status": self.status.value,
            "suggested_tools": list(self.suggested_tools),
        }


@dataclass
class Plan:
    goal: str
    steps: list[PlanStep] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal": self.goal,
            "steps": [step.to_dict() for step in self.steps],
        }

    def mark_started(self) -> None:
        if self.steps and all(step.status == PlanStatus.PENDING for step in self.steps):
            self.steps[0].status = PlanStatus.IN_PROGRESS

    def advance_after_turn(self) -> None:
        """Mark the current active step done and start the next pending step."""
        for idx, step in enumerate(self.steps):
            if step.status == PlanStatus.IN_PROGRESS:
                step.status = PlanStatus.DONE
                if idx + 1 < len(self.steps):
                    self.steps[idx + 1].status = PlanStatus.IN_PROGRESS
                return
        for step in self.steps:
            if step.status == PlanStatus.PENDING:
                step.status = PlanStatus.IN_PROGRESS
                return

    def mark_done(self) -> None:
        for step in self.steps:
            step.status = PlanStatus.DONE

    def active_step(self) -> PlanStep | None:
        for step in self.steps:
            if step.status == PlanStatus.IN_PROGRESS:
                return step
        return None

    def to_prompt_text(self) -> str:
        lines = [f"Goal: {self.goal}", "Plan:"]
        for step in self.steps:
            tools = ", ".join(step.suggested_tools) if step.suggested_tools else "n/a"
            lines.append(
                f"- [{step.status.value}] {step.id}. {step.title} (tools: {tools})"
            )
        return "\n".join(lines)

    def maybe_replan(self, reason: str) -> bool:
        """Perform one lightweight replan by rewriting the active step title."""
        active = self.active_step()
        if active is None:
            return False
        if "failure" not in reason.lower() and "error" not in reason.lower():
            return False
        if active.replanned:
            return False

        title = active.title.lower()
        if any(word in title for word in ["verification", "test", "check", "re-run"]):
            active.title = "Re-run verification after fixing the previous error"
        elif any(word in title for word in ["inspect", "understand", "gather", "re-inspect"]):
            active.title = "Re-inspect relevant files after the tool failure"
        elif any(word in title for word in ["apply", "change", "code", "file", "revise", "implementation"]):
            active.title = "Revise the implementation based on the tool failure"
        else:
            active.title = "Re-inspect relevant files after the tool failure"
        active.replanned = True
        return True

    def current_step_title(self) -> str | None:
        active = self.active_step()
        return active.title if active else None

    def _title_keyword_match(self, title: str, tool_names: set[str]) -> bool:
        title_lower = title.lower()
        if any(word in title_lower for word in ["inspect", "understand", "gather", "re-inspect"]):
            return bool(tool_names & INSPECT_TOOLS)
        if any(word in title_lower for word in ["apply", "change", "code", "file", "revise", "implementation"]):
            return bool(tool_names & APPLY_TOOLS)
        if any(word in title_lower for word in ["verification", "test", "check", "re-run"]):
            return bool(tool_names & VERIFY_TOOLS)
        return False

    def advance_after_tools(self, tool_names: list[str], success_count: int) -> bool:
        """Advance when successful tools match suggested_tools or title keywords."""
        if success_count <= 0:
            return False
        active = self.active_step()
        if active is None:
            return False

        tools = set(tool_names)
        if active.suggested_tools and tools & set(active.suggested_tools):
            self.advance_after_turn()
            return True
        if self._title_keyword_match(active.title, tools):
            self.advance_after_turn()
            return True
        return False


class SimplePlanner:
    """Builds a small deterministic plan for traceability."""

    def create_plan(self, task_description: str, enabled_tools: list[str] | None = None) -> Plan:
        tools = set(enabled_tools or [])
        inspect_tools = sorted(tools & INSPECT_TOOLS) or ["read_file"]
        steps = [
            PlanStep(
                id=1,
                title="Understand the task and inspect relevant files",
                suggested_tools=inspect_tools,
            )
        ]

        apply_tools = sorted(tools & APPLY_TOOLS)
        if apply_tools:
            steps.append(
                PlanStep(
                    id=2,
                    title="Apply the required code or file changes",
                    suggested_tools=apply_tools,
                )
            )
        else:
            steps.append(
                PlanStep(
                    id=2,
                    title="Use available tools to gather the answer",
                    suggested_tools=inspect_tools,
                )
            )

        if "run_command" in tools:
            steps.append(
                PlanStep(
                    id=3,
                    title="Run a verification command or test when useful",
                    suggested_tools=["run_command"],
                )
            )
        else:
            steps.append(
                PlanStep(
                    id=3,
                    title="Check the final state against the request",
                    suggested_tools=inspect_tools,
                )
            )

        plan = Plan(goal=task_description, steps=steps)
        plan.mark_started()
        return plan
