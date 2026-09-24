"""Zero-model fail-closed wiring for pilot receipts, importer, and ledger flags.

Fixture output is never a real 240 pilot run.
"""
from __future__ import annotations

import copy
import hashlib
from typing import Any

from src.eval.a5_receipts import import_pilot_receipt, validate_pilot_receipt

FIXTURE_NOW = "2026-09-22T00:00:00+00:00"


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def fixture_assignment() -> dict[str, Any]:
    return {
        "assignment_id": _sha("fixture-assignment"),
        "experiment_id": "a5-pilot-20-v1",
        "canonical_target_id": "django__django-13265",
        "agent_task_id": "a5-task-9d74ed989dbd3bb5",
        "variant": "B0",
        "repeat_id": 0,
        "seed": 42,
        "public_task_hash": _sha("fixture-public-task"),
    }


def fixture_bindings() -> dict[str, str]:
    return {
        "snapshot": _sha("fixture-memory-snapshot"),
        "model": _sha("fixture-model-binding"),
        "harness": _sha("fixture-harness-fp"),
        "agent": _sha("fixture-agent-fp"),
        "candidate": _sha("fixture-candidate"),
        "grader": _sha("fixture-grader-receipt"),
        "target_base": _sha("b2b0711b555fa292751763c2df4fe577c396f265"),
    }


def injection_ref(bindings: dict[str, str], variant: str) -> dict[str, str]:
    return {
        "source_hash": _sha(f"fixture-source-{variant}"),
        "evidence_hash": _sha(f"fixture-evidence-{variant}"),
        "snapshot_hash": bindings["snapshot"],
        "injection_receipt_hash": _sha(f"fixture-injection-{variant}"),
    }


def make_fixture_receipt(variant: str, *, bindings: dict[str, str] | None = None,
                         assignment: dict[str, Any] | None = None) -> dict[str, Any]:
    bindings = bindings or fixture_bindings()
    assignment = dict(assignment or fixture_assignment())
    assignment["variant"] = variant
    receipt = {
        "schema": "a5.pilot-run-receipt.v1",
        "assignment_id": assignment["assignment_id"],
        "experiment_id": assignment["experiment_id"],
        "canonical_target_id": assignment["canonical_target_id"],
        "agent_task_id": assignment["agent_task_id"],
        "variant": variant,
        "repeat_id": assignment["repeat_id"],
        "seed": assignment["seed"],
        "public_task_hash": assignment["public_task_hash"],
        "target_base_hash": bindings["target_base"],
        "memory_snapshot_hash": bindings["snapshot"],
        "injection_receipt_refs": [] if variant == "B0" else [injection_ref(bindings, variant)],
        "model_binding_hash": bindings["model"],
        "harness_fingerprint": bindings["harness"],
        "agent_fingerprint": bindings["agent"],
        "operation_id": f"fixture-{variant}-op",
        "attempt_ids": [f"fixture-{variant}-attempt-1"],
        "usage": {"unknown": True},
        "reservation": {"reserved_cny": "0.192"},
        "settlement": {"status": "unknown_keeps_reserve", "cost_cny": "0.192"},
        "candidate_hash": bindings["candidate"],
        "grader_receipt_ref": bindings["grader"],
        "cleanup_verified": True,
        "status": "fixture_accepted",
        "failure_reason": None,
        "created_at": FIXTURE_NOW,
        "finished_at": FIXTURE_NOW,
        "fixture_only": True,
        "model_calls": 0,
        "paid": False,
    }
    return receipt


def expected_kwargs(assignment: dict[str, Any], bindings: dict[str, str]) -> dict[str, Any]:
    return {
        "expected_assignment": assignment,
        "expected_snapshot_hash": bindings["snapshot"],
        "expected_model_binding": bindings["model"],
        "expected_harness_fingerprint": bindings["harness"],
        "expected_agent_fingerprint": bindings["agent"],
    }


def mutate(receipt: dict[str, Any], **changes: Any) -> dict[str, Any]:
    row = copy.deepcopy(receipt)
    for key, value in changes.items():
        row[key] = value
    return row


