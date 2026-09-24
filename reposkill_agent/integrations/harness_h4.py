"""Trusted, data-only async adapter for coding-harness H4 policy wire 0.1.

H4 gives message hashes, not observation bodies, and rejects all actions. A
reviewed public tree is bound at construction. Hashes never become code evidence.
This module intentionally imports no harness classes and performs no I/O.
"""

from __future__ import annotations

import asyncio
import json
import re
from datetime import UTC, datetime
from typing import Literal

from pydantic import Field, ValidationError

from reposkill_agent.evidence.models import EvidenceState
from reposkill_agent.evidence.strategy import (
    plan_public_step,
    restore_strategy_state,
    strategy_state_for,
)
from reposkill_agent.memory.records import MemoryRecord
from reposkill_agent.memory.source_manifest import SourcePolicy, validate_build_manifest
from reposkill_agent.memory.validity import RepoFacts
from reposkill_agent.protocol.public import (
    BoundaryError,
    Digest,
    PublicTask,
    StrictModel,
    canonical,
    decode_public_task,
    digest,
    reject_oracle,
    safe_relative,
)

MAX_POLICY_BYTES = 65536
ADAPTER_VERSION = "reposkill-h4-1"
# Union of this project's public boundary and H4's actual forbidden fields.
H4_FORBIDDEN = {"oracle", "answer", "expected", "futuresolution"}


def wire_data(value: object) -> dict:
    """Copy finite, bounded JSON; error messages never echo rejected payloads."""
    try:
        text = json.dumps(value, ensure_ascii=False, allow_nan=False)
        if len(text.encode()) > MAX_POLICY_BYTES:
            raise ValueError("quota")
        data = json.loads(text)
        reject_oracle(data)

        def walk(node):
            if isinstance(node, dict):
                for key, child in node.items():
                    if re.sub(r"[^a-z]", "", key.lower()) in H4_FORBIDDEN:
                        raise ValueError("private")
                    walk(child)
            elif isinstance(node, list):
                for child in node:
                    walk(child)

        walk(data)
        if not isinstance(data, dict):
            raise ValueError("object")
        return data
    except (ValueError, TypeError, RecursionError):
        raise BoundaryError("invalid_h4_public_json") from None


class MessageDigest(StrictModel):
    role: Literal["system", "user", "assistant", "tool"]
    sha256: Digest


class H4Input(StrictModel):
    schema_version: str
    task: dict
    observations: tuple[MessageDigest, ...]
    repo_revision: str
    budget: dict
    state: dict


class H4State(StrictModel):
    schema_version: Literal["0.1"] = "0.1"
    adapter_version: Literal["reposkill-h4-1"] = ADAPTER_VERSION
    binding_hash: Digest
    calls: int = Field(ge=1)
    strategy: dict
    message_digest: Digest
    tool_history_seen: bool = False


def harness_public_task(task: PublicTask) -> dict:
    """Explicit H3 PublicTask projection; it never accepts EvaluationSpec.

    H3 enforces these two limits. Token, cost, retry, and tool limits must be
    frozen in the host config separately, not silently translated into a ledger.
    """
    if task.protocol_mode != "realistic":
        raise BoundaryError("realistic_h4_required")
    return wire_data(
        {
            "task_id": task.task_id,
            "description": task.issue_text,
            "repo_id": task.repo_ref.repo_id,
            "base_revision": task.repo_ref.revision,
            "workspace_profile": task.execution_profile_ref,
            "budget": {
                "max_model_calls": task.budget.model_calls,
                "total_timeout_seconds": task.budget.wall_seconds,
            },
            "public_context": task.public_context.model_dump(mode="json"),
        }
    )


