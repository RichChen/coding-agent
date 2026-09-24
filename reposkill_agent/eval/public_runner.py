"""Small deterministic runner for walking the public strategy contract offline."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from pydantic import Field

from reposkill_agent.evidence.models import EvidenceState, Observation
from reposkill_agent.evidence.strategy import (
    plan_public_step,
    serialize_strategy_state,
    strategy_state_for,
)
from reposkill_agent.memory.records import MemoryRecord
from reposkill_agent.memory.source_manifest import SourcePolicy
from reposkill_agent.memory.validity import RepoFacts
from reposkill_agent.protocol.public import PublicTask, StrictModel, Versioned


class PublicRunRound(StrictModel):
    round_id: int = Field(ge=0)
    result: dict
    state: str


class PublicRunResult(Versioned):
    protocol_mode: str
    rounds: tuple[PublicRunRound, ...]
    external_model_calls: int = 0
    tool_calls_executed: int = 0


def run_public_rounds(
    task: PublicTask,
    tree: tuple[str, ...],
    observation_rounds: Iterable[tuple[Observation, ...]] = (),
    *,
    records: tuple[MemoryRecord, ...] = (),
    facts: RepoFacts | None = None,
    source_policy: SourcePolicy | None = None,
    now: datetime | None = None,
    memory_snapshot_id: str | None = None,
) -> PublicRunResult:
    """Run pure locator/gate rounds with fixture-supplied observations.

    ``observation_rounds`` models a host returning read/search results.  The
    function does not execute a tool, patch, test, model call, or filesystem
    operation and reports those counters explicitly as zero.
    """

    if task.protocol_mode != "realistic":
        raise ValueError("realistic_public_runner_required")
    state: EvidenceState | None = None
    rounds: list[PublicRunRound] = []
    for index, observations in enumerate(observation_rounds):
        result = plan_public_step(
            task,
            tree,
            state=state,
            observations=observations,
            records=records,
            facts=facts,
            source_policy=source_policy,
            now=now,
            decision_id=f"public-round-{index}",
        )
        locator_state = EvidenceState.model_validate(result["locator"]["state"])
        decision_ids = tuple(p["proposal_id"] for p in result["locator"]["proposals"])
        checkpoint = strategy_state_for(
            task,
            locator_state,
            memory_snapshot_id=memory_snapshot_id,
            proposal_ids=decision_ids,
        )
        rounds.append(
            PublicRunRound(
                round_id=index,
                result=result,
                state=serialize_strategy_state(checkpoint),
            )
        )
        state = locator_state
    return PublicRunResult(protocol_mode=task.protocol_mode, rounds=tuple(rounds))
