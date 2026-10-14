"""E-A1 pure selectors. B2/B3 differ only in current validity gating."""

from __future__ import annotations

import json
from datetime import datetime

from pydantic import Field

from reposkill_agent.evidence.locator import tokens
from reposkill_agent.evidence.models import EvidenceState
from reposkill_agent.experiments.contracts import (
    DatasetManifest,
    ExperimentContract,
    MemoryBuildManifest,
    Variant,
    bind_task,
    model_hash,
    require_frozen,
)
from reposkill_agent.integrations.harness_h4 import wire_data
from reposkill_agent.memory.validity import RepoFacts, check_validity
from reposkill_agent.protocol.public import Digest, StrictModel, canonical, digest


class CandidateAudit(StrictModel):
    candidate_id: str
    memory_id: str
    score: int
    source_hash: Digest
    selected: bool
    requested: bool
    rejected: bool
    reasons: tuple[str, ...]
    validity: str
    validity_reasons: tuple[str, ...]
    text: str
    text_hash: Digest
    bytes: int = Field(ge=0)


class VariantDecision(StrictModel):
    experiment_id: str
    task_id: str
    variant: Variant
    decision_id: str
    profile_hash: Digest
    history_hash: Digest
    items: tuple[CandidateAudit, ...]
    external_model_calls: int = 0
    method_degraded: bool = False
    injection_status: str = "await_host_receipt"

    def context_candidates(self) -> list[dict]:
        return [
            {
                "id": c.candidate_id,
                "text": c.text,
                "source": c.source_hash,
                "reason": "experiment_selected",
                "valid": True,
                "priority": c.score,
            }
            for c in self.items
            if c.requested
        ]


def select_variant(
    task,
    evidence: EvidenceState,
    facts: RepoFacts,
    contract: ExperimentContract,
    dataset: DatasetManifest,
    memory: MemoryBuildManifest,
    variant: Variant,
    *,
    now: datetime,
    decision_id: str,
) -> VariantDecision:
    require_frozen(contract, dataset, memory)
    bind_task(task, dataset)
    if variant not in contract.variants:
        raise ValueError("unknown_variant")
    profile = contract.profile
    if (
        task.budget.model_calls,
        task.budget.input_tokens,
        task.budget.output_tokens,
        task.budget.tool_calls,
        task.budget.wall_seconds,
        task.budget.retry_limit,
    ) != (
        profile.model_calls,
        profile.input_tokens,
        profile.output_tokens,
        profile.tool_calls,
        profile.wall_seconds,
        profile.retry_limit,
    ):
        raise ValueError("task_budget_profile_mismatch")
    if (facts.repo_id, facts.revision) != (task.repo_ref.repo_id, task.repo_ref.revision):
        raise ValueError("facts_task_mismatch")
    if evidence.repo_revision != task.repo_ref.revision or any(
        o.repo_revision != task.repo_ref.revision for o in evidence.observations
    ):
        raise ValueError("evidence_task_mismatch")
    result = dict(
        experiment_id=contract.experiment_id,
        task_id=task.task_id,
        variant=variant,
        decision_id=decision_id,
        profile_hash=model_hash(profile),
        history_hash=model_hash(memory),
    )
    if variant == "B0":
        return VariantDecision(**result, items=())
    # IDs, paths, split metadata and private evaluator objects never enter the index.
    query = tokens(task.issue_text + "\n" + "\n".join(o.content for o in evidence.observations))
    ranked = sorted(
        ((len(query & tokens(h.raw_text)), h) for h in memory.history),
        key=lambda pair: (-pair[0], pair[1].source.artifact.sha256),
    )[: profile.candidate_limit]
    groups = {}
    for h in memory.history:
        if h.record.conflict_group:
            groups.setdefault(h.record.conflict_group, set()).add(h.record.content_hash)
    items, seen = [], set()
    used = selected_count = 0
    for score, h in ranked:
        record = h.record
        if variant == "B1":
            text = h.raw_text
        else:
            text = canonical(
                {
                    "kind": "procedure_skill",
                    "procedure": record.procedure,
                    "applicability": record.applicability,
                    "verification": record.verification_recipe,
                    "source_hash": h.source.artifact.sha256,
                }
            )
        wire_data(json.loads(text))
        reasons = []
        if not score:
            reasons.append("no_public_relevance")
        if record.status != "validated":
            reasons.append("status_" + record.status)
        if record.conflict_group and len(groups[record.conflict_group]) > 1:
            reasons.append("unresolved_conflict")
        if record.content_hash in seen:
            reasons.append("duplicate_content")
        validity, checks = "not_checked", ()
        if variant == "B3":
            checked = check_validity(record, facts, now)
            validity = checked.status
            checks = tuple(c.reason for c in checked.checks)
            if validity != "valid":
                reasons.append("validity_" + validity)
        nbytes = len(text.encode())
        if selected_count >= profile.injection_limit or used + nbytes > profile.injection_bytes:
            reasons.append("injection_quota")
        selected = not reasons
        if selected:
            selected_count += 1
            used += nbytes
            seen.add(record.content_hash)
        items.append(
            CandidateAudit(
                candidate_id=digest(decision_id + ":" + h.source.artifact.sha256),
                memory_id=record.memory_id,
                score=score,
                source_hash=h.source.artifact.sha256,
                selected=selected,
                requested=selected,
                rejected=not selected,
                reasons=tuple(reasons),
                validity=validity,
                validity_reasons=checks,
                text=text,
                text_hash=digest(text),
                bytes=nbytes,
            )
        )
    return VariantDecision(**result, items=tuple(items))
