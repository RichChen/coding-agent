"""QA agent for test nodes."""

from __future__ import annotations

from reposkill_agent.adapters.base import WorkspaceAdapter
from reposkill_agent.agents.contracts import AgentContext, AgentResult, RoleAgent


class QAAgent(RoleAgent):
    """Handles test node and classifies pass/fail."""

    role = "qa"

    def run(self, context: AgentContext, adapter: WorkspaceAdapter) -> AgentResult:
        test_result = adapter.run_tests(context.task.test_command)
        return AgentResult(
            success=test_result.passed,
            payload={"test_result": test_result.model_dump(), "test_result_obj": test_result},
        )
