from pathlib import Path
from types import SimpleNamespace

import pytest

import reposkill_agent.memory.lightweight_snapshot as lightweight_snapshot
from reposkill_agent.eval.graph_runner import TaskGraphRunner
from reposkill_agent.llm.prompts import format_memory_hints
from reposkill_agent.memory.lightweight_snapshot import (
    load_lightweight_snapshot,
    prepare_lightweight_injection,
)

HARNESS = Path("D:/crq/src/coding-harness/docs/upgrade/evidence/A5-real240-77-harness-preflight")


def test_frozen_snapshot_loads_only_contract_fields_and_keeps_smoke_boundary():
    snapshot = load_lightweight_snapshot(
        HARNESS / "memory-snapshot.jsonl",
        HARNESS / "memory-snapshot-manifest.json",
        HARNESS / "memory-consumption-contract.json",
    )
    assert snapshot.internal_usable_count == 11
    assert snapshot.full_grader_validated_count == 0
    assert snapshot.promotion_permitted is False
    assert len(snapshot.records) == 11
    assert all("source_record" not in row.raw_view() for row in snapshot.records)


@pytest.mark.parametrize("variant", ["B1", "B2", "B3"])
def test_augmented_variants_prepare_hints_and_complete_offline_receipts(variant):
    snapshot = load_lightweight_snapshot(
        HARNESS / "memory-snapshot.jsonl",
        HARNESS / "memory-snapshot-manifest.json",
        HARNESS / "memory-consumption-contract.json",
    )
    plan = prepare_lightweight_injection(
        snapshot,
        variant,
        decision_id=f"offline-{variant}",
        repo="django/django",
        base_revision=(
            next(row.base_revision for row in snapshot.records if row.repo == "django/django")
            if variant == "B3"
            else None
        ),
        source_tree_hash=(
            next(row.source_tree_hash for row in snapshot.records if row.repo == "django/django")
            if variant == "B3"
            else None
        ),
    )
    expected_count = 1 if variant == "B3" else 2
    assert plan.injected_count == len(plan.hints) == len(plan.receipts) == expected_count
    for hint, receipt in zip(plan.hints, plan.receipts, strict=True):
        assert receipt.variant == variant
        assert receipt.snapshot_hash == snapshot.snapshot_hash
        assert receipt.requested_hash == hint["requested_hash"]
        assert receipt.requested_bytes == len(hint["text"].encode("utf-8"))
        assert receipt.status == "prepared_not_injected"
        assert receipt.actual_hash is None
        assert receipt.model_operation_id is None
        assert receipt.model_attempt_id is None


def test_b0_never_prepares_a_memory_hint_or_receipt():
    snapshot = load_lightweight_snapshot(
        HARNESS / "memory-snapshot.jsonl",
        HARNESS / "memory-snapshot-manifest.json",
        HARNESS / "memory-consumption-contract.json",
    )
    plan = prepare_lightweight_injection(snapshot, "B0", decision_id="offline-B0")
    assert plan.injected_count == 0
    assert plan.hints == ()
    assert plan.receipts == ()


@pytest.mark.parametrize("variant, expected", [("B0", 0), ("B1", 2), ("B2", 2), ("B3", 1)])
def test_graph_runner_runtime_path_delivers_only_configured_variant_hints(variant, expected):
    snapshot = load_lightweight_snapshot(
        HARNESS / "memory-snapshot.jsonl",
        HARNESS / "memory-snapshot-manifest.json",
        HARNESS / "memory-consumption-contract.json",
    )
    django_row = next(row for row in snapshot.records if row.repo == "django/django")
    runner = TaskGraphRunner(
        use_memory=True,
        lightweight_memory_snapshot=snapshot,
        lightweight_memory_variant=variant,
        lightweight_memory_repo="django/django",
        lightweight_memory_base_revision=(django_row.base_revision if variant == "B3" else None),
        lightweight_memory_source_tree_hash=(
            django_row.source_tree_hash if variant == "B3" else None
        ),
    )
    stats = {"memory_candidate_count": 0, "memory_injected_count": 0, "memory_retrieval_count": 0}
    hints = runner._resolve_memory_hints(
        SimpleNamespace(id="offline-target"), "unused", [], None, stats
    )
    assert len(hints) == expected
    assert stats["memory_injected_count"] == expected
    assert stats["memory_injection_receipt_status"] == "prepared_not_injected"
    assert stats["memory_full_grader_validated"] is False
    assert all(hint["injection_receipt"]["status"] == "prepared_not_injected" for hint in hints)
    if variant != "B0":
        prompt_memory = format_memory_hints(hints)
        assert "LightweightMemoryReference:" in prompt_memory
        assert "receipt_status: prepared_not_injected" in prompt_memory


def test_b3_fails_closed_without_current_repository_fingerprint():
    snapshot = load_lightweight_snapshot(
        HARNESS / "memory-snapshot.jsonl",
        HARNESS / "memory-snapshot-manifest.json",
        HARNESS / "memory-consumption-contract.json",
    )
    plan = prepare_lightweight_injection(
        snapshot, "B3", decision_id="missing-fingerprint", repo="django/django"
    )
    assert plan.injected_count == 0


def test_loader_rejects_snapshot_hash_mismatch(monkeypatch):
    class MismatchHash:
        def __init__(self, *args, **kwargs):
            pass

        def update(self, *args, **kwargs):
            pass

        def hexdigest(self):
            return "0" * 64

    monkeypatch.setattr(lightweight_snapshot.hashlib, "sha256", MismatchHash)
    with pytest.raises(ValueError, match="snapshot_hash_mismatch"):
        load_lightweight_snapshot(
            HARNESS / "memory-snapshot.jsonl",
            HARNESS / "memory-snapshot-manifest.json",
            HARNESS / "memory-consumption-contract.json",
        )
