"""Deterministic lexical baseline over public observations, not benchmark metadata."""

from __future__ import annotations

import re

from reposkill_agent.evidence.models import (
    EvidenceState,
    LocatorDecision,
    Observation,
    Proposal,
)
from reposkill_agent.protocol.public import PublicTask, digest, safe_relative

STOP = frozenset(
    {
        "the",
        "and",
        "for",
        "with",
        "from",
        "this",
        "that",
        "when",
        "fix",
        "bug",
        "fails",
        "failure",
        "should",
        "test",
        "tests",
    }
)


def tokens(text: str) -> set[str]:
    return {
        s.lower() for s in re.findall(r"[A-Za-z_][A-Za-z_0-9]{2,}", text) if s.lower() not in STOP
    }


def writable(path: str) -> bool:
    parts = path.lower().split("/")
    return (
        "tests" not in parts
        and "test" not in parts
        and not parts[-1].startswith("test_")
        and not parts[-1].endswith("_test.py")
    )


class EvidenceLocator:
    def __init__(self, per_round: int = 3, max_files: int = 6, max_chars: int = 12000):
        if min(per_round, max_files, max_chars) < 1:
            raise ValueError("invalid_evidence_limits")
        self.per_round, self.max_files, self.max_chars = per_round, max_files, max_chars

    def decide(
        self,
        task: PublicTask,
        tree: tuple[str, ...],
        state: EvidenceState | None = None,
        observations: tuple[Observation, ...] = (),
    ) -> LocatorDecision:
        if task.protocol_mode != "realistic":
            raise ValueError("realistic_locator_requires_public_protocol")
        state = state or EvidenceState(repo_revision=task.repo_ref.revision)
        if state.repo_revision != task.repo_ref.revision:
            raise ValueError("evidence_revision_changed")
        paths = sorted({safe_relative(p) for p in tree})
        if len(paths) > 2000:
            raise ValueError("tree_requires_bounded_host_view")
        merged = {o.observation_id: o for o in state.observations}
        chars = sum(len(o.content) for o in merged.values())
        for obs in observations:
            if obs.repo_revision != state.repo_revision or obs.path not in paths:
                raise ValueError("unbound_observation")
            if obs.observation_id in merged:
                if merged[obs.observation_id] != obs:
                    raise ValueError("observation_id_collision")
                continue
            if chars + len(obs.content) > self.max_chars:
                raise ValueError("evidence_content_budget_exceeded")
            merged[obs.observation_id] = obs
            chars += len(obs.content)
        observed = tuple(sorted(merged.values(), key=lambda o: o.observation_id))
        files = {o.path for o in observed if o.kind == "file"}
        if len(files) > self.max_files:
            raise ValueError("evidence_file_budget_exceeded")
        query = tokens(task.issue_text)
        ranked = []
        for path in paths:
            direct = path in task.issue_text or path in "\n".join(
                o.content for o in observed if o.kind == "public_test"
            )
            evidence = [o for o in observed if o.path == path]
            score = 100 if direct else 0
            score += 3 * len(query & tokens(path))
            score += sum(len(query & tokens(o.content)) for o in evidence)
            # Imports/call sites are accepted as search observations from the host.
            if score:
                refs = tuple(o.artifact.logical_id for o in evidence)
                ranked.append((-score, path, refs, "public_path" if direct else "lexical_evidence"))
        ranked.sort()
        selected = tuple(path for _, path, _, _ in ranked if path in files)
        remaining = max(0, task.budget.tool_calls - state.tool_proposals_spent)
        proposed_paths = set(state.proposed_paths)
        proposals = []
        capacity = min(
            self.per_round, remaining, max(0, self.max_files - len(files | proposed_paths))
        )
        for _, path, refs, reason in ranked:
            if path in files or path in proposed_paths or len(proposals) >= capacity:
                continue
            if "read" in task.allowed_tools:
                proposals.append(
                    Proposal(
                        proposal_id=digest("read:" + path),
                        tool="read",
                        path=path,
                        reason=reason,
                        evidence_refs=refs,
                    )
                )
        search_query = " ".join(sorted(query))[:300]
        searched = state.searched_queries
        if (
            not proposals
            and not selected
            and search_query
            and remaining
            and search_query not in searched
            and "search" in task.allowed_tools
        ):
            proposals.append(
                Proposal(
                    proposal_id=digest("search:" + search_query),
                    tool="search",
                    query=search_query,
                    reason="issue_keywords",
                )
            )
            searched = (*searched, search_query)
        status = (
            "needs_observation"
            if proposals
            else "evidence_ready"
            if selected
            else "budget_exhausted"
            if not remaining or not capacity
            else "insufficient_evidence"
        )
        new_state = EvidenceState(
            repo_revision=state.repo_revision,
            observations=observed,
            proposed_paths=tuple(sorted(proposed_paths | {p.path for p in proposals if p.path})),
            searched_queries=searched,
            hypotheses=selected,
            missing_evidence=() if selected else ("need_public_code_evidence",),
            tool_proposals_spent=state.tool_proposals_spent + len(proposals),
        )
        return LocatorDecision(
            status=status, state=new_state, proposals=tuple(proposals), selected_paths=selected
        )
