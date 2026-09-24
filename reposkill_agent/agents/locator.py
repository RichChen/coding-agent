"""Locator agent for file/symbol hypothesis nodes."""

from __future__ import annotations

from reposkill_agent.adapters.base import WorkspaceAdapter
from reposkill_agent.agents.contracts import AgentContext, AgentResult, RoleAgent
from reposkill_agent.core.context_expansion import (
    collect_requested_context,
    expand_allowed_paths,
    merge_expanded_paths,
)


class LocatorAgent(RoleAgent):
    """Handles locate node and context expansion after needs_more_context."""

    role = "locator"

    def run(self, context: AgentContext, adapter: WorkspaceAdapter) -> AgentResult:
        matches: list[str] = []
        for path in context.task.expected_files:
            normalized = path.replace("\\", "/")
            if path in adapter.list_files(path) or normalized in adapter.list_files("**/*"):
                matches.append(normalized)

        current_paths = set(matches) | {p.replace("\\", "/") for p in context.expanded_paths}
        requested = collect_requested_context(context.previous_actions)
        expanded_paths: list[str] = []
        expansion_reasons: list[str] = []
        if requested:
            added, reasons = expand_allowed_paths(
                adapter=adapter,
                task=context.task,
                requested_context=requested,
                current_paths=current_paths,
            )
            expanded_paths = added
            expansion_reasons = reasons

        all_matches = merge_expanded_paths(matches, expanded_paths)
        success = bool(all_matches) or not context.task.expected_files
        return AgentResult(
            success=success,
            payload={
                "matches": all_matches,
                "expected_files": context.task.expected_files,
                "expanded_paths": expanded_paths,
                "expansion_reasons": expansion_reasons,
                "requested_context": requested,
            },
        )
