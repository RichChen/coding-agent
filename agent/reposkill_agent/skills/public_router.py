"""Evidence-only skill routing for the realistic public protocol.

This module deliberately has no dependency on ``TaskSpec`` or task tags.  A
host supplies only the public task, observations already admitted into the
evidence state, repository facts, and an explicit routing budget.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from pydantic import Field

from reposkill_agent.evidence.locator import tokens
from reposkill_agent.evidence.models import EvidenceState
from reposkill_agent.memory.validity import RepoFacts
from reposkill_agent.protocol.public import PublicTask, StrictModel, Versioned
from reposkill_agent.skills.models import SkillSpec


class PublicSkillBudget(StrictModel):
    max_candidates: int = Field(default=20, ge=0)
    max_selected: int = Field(default=3, ge=0)
    max_chars: int = Field(default=6000, ge=0)


class PublicSkillItem(StrictModel):
    skill_id: str
    version: str
    score: int = Field(ge=0)
    reason: str
    estimated_chars: int = Field(ge=0)


class PublicSkillRoute(Versioned):
    protocol_mode: str = "realistic"
    candidates: tuple[PublicSkillItem, ...] = ()
    selected: tuple[PublicSkillItem, ...] = ()
    rejected: tuple[dict[str, str], ...] = ()
    candidate_count: int = 0
    selected_count: int = 0
    rejected_count: int = 0
    estimated_chars: int = 0
    external_model_calls: int = 0


def _evidence_text(state: EvidenceState) -> str:
    return "\n".join(
        [*state.hypotheses] + [o.path + "\n" + o.content for o in state.observations]
    )


def _normalise(value: str) -> str:
    return re.sub(r"[^a-z0-9_ ]+", " ", value.lower())


def _contains_requirement(requirement: str, text: str, word_set: set[str]) -> bool:
    normalized = _normalise(requirement)
    if normalized and normalized in _normalise(text):
        return True
    required = tokens(requirement)
    return bool(required) and required <= word_set


def route_public_skills(
    task: PublicTask,
    evidence: EvidenceState,
    facts: RepoFacts,
    skills: Iterable[SkillSpec],
    budget: PublicSkillBudget | None = None,
) -> PublicSkillRoute:
    """Rank and gate skills using public evidence only.

    A zero-result route is valid.  Repository facts are an identity and
    provenance check here; semantic dependency validity remains the memory
    gate's responsibility.
    """

    if task.protocol_mode != "realistic":
        raise ValueError("realistic_skill_route_required")
    if (task.repo_ref.repo_id, task.repo_ref.revision) != (facts.repo_id, facts.revision):
        raise ValueError("task_facts_mismatch")
    if evidence.repo_revision != task.repo_ref.revision:
        raise ValueError("evidence_revision_changed")
    budget = budget or PublicSkillBudget()
    evidence_text = task.issue_text + "\n" + _evidence_text(evidence)
    words = tokens(evidence_text)
    issue_words = tokens(task.issue_text)
    ranked: list[tuple[int, SkillSpec, str]] = []
    rejected: list[dict[str, str]] = []
    for skill in skills:
        requirement = skill.evidence_requirements()
        missing = [r for r in requirement if not _contains_requirement(r, evidence_text, words)]
        forbidden = [
            r
            for r in skill.not_applicable_when
            if _contains_requirement(r, evidence_text, words)
        ]
        if missing:
            rejected.append({"skill_id": skill.id, "reason": "missing_public_evidence"})
            continue
        if forbidden:
            rejected.append({"skill_id": skill.id, "reason": "not_applicable_from_evidence"})
            continue
        skill_words = tokens(
            " ".join((skill.id, skill.name, skill.purpose, skill.pattern, *skill.applies_when))
        )
        score = len(issue_words & skill_words) + len(words & skill_words)
        if skill.domains and not (words & {d.lower() for d in skill.domains}):
            rejected.append({"skill_id": skill.id, "reason": "domain_not_observed"})
            continue
        if score <= 0:
            rejected.append({"skill_id": skill.id, "reason": "no_public_relevance"})
            continue
        ranked.append((score, skill, "public_issue_and_evidence_overlap"))
    ranked.sort(key=lambda item: (-item[0], item[1].id))
    ranked = ranked[: budget.max_candidates]
    candidate_items = tuple(
        PublicSkillItem(
            skill_id=skill.id,
            version=skill.version,
            score=score,
            reason=reason,
            estimated_chars=(
                len(skill.name) + len(skill.purpose) + sum(len(x) for x in skill.recipe_lines())
            ),
        )
        for score, skill, reason in ranked
    )
    selected_list: list[PublicSkillItem] = []
    used = 0
    for item in candidate_items:
        if (
            len(selected_list) >= budget.max_selected
            or used + item.estimated_chars > budget.max_chars
        ):
            rejected.append({"skill_id": item.skill_id, "reason": "routing_budget"})
            continue
        selected_list.append(item)
        used += item.estimated_chars
    selected = tuple(selected_list)
    return PublicSkillRoute(
        candidates=candidate_items,
        selected=selected,
        rejected=tuple(rejected),
        candidate_count=len(candidate_items),
        selected_count=len(selected),
        rejected_count=len(rejected),
        estimated_chars=used,
    )
