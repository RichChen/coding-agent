"""Public lexical retrieval, validity gating and host injection receipts."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from reposkill_agent.evidence.locator import tokens
from reposkill_agent.memory.records import MemoryRecord, UseRecord
from reposkill_agent.memory.source_manifest import SourcePolicy, validate_build_manifest
from reposkill_agent.memory.validity import RepoFacts, ValidityResult, check_validity
from reposkill_agent.protocol.public import PublicTask, StrictModel, canonical, digest


class ContextCandidate(StrictModel):
    candidate_id: str
    memory_id: str
    revision: int
    text: str
    requested_hash: str
    requested_chars: int
    source_refs: tuple[str, ...]


class GateItem(StrictModel):
    memory_id: str
    revision: int
    score: int
    selected: bool
    reasons: tuple[str, ...]
    validity: ValidityResult


class GateDecision(StrictModel):
    decision_id: str
    candidates: tuple[ContextCandidate, ...]
    items: tuple[GateItem, ...]
    requested_chars: int
    external_model_calls: int = 0


def select_memory(
    task: PublicTask,
    records: list[MemoryRecord],
    facts: RepoFacts,
    policy: SourcePolicy,
    now: datetime,
    *,
    decision_id: str,
    max_hints: int = 3,
    max_chars: int = 6000,
) -> GateDecision:
    if task.protocol_mode != "realistic":
        raise ValueError("realistic_memory_required")
    if task.task_id not in policy.target_task_ids:
        raise ValueError("target_missing_from_source_policy")
    if (task.repo_ref.repo_id, task.repo_ref.revision) != (facts.repo_id, facts.revision):
        raise ValueError("task_facts_mismatch")
    if min(max_hints, max_chars) < 0:
        raise ValueError("negative_context_budget")
    validate_build_manifest(policy)
    # Snapshot readers must supply only latest versions; duplicates are a caller error.
    if len({r.memory_id for r in records}) != len(records):
        raise ValueError("duplicate_memory_revisions")
    query = tokens(task.issue_text)
    ranked = sorted(
        ((len(query & tokens(r.procedure + " " + " ".join(r.applicability))), r) for r in records),
        key=lambda pair: (-pair[0], pair[1].memory_id),
    )
    validities = {r.memory_id: check_validity(r, facts, now) for r in records}
    groups: dict[str, set[str]] = {}
    for _, r in ranked:
        if r.conflict_group and r.status not in {"retired", "quarantined"}:
            groups.setdefault(r.conflict_group, set()).add(r.content_hash)
    selected, items, hashes = [], [], set()
    used = 0
    for score, record in ranked:
        validity = validities[record.memory_id]
        reasons = list(policy.reasons(record))
        if record.status != "validated":
            reasons.append("status_" + record.status)
        if validity.status != "valid":
            reasons.append("validity_" + validity.status)
        if record.conflict_group and len(groups.get(record.conflict_group, ())) > 1:
            reasons.append("unresolved_conflict")
        if not score:
            reasons.append("no_public_relevance")
        text = canonical(record.hint())
        if record.content_hash in hashes:
            reasons.append("duplicate_content")
        if len(selected) >= max_hints or used + len(text) > max_chars:
            reasons.append("context_budget")
        if not reasons:
            selected.append(
                ContextCandidate(
                    candidate_id=digest(f"{decision_id}:{record.memory_id}:{record.revision}"),
                    memory_id=record.memory_id,
                    revision=record.revision,
                    text=text,
                    requested_hash=digest(text),
                    requested_chars=len(text),
                    source_refs=tuple(s.artifact.logical_id for s in record.sources),
                )
            )
            hashes.add(record.content_hash)
            used += len(text)
        items.append(
            GateItem(
                memory_id=record.memory_id,
                revision=record.revision,
                score=score,
                selected=not reasons,
                reasons=tuple(reasons),
                validity=validity,
            )
        )
    return GateDecision(
        decision_id=decision_id,
        candidates=tuple(selected),
        items=tuple(items),
        requested_chars=used,
    )


class InjectionReceipt(StrictModel):
    """Trusted host response; ranges refer to the submitted candidate text."""

    receipt_id: str
    decision_id: str
    candidate_id: str
    requested_hash: str
    status: Literal["injected", "rejected"]
    start_char: int = Field(default=0, ge=0)
    end_char: int = Field(default=0, ge=0)
    actual_hash: str | None = None
    model_operation_id: str | None = None
    model_attempt_id: str | None = None
    reason: str


def confirm_injection(
    decision: GateDecision,
    receipts: tuple[InjectionReceipt, ...],
    run_id: str,
) -> tuple[UseRecord, ...]:
    records, seen = [], set()
    candidates = {c.candidate_id: c for c in decision.candidates}
    for receipt in receipts:
        candidate = candidates.get(receipt.candidate_id)
        if (
            receipt.decision_id != decision.decision_id
            or candidate is None
            or receipt.requested_hash != candidate.requested_hash
            or receipt.candidate_id in seen
        ):
            raise ValueError("unbound_injection_receipt")
        seen.add(receipt.candidate_id)
        if receipt.status == "injected":
            actual = candidate.text[receipt.start_char : receipt.end_char]
            if (
                not actual
                or receipt.end_char > len(candidate.text)
                or digest(actual) != receipt.actual_hash
                or not receipt.model_operation_id
                or not receipt.model_attempt_id
            ):
                raise ValueError("unverified_injection_receipt")
            stage = "actually_injected"
        else:
            if receipt.end_char or receipt.start_char or receipt.actual_hash is not None:
                raise ValueError("rejected_receipt_has_content")
            stage = "rejected"
        records.append(
            UseRecord(
                use_id=receipt.receipt_id,
                run_id=run_id,
                decision_id=decision.decision_id,
                memory_id=candidate.memory_id,
                revision=candidate.revision,
                stage=stage,
                receipt_id=receipt.receipt_id,
                reason=receipt.reason,
            )
        )
    return tuple(records)
