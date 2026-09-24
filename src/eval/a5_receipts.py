"""Fail-closed B0-B3 host receipt schema and importer."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

VARIANTS = ("B0", "B1", "B2", "B3")
PHASES = ("build", "pilot")


def _sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


@dataclass(frozen=True)
class ReceiptValidation:
    valid: bool
    errors: tuple[str, ...]


def validate_receipt(receipt: dict[str, Any], *, expected_model_binding: str | None = None,
                     expected_source_fingerprint: str | None = None) -> ReceiptValidation:
    errors = []
    if not isinstance(receipt, dict) or receipt.get("schema") != "a5.receipt.v1":
        return ReceiptValidation(False, ("schema",))
    for key in ("task_id", "operation_id"):
        if not isinstance(receipt.get(key), str) or not receipt[key]: errors.append(key)
    for key in ("source_snapshot_hash", "model_binding_hash", "source_fingerprint"):
        if not _sha256(receipt.get(key)): errors.append(key)
    if receipt.get("phase") not in PHASES: errors.append("phase")
    if receipt.get("variant") not in VARIANTS: errors.append("variant")
    if type(receipt.get("repeat")) is not int or receipt["repeat"] < 1: errors.append("repeat")
    if expected_model_binding and receipt.get("model_binding_hash") != expected_model_binding: errors.append("model_binding_drift")
    if expected_source_fingerprint and receipt.get("source_fingerprint") != expected_source_fingerprint: errors.append("source_fingerprint_drift")
    attempts = receipt.get("model_attempts")
    if not isinstance(attempts, list): errors.append("model_attempts")
    else:
        ids = [a.get("attempt_id") for a in attempts if isinstance(a, dict)]
        if len(ids) != len(attempts) or not all(isinstance(x, str) and x for x in ids) or len(set(ids)) != len(ids): errors.append("attempt_identity")
        if any(not isinstance(a.get("component"), str) or not a.get("component") for a in attempts if isinstance(a, dict)): errors.append("attempt_component")
    injections = receipt.get("injections")
    if not isinstance(injections, list): errors.append("injections")
    elif receipt.get("variant") == "B0" and injections: errors.append("B0_must_have_no_injection")
    elif receipt.get("variant") != "B0":
        for item in injections:
            if (not isinstance(item, dict) or not _sha256(item.get("candidate_hash"))
                    or not _sha256(item.get("source_hash")) or not item.get("evidence_ref")):
                errors.append("injection_binding")
    grader = receipt.get("grader")
    if not isinstance(grader, dict) or grader.get("status") not in ("pass", "fail", "partial", "invalid_env", "missing"):
        errors.append("grader")
    ledger = receipt.get("ledger")
    if not isinstance(ledger, dict) or ledger.get("schema") != "a5.cny.ledger.v1": errors.append("ledger")
    return ReceiptValidation(not errors, tuple(dict.fromkeys(errors)))


def import_receipt(receipt: dict[str, Any], **kwargs) -> dict[str, Any]:
    validation = validate_receipt(receipt, **kwargs)
    if not validation.valid:
        raise ValueError("invalid A5 receipt: " + ",".join(validation.errors))
    result = dict(receipt)
    result["receipt_status"] = "accepted"
    result["following_claim"] = "not_inferred_from_injection"
    return result


PILOT_RECEIPT_SCHEMAS = ("a5.pilot-run-receipt.v1", "a5.pilot-run-receipt.v2")
PILOT_RECEIPT_SCHEMA = "a5.pilot-run-receipt.v1"
PILOT_SEEDS = (42, 43, 44)
PILOT_REPEAT_TO_SEED = {0: 42, 1: 43, 2: 44}
PILOT_STATUSES = (
    "planned", "running", "completed", "failed", "missing", "invalid",
    "blocked", "fixture_accepted", "fixture_rejected",
)
PILOT_REQUIRED_FIELDS = (
    "assignment_id", "experiment_id", "canonical_target_id", "agent_task_id",
    "variant", "repeat_id", "seed", "public_task_hash", "target_base_hash",
    "memory_snapshot_hash", "injection_receipt_refs", "model_binding_hash",
    "harness_fingerprint", "agent_fingerprint", "operation_id", "attempt_ids",
    "usage", "reservation", "settlement", "candidate_hash", "grader_receipt_ref",
    "cleanup_verified", "status", "failure_reason", "created_at", "finished_at",
)
PILOT_SHA_FIELDS = (
    "assignment_id", "public_task_hash", "target_base_hash", "memory_snapshot_hash",
    "model_binding_hash", "harness_fingerprint", "agent_fingerprint", "candidate_hash",
)


def _pilot_injection_ok(item: Any) -> bool:
    return (
        isinstance(item, dict)
        and _sha256(item.get("source_hash"))
        and _sha256(item.get("evidence_hash"))
        and _sha256(item.get("snapshot_hash"))
        and _sha256(item.get("injection_receipt_hash"))
    )


def validate_pilot_receipt(
    receipt: dict[str, Any],
    *,
    expected_assignment: dict[str, Any] | None = None,
    expected_snapshot_hash: str | None = None,
    expected_model_binding: str | None = None,
    expected_harness_fingerprint: str | None = None,
    expected_agent_fingerprint: str | None = None,
) -> ReceiptValidation:
    errors = []
    if not isinstance(receipt, dict) or receipt.get("schema") not in PILOT_RECEIPT_SCHEMAS:
        return ReceiptValidation(False, ("schema",))
    if receipt.get("schema") == "a5.pilot-run-receipt.v2":
        if receipt.get("protocol_version") not in ("a5-real240-v8", "a5-real240-v9"):
            errors.append("protocol_version")
        profile = receipt.get("profile")
        common_profile_ok = (isinstance(profile, dict) and profile.get("max_steps") == 35
                             and profile.get("max_model_calls") == 24
                             and profile.get("context_max_tokens") == 96_000
                             and profile.get("total_timeout_seconds") == 1200)
        v9_profile_ok = (receipt.get("protocol_version") != "a5-real240-v9" or
                         (profile.get("context_strategy") == "masking"
                          and profile.get("keep_recent_tool_results") == 4
                          and profile.get("tool_output_max_chars") == 12_000)) if isinstance(profile, dict) else False
        if not common_profile_ok or not v9_profile_ok:
            errors.append("profile")
    for key in PILOT_REQUIRED_FIELDS:
        if key not in receipt:
            errors.append(key)
    inactive = receipt.get("status") in ("planned", "blocked", "missing")
    for key in PILOT_SHA_FIELDS:
        if inactive and key == "candidate_hash":
            continue
        if not _sha256(receipt.get(key)):
            errors.append(key)
    if receipt.get("variant") not in VARIANTS:
        errors.append("variant")
    if receipt.get("repeat_id") not in PILOT_REPEAT_TO_SEED:
        errors.append("repeat_id")
    elif receipt.get("seed") != PILOT_REPEAT_TO_SEED[receipt["repeat_id"]]:
        errors.append("seed_repeat_mismatch")
    if receipt.get("seed") not in PILOT_SEEDS:
        errors.append("seed")
    if receipt.get("status") not in PILOT_STATUSES:
        errors.append("status")
    if not isinstance(receipt.get("experiment_id"), str) or not receipt.get("experiment_id"):
        errors.append("experiment_id")
    if not isinstance(receipt.get("canonical_target_id"), str) or not receipt.get("canonical_target_id"):
        errors.append("canonical_target_id")
    if not isinstance(receipt.get("agent_task_id"), str) or not receipt.get("agent_task_id"):
        errors.append("agent_task_id")
    if not inactive and (not isinstance(receipt.get("operation_id"), str) or not receipt.get("operation_id")):
        errors.append("operation_id")
    for key in ("created_at", "finished_at"):
        if not isinstance(receipt.get(key), str) or not receipt.get(key):
            errors.append(key)
    if not inactive and type(receipt.get("cleanup_verified")) is not bool:
        errors.append("cleanup_verified")

    attempts = receipt.get("attempt_ids")
    if not isinstance(attempts, list) or (not inactive and not attempts):
        errors.append("attempt_ids")
    else:
        if any(not isinstance(item, str) or not item for item in attempts):
            errors.append("attempt_ids")
        if len(set(attempts)) != len(attempts):
            errors.append("duplicate_attempt")

    injections = receipt.get("injection_receipt_refs")
    if not isinstance(injections, list):
        errors.append("injection_receipt_refs")
    elif receipt.get("variant") == "B0":
        if injections:
            errors.append("B0_must_have_no_injection")
    else:
        if injections and any(not _pilot_injection_ok(item) for item in injections):
            errors.append("injection_binding")
        if not injections and not inactive and receipt.get("injection_decision") not in (
            "not_selected", "no_relevant_memory", "rejected_invalid", "rejected_unknown"
        ):
            errors.append("injection_decision_missing")

    if inactive:
        if attempts or injections or receipt.get("operation_id") or receipt.get("candidate_hash"):
            errors.append("inactive_has_execution_evidence")
        if receipt.get("grader_receipt_ref") or receipt.get("reservation") or receipt.get("settlement"):
            errors.append("inactive_has_result_evidence")
        if receipt.get("cleanup_verified") is not None:
            errors.append("inactive_cleanup_claim")
        if expected_assignment:
            for key in ("assignment_id", "canonical_target_id", "agent_task_id", "variant", "repeat_id", "seed"):
                if expected_assignment.get(key) != receipt.get(key):
                    errors.append("assignment_mismatch")
                    break
        return ReceiptValidation(not errors, tuple(dict.fromkeys(errors)))

    usage = receipt.get("usage")
    settlement = receipt.get("settlement")
    reservation = receipt.get("reservation")
    if not isinstance(usage, dict):
        errors.append("usage")
    if not isinstance(settlement, dict) or settlement.get("status") not in ("provider_usage", "unknown_keeps_reserve"):
        errors.append("settlement")
    if not isinstance(reservation, dict) or not reservation.get("reserved_cny"):
        errors.append("reservation")
    known = (
        isinstance(usage, dict)
        and type(usage.get("prompt_tokens")) is int and usage["prompt_tokens"] >= 0
        and type(usage.get("completion_tokens")) is int and usage["completion_tokens"] >= 0
    )
    if isinstance(usage, dict) and usage.get("unknown") is True:
        known = False
    if not known and isinstance(settlement, dict) and settlement.get("status") != "unknown_keeps_reserve":
        errors.append("unknown_usage_must_keep_reserve")
    if known and isinstance(settlement, dict) and settlement.get("status") != "provider_usage":
        errors.append("known_usage_settlement")

    grader_ref = receipt.get("grader_receipt_ref")
    if grader_ref in (None, "", False) or (isinstance(grader_ref, dict) and not grader_ref):
        errors.append("grader_receipt_missing")
    elif isinstance(grader_ref, str) and not _sha256(grader_ref):
        errors.append("grader_receipt_ref")
    elif isinstance(grader_ref, dict) and not _sha256(grader_ref.get("sha256")):
        errors.append("grader_receipt_ref")

    if receipt.get("schema") == "a5.pilot-run-receipt.v2" and not inactive:
        if type(receipt.get("changed_file_count")) is not int or receipt["changed_file_count"] < 0:
            errors.append("changed_file_count")
        elif not isinstance(receipt.get("changed_paths"), list) or receipt["changed_file_count"] != len(receipt["changed_paths"]):
            errors.append("changed_paths")
        acceptance = receipt.get("acceptance")
        if not isinstance(acceptance, dict) or not isinstance(acceptance.get("required_test_nodeids"), list) \
                or not isinstance(acceptance.get("results"), list) or type(acceptance.get("all_required_passed")) is not bool:
            errors.append("acceptance")
        if receipt.get("protocol_version") == "a5-real240-v9":
            peak = receipt.get("peak_context")
            if not isinstance(peak, dict) or type(peak.get("admission_input_tokens")) is not int \
                    or type(peak.get("serialized_bytes")) is not int:
                errors.append("peak_context")

    success_statuses = ("completed", "fixture_accepted")
    if receipt.get("status") in success_statuses and receipt.get("cleanup_verified") is not True:
        errors.append("cleanup_false")
    if receipt.get("fixture_only") is True:
        if receipt.get("paid") is not False:
            errors.append("fixture_paid")
        if receipt.get("model_calls") != 0:
            errors.append("fixture_model_calls")
        if receipt.get("status") not in ("fixture_accepted", "fixture_rejected", "invalid", "missing"):
            errors.append("fixture_status")
    if expected_assignment:
        for key in ("assignment_id", "canonical_target_id", "agent_task_id", "variant", "repeat_id", "seed"):
            if expected_assignment.get(key) != receipt.get(key):
                errors.append("assignment_mismatch")
                break
        if expected_assignment.get("public_task_hash") and expected_assignment["public_task_hash"] != receipt.get("public_task_hash"):
            errors.append("assignment_mismatch")
    if expected_snapshot_hash and receipt.get("memory_snapshot_hash") != expected_snapshot_hash:
        errors.append("snapshot_drift")
    if expected_model_binding and receipt.get("model_binding_hash") != expected_model_binding:
        errors.append("model_binding_drift")
    if expected_harness_fingerprint and receipt.get("harness_fingerprint") != expected_harness_fingerprint:
        errors.append("harness_fingerprint_drift")
    if expected_agent_fingerprint and receipt.get("agent_fingerprint") != expected_agent_fingerprint:
        errors.append("agent_fingerprint_drift")
    return ReceiptValidation(not errors, tuple(dict.fromkeys(errors)))


def import_pilot_receipt(receipt: dict[str, Any], **kwargs) -> dict[str, Any]:
    validation = validate_pilot_receipt(receipt, **kwargs)
    if not validation.valid:
        raise ValueError("invalid A5 pilot receipt: " + ",".join(validation.errors))
    result = dict(receipt)
    result["receipt_status"] = "accepted"
    result["following_claim"] = "not_inferred_from_injection"
    if result.get("fixture_only") is True:
        result["pilot_claim"] = "not_a_real_pilot"
        result["paid"] = False
        result["model_calls"] = 0
    return result
