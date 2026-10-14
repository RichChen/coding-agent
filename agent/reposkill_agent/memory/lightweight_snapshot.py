"""Bounded runtime adapter for externally validated lightweight A5 snapshots.

These records are deliberately not ``MemoryRecord(status="validated")``: the
harness receipt scope is a public smoke, not this agent's full independent grader.
Only fields explicitly allowed by the harness consumption contract are retained.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from reposkill_agent.protocol.public import Digest, StrictModel, canonical, digest

LIGHTWEIGHT_FIELDS = frozenset(
    {
        "source_id",
        "repo",
        "base_revision",
        "source_tree_hash",
        "transport_image_digest",
        "public_input_sha256",
        "trajectory_sha256",
        "validation_receipt_sha256",
        "candidate_delta_sha256",
        "validation_scope",
        "record_state",
        "snapshot_hash",
        "line_sha256",
    }
)
PRIVATE_OR_PROMOTION_FIELDS = frozenset(
    {
        "gold_patch",
        "test_patch",
        "FAIL_TO_PASS",
        "PASS_TO_PASS",
        "hidden_tests",
        "private_grader_output",
        "full_grader_validated",
        "status",
        "validation",
        "last_validated_at",
        "dependency_mapping_complete",
    }
)


class LightweightMemoryView(StrictModel):
    source_id: str = Field(min_length=1)
    repo: str = Field(min_length=1)
    base_revision: str = Field(min_length=7)
    source_tree_hash: Digest
    transport_image_digest: str = Field(min_length=1)
    public_input_sha256: Digest
    trajectory_sha256: Digest
    validation_receipt_sha256: Digest
    candidate_delta_sha256: Digest
    validation_scope: Literal["public_independent_smoke_receipt"]
    record_state: Literal["validated_lightweight"]
    snapshot_hash: Digest
    line_sha256: Digest

    @property
    def memory_id(self) -> str:
        return "a5-lightweight:" + self.source_id

    def raw_view(self) -> dict:
        """B1 view: the exact contract-allowlisted references, never trajectory text."""
        return self.model_dump(mode="json")

    def structured_view(self) -> dict:
        """B2/B3 view: grouped public provenance and validation references."""
        return {
            "kind": "validated_lightweight_reference",
            "source": {
                "source_id": self.source_id,
                "repo": self.repo,
                "base_revision": self.base_revision,
                "source_tree_hash": self.source_tree_hash,
            },
            "evidence": {
                "public_input_sha256": self.public_input_sha256,
                "trajectory_sha256": self.trajectory_sha256,
                "validation_receipt_sha256": self.validation_receipt_sha256,
                "candidate_delta_sha256": self.candidate_delta_sha256,
                "transport_image_digest": self.transport_image_digest,
            },
            "validation_scope": self.validation_scope,
            "record_state": self.record_state,
            "snapshot_hash": self.snapshot_hash,
            "line_sha256": self.line_sha256,
        }


class LightweightMemorySnapshot(StrictModel):
    view_type: Literal["a5.agent-lightweight-memory-view.v1"]
    snapshot_hash: Digest
    source_manifest_hash: Digest
    records: tuple[LightweightMemoryView, ...]
    internal_usable_count: int = Field(ge=0)
    full_grader_validated_count: Literal[0] = 0
    promotion_permitted: Literal[False] = False

    @model_validator(mode="after")
    def consistent(self):
        if self.internal_usable_count != len(self.records):
            raise ValueError("lightweight_internal_count_mismatch")
        if any(row.snapshot_hash != self.snapshot_hash for row in self.records):
            raise ValueError("lightweight_snapshot_binding_mismatch")
        if len({row.source_id for row in self.records}) != len(self.records):
            raise ValueError("duplicate_lightweight_source")
        return self


class PreparedInjectionReceipt(StrictModel):
    """Complete receipt envelope before any host/model operation occurs."""

    receipt_type: Literal["a5.lightweight-injection-receipt.v1"]
    receipt_id: str
    decision_id: str
    candidate_id: str
    memory_id: str
    variant: Literal["B1", "B2", "B3"]
    snapshot_hash: Digest
    requested_hash: Digest
    requested_bytes: int = Field(ge=1)
    status: Literal["prepared_not_injected"]
    actual_hash: None = None
    model_operation_id: None = None
    model_attempt_id: None = None
    reason: Literal["offline_preview_no_host_operation"]


class LightweightInjectionPlan(StrictModel):
    plan_type: Literal["a5.lightweight-injection-plan.v1"]
    decision_id: str
    variant: Literal["B0", "B1", "B2", "B3"]
    snapshot_hash: Digest
    hints: tuple[dict, ...]
    receipts: tuple[PreparedInjectionReceipt, ...]
    injected_count: int = Field(ge=0)

    @model_validator(mode="after")
    def receipt_count(self):
        if self.injected_count != len(self.hints) or self.injected_count != len(self.receipts):
            raise ValueError("lightweight_injection_plan_count_mismatch")
        if self.variant == "B0" and self.injected_count:
            raise ValueError("B0_memory_injection_forbidden")
        return self


def load_lightweight_snapshot(
    snapshot_path: str | Path,
    manifest_path: str | Path,
    contract_path: str | Path,
) -> LightweightMemorySnapshot:
    """Reconstruct only contract-allowlisted metadata and verify all freeze hashes."""
    snapshot_path, manifest_path, contract_path = map(
        Path, (snapshot_path, manifest_path, contract_path)
    )
    raw_bytes = snapshot_path.read_bytes()
    snapshot_hash = hashlib.sha256(raw_bytes).hexdigest()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    manifest_hash = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    allowed = frozenset(contract.get("agent_consumable_fields", ()))
    if allowed != LIGHTWEIGHT_FIELDS:
        raise ValueError("lightweight_contract_field_allowlist_mismatch")
    if snapshot_hash != contract.get("snapshot_hash") or snapshot_hash != manifest.get(
        "snapshot_hash"
    ):
        raise ValueError("lightweight_snapshot_hash_mismatch")
    if (
        contract.get("schema") != "a5.memory-consumption-contract.v1"
        or contract.get("record_state") != "validated_lightweight"
        or contract.get("validation_scope") != "public_independent_smoke_receipt"
        or contract.get("private_grader_run") is not False
        or contract.get("full_grader_validated") is not False
    ):
        raise ValueError("lightweight_contract_claim_boundary_mismatch")

    rows = []
    for line in raw_bytes.splitlines():
        if not line.strip():
            continue
        source = json.loads(line)
        # The frozen transport nests allowed values under bindings/hashes. Project only
        # named contract fields; ignore source_record, source_dir and all host-only data.
        bindings, hashes = source.get("bindings", {}), source.get("hashes", {})
        view = {
            "source_id": source.get("source_id"),
            "repo": bindings.get("repo"),
            "base_revision": bindings.get("base_revision"),
            "source_tree_hash": bindings.get("source_tree_hash"),
            "transport_image_digest": bindings.get("transport_image_digest"),
            "public_input_sha256": hashes.get("public_input_sha256"),
            "trajectory_sha256": hashes.get("trajectory_sha256"),
            "validation_receipt_sha256": hashes.get("validation_receipt_sha256"),
            "candidate_delta_sha256": hashes.get("candidate_delta_sha256"),
            "validation_scope": source.get("validation_scope"),
            "record_state": source.get("record_state"),
            "snapshot_hash": snapshot_hash,
            "line_sha256": source.get("line_sha256"),
        }
        if set(view) != LIGHTWEIGHT_FIELDS or any(value is None for value in view.values()):
            raise ValueError("lightweight_record_missing_allowed_field")
        view["snapshot_hash"] = snapshot_hash
        rows.append(LightweightMemoryView.model_validate(view))

    if len(rows) != manifest.get("n_records") or len(rows) != 11:
        raise ValueError("lightweight_snapshot_record_count_mismatch")
    if [row.source_id for row in rows] != manifest.get("source_ids"):
        raise ValueError("lightweight_snapshot_source_order_mismatch")
    manifest_rows = {row["source_id"]: row for row in manifest.get("records", [])}
    if len(manifest_rows) != len(rows):
        raise ValueError("lightweight_snapshot_manifest_rows_mismatch")
    for row in rows:
        if manifest_rows[row.source_id].get("line_sha256") != row.line_sha256:
            raise ValueError("lightweight_snapshot_line_binding_mismatch")

    return LightweightMemorySnapshot(
        view_type="a5.agent-lightweight-memory-view.v1",
        snapshot_hash=snapshot_hash,
        source_manifest_hash=manifest_hash,
        records=tuple(rows),
        internal_usable_count=len(rows),
    )


def prepare_lightweight_injection(
    snapshot: LightweightMemorySnapshot,
    variant: Literal["B0", "B1", "B2", "B3"],
    *,
    decision_id: str,
    repo: str | None = None,
    base_revision: str | None = None,
    source_tree_hash: str | None = None,
    max_records: int = 2,
    max_bytes: int = 4096,
) -> LightweightInjectionPlan:
    """Prepare deterministic hints for AgentContext; never claims a host injection."""
    if min(max_records, max_bytes) < 0:
        raise ValueError("negative_lightweight_injection_budget")
    selected: list[tuple[LightweightMemoryView, dict, str]] = []
    used = 0
    b3_fingerprint_missing = variant == "B3" and not (repo and base_revision and source_tree_hash)
    if variant != "B0" and not b3_fingerprint_missing:
        candidates = [
            row
            for row in snapshot.records
            if (repo is None or row.repo == repo)
            and (
                variant != "B3"
                or (row.base_revision == base_revision and row.source_tree_hash == source_tree_hash)
            )
        ]
        for row in candidates:
            payload = row.raw_view() if variant == "B1" else row.structured_view()
            text = canonical(payload)
            size = len(text.encode("utf-8"))
            if len(selected) >= max_records or used + size > max_bytes:
                break
            selected.append((row, payload, text))
            used += size

    hints, receipts = [], []
    for index, (row, payload, text) in enumerate(selected):
        candidate_id = digest(f"{decision_id}:{variant}:{row.memory_id}:{row.line_sha256}")
        receipt_id = digest(f"receipt:{candidate_id}")
        hints.append(
            {
                "candidate_id": candidate_id,
                "memory_id": row.memory_id,
                "revision": 1,
                "variant": variant,
                "text": text,
                "source_hash": row.line_sha256,
                "snapshot_hash": snapshot.snapshot_hash,
                "requested_hash": digest(text),
                "reason": "lightweight_snapshot_reference",
            }
        )
        receipts.append(
            PreparedInjectionReceipt(
                receipt_type="a5.lightweight-injection-receipt.v1",
                receipt_id=receipt_id,
                decision_id=decision_id,
                candidate_id=candidate_id,
                memory_id=row.memory_id,
                variant=variant,
                snapshot_hash=snapshot.snapshot_hash,
                requested_hash=digest(text),
                requested_bytes=len(text.encode("utf-8")),
                status="prepared_not_injected",
                reason="offline_preview_no_host_operation",
            )
        )
        hints[-1]["injection_receipt"] = receipts[-1].model_dump(mode="json")
    return LightweightInjectionPlan(
        plan_type="a5.lightweight-injection-plan.v1",
        decision_id=decision_id,
        variant=variant,
        snapshot_hash=snapshot.snapshot_hash,
        hints=tuple(hints),
        receipts=tuple(receipts),
        injected_count=len(hints),
    )
