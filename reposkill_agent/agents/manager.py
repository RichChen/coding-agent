"""Manager agent for inspect and summarize nodes."""

from __future__ import annotations

from reposkill_agent.adapters.base import WorkspaceAdapter
from reposkill_agent.agents.contracts import AgentContext, AgentResult, RoleAgent


class ManagerAgent(RoleAgent):
    """Handles manager-owned nodes."""

    role = "manager"

    def run(self, context: AgentContext, adapter: WorkspaceAdapter) -> AgentResult:
        if context.node.id == "inspect":
            files = adapter.list_files("**/*.py")
            return AgentResult(
                success=True,
                payload={"matched_files": files[:20], "count": len(files)},
            )
        if context.node.id == "summarize":
            return AgentResult(
                success=True,
                payload={"summary": f"task={context.task.id} complete"},
            )
        return AgentResult(
            success=False,
            payload={"error": f"manager cannot handle node {context.node.id}"},
        )