class RepoSkillH4Plugin:
    """Structurally implements ``async PolicyPlugin.decide(dict) -> dict``.

    All mutable per-run state is returned to the host, never retained on self.
    The optional memory is a frozen, independently validated public snapshot.
    H4 cannot refresh facts after tools; memory is withheld once a tool is seen.
    """

    name = "reposkill-public"
    schema_version = "0.1"

    def __init__(
        self,
        task: PublicTask,
        tree: tuple[str, ...],
        *,
        enabled: bool = True,
        records: tuple[MemoryRecord, ...] = (),
        facts: RepoFacts | None = None,
        source_policy: SourcePolicy | None = None,
    ):
        self._task, _ = decode_public_task(task.model_dump(mode="json"))
        if self._task.protocol_mode != "realistic":
            raise BoundaryError("realistic_h4_required")
        self._tree = tuple(sorted({safe_relative(p) for p in tree}))
        if len(self._tree) > 2000:
            raise BoundaryError("tree_requires_bounded_host_view")
        self._enabled = enabled
        self._records = tuple(MemoryRecord.model_validate(r.model_dump()) for r in records)
        self._facts = RepoFacts.model_validate(facts.model_dump()) if facts else None
        self._policy = (
            SourcePolicy.model_validate(source_policy.model_dump()) if source_policy else None
        )
        if records:
            if self._facts is None or self._policy is None:
                raise BoundaryError("memory_requires_facts_policy")
            validate_build_manifest(self._policy)
            if self._task.task_id not in self._policy.target_task_ids:
                raise BoundaryError("target_missing_from_source_policy")
        self._memory_snapshot = digest(
            canonical([r.model_dump(mode="json") for r in self._records])
        )
        self._binding = digest(
            canonical(
                {
                    "adapter": ADAPTER_VERSION,
                    "task": self._task.model_dump(mode="json"),
                    "tree": self._tree,
                    "memory": self._memory_snapshot,
                    "facts": self._facts.model_dump(mode="json") if self._facts else None,
                    "policy": self._policy.model_dump(mode="json") if self._policy else None,
                    "enabled": enabled,
                }
            )
        )

    def _input(self, raw: dict) -> H4Input:
        data = wire_data(raw)
        version = data.get("schema_version")
        if not isinstance(version, str) or not re.fullmatch(r"0\.\d+", version):
            raise BoundaryError("unsupported_h4_schema")
        extras = set(data) - set(H4Input.model_fields)
        if extras and version == "0.1":
            raise BoundaryError("unknown_h4_field")
        try:
            parsed = H4Input.model_validate(
                {k: v for k, v in data.items() if k in H4Input.model_fields}
            )
        except ValidationError:
            raise BoundaryError("invalid_h4_input") from None
        if parsed.repo_revision != self._task.repo_ref.revision:
            raise BoundaryError("h4_revision_mismatch")
        actual_task = parsed.task
        # AgentLoop passes exactly this minimal shape. run_h3 wraps a serialized
        # H3 PublicTask in issue_text; validate that whole public object as well.
        if set(actual_task) == {"task_id", "issue_text"}:
            if actual_task["task_id"] != self._task.task_id:
                raise BoundaryError("h4_task_mismatch")
            issue = actual_task["issue_text"]
            if issue == self._task.issue_text:
                return parsed
            try:
                actual_task = wire_data(json.loads(issue))
            except (ValueError, TypeError):
                raise BoundaryError("h4_task_mismatch") from None
        if actual_task != harness_public_task(self._task):
            raise BoundaryError("h4_task_mismatch")
        return parsed

    async def decide(self, policy_input: dict) -> dict:
        # Cooperative cancellation point; no blocking I/O or nested event loop.
        await asyncio.sleep(0)
        data = self._input(policy_input)
        if not self._enabled:
            return dict(
                schema_version="0.1", candidates=[], state={}, events=[], action_proposals=[]
            )
        previous = None
        count = 0
        tool_seen = any(o.role == "tool" for o in data.observations)
        if data.state:
            try:
                saved = H4State.model_validate(data.state)
                if saved.binding_hash != self._binding:
                    raise ValueError("binding")
                previous = restore_strategy_state(
                    self._task, saved.strategy, memory_snapshot_id=self._memory_snapshot
                )
                if previous.evidence_state.repo_revision != data.repo_revision:
                    raise ValueError("evidence revision")
                # H4 never supplied observation bodies or injection receipts.
                if previous.evidence_state.observations or previous.receipt_cursor is not None:
                    raise ValueError("unsupported evidence")
                count = saved.calls
                tool_seen = tool_seen or saved.tool_history_seen
            except (ValueError, TypeError):
                raise BoundaryError("invalid_h4_checkpoint") from None
        decision_id = digest(f"{self._binding}:{count}")
        result = plan_public_step(
            self._task,
            self._tree,
            state=previous.evidence_state if previous else None,
            records=() if tool_seen else self._records,
            facts=self._facts,
            source_policy=self._policy,
            now=datetime.now(UTC),
            decision_id=decision_id,
        )
        locator = result["locator"]
        proposals = locator["proposals"]
        candidates = []
        if proposals:
            candidates.append(
                {
                    "id": decision_id + "-evidence-plan",
                    "text": canonical(
                        {
                            "basis": "public_issue_and_reviewed_tree_only",
                            "suggested_reads_or_searches": proposals,
                            "limitations": "No code observed; proposals have not been executed.",
                        }
                    ),
                    "source": "reposkill:public-evidence-locator",
                    "reason": "request_public_evidence",
                    "valid": True,
                    "priority": 0,
                    "repo_revision": data.repo_revision,
                }
            )
        memory = result["memory_decision"]
        if memory:
            for candidate in memory["candidates"]:
                candidates.append(
                    {
                        "id": candidate["candidate_id"],
                        "text": candidate["text"],
                        "source": "reposkill:memory:" + candidate["memory_id"],
                        "reason": "public_provenance_and_dependency_checks_passed",
                        "valid": True,
                        "priority": 1,
                        "repo_revision": data.repo_revision,
                    }
                )
        proposed_ids = tuple(
            sorted(
                set(
                    (previous.proposal_ids if previous else ())
                    + tuple(p["proposal_id"] for p in proposals)
                )
            )
        )
        checkpoint = strategy_state_for(
            self._task,
            EvidenceState.model_validate(locator["state"]),
            memory_snapshot_id=self._memory_snapshot,
            proposal_ids=proposed_ids,
        )
        state = H4State(
            binding_hash=self._binding,
            calls=count + 1,
            strategy=checkpoint.model_dump(mode="json"),
            message_digest=digest(canonical([o.model_dump() for o in data.observations])),
            tool_history_seen=tool_seen,
        )
        return wire_data(
            {
                "schema_version": "0.1",
                "candidates": candidates,
                "state": state.model_dump(mode="json"),
                "action_proposals": proposals,
                "events": [
                    {
                        "type": "reposkill.policy_decision",
                        "decision_id": decision_id,
                        "locator_status": locator["status"],
                        "proposal_status": "submitted_not_executed",
                        "body_observations_available": False,
                        "memory_status": "withheld_after_tool_history"
                        if tool_seen
                        else "frozen_snapshot",
                        "memory_items": memory["items"] if memory else [],
                        "external_model_calls": 0,
                        "tool_calls_executed": 0,
                        "injection_status": "await_host_record",
                        "observed_following": "unknown",
                    }
                ],
            }
        )