def run_fail_closed_cases() -> dict[str, Any]:
    bindings = fixture_bindings()
    assignment = fixture_assignment()
    cases = []

    def check(name: str, receipt: dict[str, Any], *, expect_error: str | None, assignment_row=None):
        kwargs = expected_kwargs(assignment_row or {**assignment, "variant": receipt["variant"]}, bindings)
        validation = validate_pilot_receipt(receipt, **kwargs)
        imported = None
        error = None
        try:
            imported = import_pilot_receipt(receipt, **kwargs)
        except ValueError as exc:
            error = str(exc)
        ok = (expect_error is None and validation.valid and imported is not None) or (
            expect_error is not None and not validation.valid and expect_error in validation.errors
        )
        cases.append({
            "name": name,
            "valid": validation.valid,
            "errors": list(validation.errors),
            "imported": imported is not None,
            "import_error": error,
            "expect_error": expect_error,
            "ok": ok,
        })

    for variant in ("B0", "B1", "B2", "B3"):
        check(f"{variant}_happy", make_fixture_receipt(variant, bindings=bindings, assignment=assignment), expect_error=None)
    check("B0_has_injection", mutate(make_fixture_receipt("B0", bindings=bindings, assignment=assignment),
                                     injection_receipt_refs=[injection_ref(bindings, "B0")]),
          expect_error="B0_must_have_no_injection")
    check("B1_missing_injection", mutate(make_fixture_receipt("B1", bindings=bindings, assignment=assignment),
                                         injection_receipt_refs=[]),
          expect_error="injection_decision_missing")
    broken_injection = make_fixture_receipt("B2", bindings=bindings, assignment=assignment)
    broken_injection["injection_receipt_refs"] = [{"source_hash": "short", "evidence_hash": bindings["snapshot"],
                                                   "snapshot_hash": bindings["snapshot"],
                                                   "injection_receipt_hash": bindings["grader"]}]
    check("B2_injection_missing_hash", broken_injection, expect_error="injection_binding")
    mismatched = make_fixture_receipt("B3", bindings=bindings, assignment=assignment)
    mismatched["canonical_target_id"] = "sympy__sympy-20154"
    check("assignment_mismatch", mismatched, expect_error="assignment_mismatch")
    drifted = mutate(make_fixture_receipt("B1", bindings=bindings, assignment=assignment),
                     memory_snapshot_hash=_sha("other-snapshot"))
    check("snapshot_drift", drifted, expect_error="snapshot_drift")
    dup = mutate(make_fixture_receipt("B1", bindings=bindings, assignment=assignment),
                 attempt_ids=["same", "same"])
    check("duplicate_attempt", dup, expect_error="duplicate_attempt")
    unknown = mutate(make_fixture_receipt("B1", bindings=bindings, assignment=assignment),
                     usage={"unknown": True}, settlement={"status": "provider_usage", "cost_cny": "0.000"})
    check("unknown_usage", unknown, expect_error="unknown_usage_must_keep_reserve")
    missing_grader = mutate(make_fixture_receipt("B1", bindings=bindings, assignment=assignment),
                            grader_receipt_ref=None)
    check("missing_grader_receipt", missing_grader, expect_error="grader_receipt_missing")
    cleanup = mutate(make_fixture_receipt("B0", bindings=bindings, assignment=assignment), cleanup_verified=False)
    check("cleanup_false", cleanup, expect_error="cleanup_false")
    paid_fixture = mutate(make_fixture_receipt("B0", bindings=bindings, assignment=assignment), paid=True)
    check("fixture_cannot_be_paid", paid_fixture, expect_error="fixture_paid")
    return {
        "schema": "a5.pilot-fixture.fail-closed.v1",
        "fixture_only": True,
        "model_calls": 0,
        "paid": False,
        "real_240_started": False,
        "generated_at": FIXTURE_NOW,
        "cases": cases,
        "all_ok": all(case["ok"] for case in cases),
    }
