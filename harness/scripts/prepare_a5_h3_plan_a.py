"""Prepare the offline H3 Plan A handoff without running any pilot work."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def file_ref(path: Path) -> dict:
    return {"path": str(path.resolve()), "sha256": sha(path)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--readiness", type=Path, required=True)
    parser.add_argument("--contract-audit", type=Path, required=True)
    parser.add_argument("--contract-resolution", type=Path, required=True)
    parser.add_argument("--receipts", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--pilot-matrix", type=Path, required=True)
    parser.add_argument("--harness-contract", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    output = args.output.resolve()
    if output.exists():
        raise SystemExit(f"refusing to overwrite existing output: {output}")
    output.mkdir(parents=True)

    readiness = load(args.readiness)
    contract_audit = load(args.contract_audit)
    contract_resolution = load(args.contract_resolution)
    receipts = load(args.receipts)
    merged_manifest = load(args.manifest)
    matrix = load(args.pilot_matrix)

    rows = receipts["rows"]
    if len(rows) != 20 or len({row["task_id"] for row in rows}) != 20:
        raise ValueError("-07 receipts must contain exactly 20 unique targets")
    if readiness.get("assigned") != 20 or readiness.get("grader_ready") != 19:
        raise ValueError("-07 readiness must be the expected 20/19 merge")
    if contract_audit["task_id"] != "django__django-13265":
        raise ValueError("unexpected Django contract audit target")

    provenance = {entry["task_id"]: entry for entry in merged_manifest["provenance"]}
    blocked_id = "django__django-13265"
    f2p_ids = contract_resolution["f2p_method_ids"]
    disposition = {
        "schema": "a5.h3.plan-a-disposition.v1",
        "plan": "A",
        "status": "frozen_offline_blocked_on_contract_target",
        "experiment_id": matrix["experiment_id"],
        "matrix": {
            "assigned": 240,
            "targets": 20,
            "variants": ["B0", "B1", "B2", "B3"],
            "repeats": 3,
            "seeds": [42, 43, 44],
            "rule": "retain the exact 20 x 4 x 3 denominator; do not delete or rewrite targets",
        },
        "django_13265": {
            "status": "contract_blocker",
            "grader_ready": False,
            "future_assignment_rows": 12,
            "future_row_statuses": ["blocked", "invalid_env", "not_run"],
            "preserve_f2p_method_ids": f2p_ids,
            "expected_f2p_count": contract_audit["expected_f2p_count"],
            "actual_baseline_failed": contract_audit["actual_baseline_failed"],
            "unexpected_baseline_passed": contract_audit["unexpected_baseline_passed"],
            "forbidden_actions": ["delete_f2p_id", "rewrite_test_identity", "mark_grader_ready", "remove_from_denominator"],
        },
        "source_evidence": {
            "preflight_48_contract_resolution": file_ref(args.contract_resolution),
            "readiness_07": file_ref(args.readiness),
            "django_contract_audit_07": file_ref(args.contract_audit),
            "pilot_matrix_lock": file_ref(args.pilot_matrix),
            "harness_contract": file_ref(args.harness_contract),
        },
        "model_calls": 0,
        "paid": False,
        "provider_started": False,
        "memory_build_started": False,
        "pilot_started": False,
    }
    save(output / "plan-a-disposition.json", disposition)

    ledger_rows = []
    ready_rows = []
    for row in rows:
        task_id = row["task_id"]
        task_dir = args.receipts.resolve().parent / "tasks" / task_id
        calibration = task_dir / "calibration.json"
        provenance_row = provenance[task_id]
        source_attempt = Path(provenance_row["source_attempt"])
        ledger_row = {
            "canonical_id": task_id,
            "grader_ready": bool(row.get("grader_ready")),
            "receipt": file_ref(calibration),
            "attempt": file_ref(source_attempt / "receipts.json"),
            "source_attempt": str(source_attempt),
        }
        if task_id == blocked_id:
            ledger_row["reason"] = "contract_blocker: declared four F2P identities do not match fixed-base baseline behavior; two fail and two pass"
            ledger_row["future_disposition"] = "12 matrix rows remain in denominator and are blocked/invalid_env/not_run until contract revision and rebaseline"
        else:
            ready_rows.append(row)
        ledger_rows.append(ledger_row)
    save(output / "pilot20-grader-ledger.json", {
        "schema": "a5.pilot20-grader-ledger.plan-a.v1",
        "assigned": 20,
        "grader_ready": 19,
        "contract_blockers": [blocked_id],
        "canonical_bound": False,
        "rows": ledger_rows,
    })

    blocker_payload = {
        "canonical_id": blocked_id,
        "contract_audit": file_ref(args.contract_audit),
        "contract_resolution": file_ref(args.contract_resolution),
        "f2p_method_ids": f2p_ids,
        "decision": contract_resolution["decision"],
    }
    blocker_bytes = json.dumps(blocker_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ready_evidence = []
    for row in ready_rows:
        ready_evidence.append({
            "canonical_id": row["task_id"],
            "grader_ready": True,
            "calibration_receipt": file_ref(args.receipts.resolve().parent / "tasks" / row["task_id"] / "calibration.json"),
            "collection_evidence": {
                "path": row["collection_evidence_ref"],
                "sha256": row["collection_evidence_sha256"],
            },
            "known_good_receipt": {
                "path": row["known_good_binding"]["receipt_ref"],
                "sha256": row["known_good_binding"]["receipt_sha256"],
            },
            "attempt": {
                "path": provenance[row["task_id"]]["source_attempt"],
                "receipts_sha256": provenance[row["task_id"]]["source_attempt_sha256"],
            },
        })
    save(output / "h3-input-package.json", {
        "schema": "a5.h3-input-package.plan-a.v1",
        "purpose": "offline agent binding input only; no provider/model/pilot authorization",
        "experiment_id": matrix["experiment_id"],
        "matrix_lock": file_ref(args.pilot_matrix),
        "ready_targets": ready_evidence,
        "ready_target_count": len(ready_evidence),
        "django_13265_blocker": {
            "status": "contract_blocker",
            "grader_ready": False,
            "decision_hash": hashlib.sha256(blocker_bytes).hexdigest(),
            "evidence": blocker_payload,
        },
        "binding_rules": [
            "bind only the 19 ready target evidence sets",
            "retain django__django-13265 in the 20-target denominator as blocked",
            "do not bind canonical or start any run from this package",
            "recheck both source fingerprints after both repositories finish changes",
        ],
        "model_calls": 0,
        "paid": False,
        "canonical_bound": False,
    })

    pending = {
        "schema": "a5.h3-harness-pending.plan-a.v1",
        "contract_ref": file_ref(args.harness_contract),
        "items": [
            {
                "id": "agent_b0_b3_semantics",
                "status": "pending_agent",
                "need": "agent-side B0/B1/B2/B3 runtime semantics, memory view, injection location, and injection receipt schema",
            },
            {
                "id": "agent_target_binding",
                "status": "pending_agent",
                "need": "agent-side canonical_id/agent_task_id/public_task/base mapping and 20-target grader readiness consumption",
            },
            {
                "id": "agent_consumption_manifest",
                "status": "pending_agent",
                "need": "agent-side manifest/hash for the allowed validated_lightweight memory snapshot",
            },
            {
                "id": "matrix_coverage_crosscheck",
                "status": "pending_agent",
                "need": "agent-side confirmation of unchanged 20 x B0-B3 x seed 42/43/44 coverage (240 rows)",
            },
            {
                "id": "dual_fingerprint_refreeze",
                "status": "must_refreeze_after_both_sides_change",
                "need": "recompute and freeze harness and coding-agent source fingerprints after both sides finish H3 changes; current pending fingerprint is not an H3 authorization",
            },
            {
                "id": "h3_manifest_hash_recheck",
                "status": "pending_both_sides",
                "need": "cross-check agent package hashes against this handoff, model binding, matrix lock, and receipt schemas",
            },
            {
                "id": "receipt_importer",
                "status": "pending_harness",
                "need": "final B0-B3 injection/grader/cleanup/usage receipt importer validation before any real run",
            },
            {
                "id": "paid_authorization",
                "status": "not_requested",
                "need": "explicit paid pilot authorization remains required; this Plan A package grants none",
            },
        ],
        "model_calls": 0,
        "paid": False,
        "pilot_started": False,
    }
    save(output / "pending.json", pending)

    save(output / "readiness.json", {
        "schema": "a5.h3-plan-a-readiness.v1",
        "status": "blocked_pending_agent_h3_and_django_contract",
        "plan_a": True,
        "assigned": 20,
        "grader_ready": 19,
        "contract_blockers": [blocked_id],
        "canonical_bound": False,
        "model_calls": 0,
        "paid": False,
        "provider_started": False,
        "memory_build_started": False,
        "pilot_started": False,
    })

    manifest = {
        path.relative_to(output).as_posix(): sha(path)
        for path in sorted(output.rglob("*"))
        if path.is_file() and path.name != "artifact-manifest.json"
    }
    save(output / "artifact-manifest.json", manifest)


if __name__ == "__main__":
    main()
