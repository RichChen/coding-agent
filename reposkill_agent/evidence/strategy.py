"""Compose public evidence and optional memory without owning any execution loop."""

from datetime import datetime
from typing import Any

from reposkill_agent.evidence.context import render_public_context
from reposkill_agent.evidence.locator import EvidenceLocator
from reposkill_agent.evidence.models import EvidenceState, Observation
from reposkill_agent.memory.gate import select_memory
from reposkill_agent.memory.records import MemoryRecord
from reposkill_agent.memory.source_manifest import SourcePolicy
from reposkill_agent.memory.validity import RepoFacts
from reposkill_agent.protocol.public import PublicTask, Versioned, canonical, digest


class PublicStrategyState(Versioned):
    """Versioned checkpoint containing strategy data only.

    It intentionally contains no host handles, filesystem paths, callbacks, or
    pending side effects.  Restoring this DTO is therefore a pure operation.
    """

    task_hash: str
    repo_revision: str
    memory_snapshot_id: str | None = None
    evidence_state: EvidenceState
    proposal_ids: tuple[str, ...] = ()
    receipt_cursor: str | None = None


def strategy_state_for(
    task: PublicTask,
    evidence_state: EvidenceState,
    *,
    memory_snapshot_id: str | None = None,
    proposal_ids: tuple[str, ...] = (),
    receipt_cursor: str | None = None,
) -> PublicStrategyState:
    """Build a checkpoint from already observed state without executing work."""

    return PublicStrategyState(
        task_hash=digest(canonical(task.model_dump(mode="json"))),
        repo_revision=task.repo_ref.revision,
        memory_snapshot_id=memory_snapshot_id,
        evidence_state=evidence_state,
        proposal_ids=proposal_ids,
        receipt_cursor=receipt_cursor,
    )


def serialize_strategy_state(state: PublicStrategyState) -> str:
    """Return deterministic JSON suitable for a harness event/artifact."""

    return canonical(state.model_dump(mode="json"))


def restore_strategy_state(
    task: PublicTask,
    payload: str | dict[str, Any],
    *,
    memory_snapshot_id: str | None = None,
) -> PublicStrategyState:
    """Validate and restore a checkpoint; this function performs no I/O."""

    try:
        state = (
            PublicStrategyState.model_validate_json(payload)
            if isinstance(payload, str)
            else PublicStrategyState.model_validate(payload)
        )
    except Exception as exc:
        raise ValueError("invalid_strategy_state") from exc
    expected_hash = digest(canonical(task.model_dump(mode="json")))
    if state.task_hash != expected_hash or state.repo_revision != task.repo_ref.revision:
        raise ValueError("strategy_state_task_mismatch")
    if memory_snapshot_id is not None and state.memory_snapshot_id != memory_snapshot_id:
        raise ValueError("strategy_state_memory_snapshot_mismatch")
    return state


def plan_public_step(
    task: PublicTask,
    tree: tuple[str, ...],
    *,
    state: EvidenceState | None = None,
    observations: tuple[Observation, ...] = (),
    records: tuple[MemoryRecord, ...] = (),
    facts: RepoFacts | None = None,
    source_policy: SourcePolicy | None = None,
    now: datetime | None = None,
    decision_id: str = "public-step",
) -> dict:
    """Return proposals/context; a host must execute and confirm actual injection.

    Empty memory is the no-op baseline. This is not a coding-harness integration.
    """
    decision = EvidenceLocator().decide(task, tree, state, observations)
    result = {
        "protocol_mode": task.protocol_mode,
        "locator": decision.model_dump(mode="json"),
        "public_context": render_public_context(task, decision),
        "memory_decision": None,
    }
    if records:
        if facts is None or source_policy is None or now is None:
            raise ValueError("memory_requires_facts_policy_clock")
        memory = select_memory(
            task, list(records), facts, source_policy, now, decision_id=decision_id
        )
        result["memory_decision"] = memory.model_dump(mode="json")
    return result
