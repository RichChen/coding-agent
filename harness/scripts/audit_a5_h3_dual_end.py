"""Independently audit the offline Plan A H3 projection from both repositories."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.runtime.session import source_fingerprint


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_bytes(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def save(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def ref_check(ref: dict) -> dict:
    path = Path(ref["path"])
    actual_path = path / "receipts.json" if path.is_dir() else path
    exists = actual_path.is_file()
    actual = sha(actual_path) if exists else None
    expected = ref.get("sha256") or ref.get("receipts_sha256")
    return {
        "path": str(path),
        "checked_file": str(actual_path),
        "expected_sha256": expected,
        "actual_sha256": actual,
        "exists": exists,
        "match": exists and actual == expected,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent-dir", type=Path, required=True)
    parser.add_argument("--plan-a-dir", type=Path, required=True)
    parser.add_argument("--assignments", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--snapshot-manifest", type=Path, required=True)
    parser.add_argument("--canonical-handoff", type=Path, required=True)
    parser.add_argument("--fingerprint-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    agent_dir = args.agent_dir.resolve()
    plan = args.plan_a_dir.resolve()
    output = args.output.resolve()
    if output.exists():
        raise SystemExit(f"refusing to overwrite existing output: {output}")
    output.mkdir(parents=True)

    agent_manifest_path = agent_dir / "artifact-manifest.json"
    agent_manifest = load(agent_manifest_path)
    agent_manifest_hash = sha(agent_manifest_path)
    expected_manifest_hash = "6b31f28f82176441bfc4076965e7b1d9d9f19085076d5ee8b3636c76b1dd57dd"
    manifest_artifact_checks = []
    for artifact in agent_manifest["artifacts"]:
        path = agent_dir / artifact["path"]
        actual = sha(path) if path.is_file() else None
        manifest_artifact_checks.append({
            "path": str(path),
            "expected_sha256": artifact["sha256"],
            "actual_sha256": actual,
            "match": actual == artifact["sha256"],
        })

    package = load(plan / "h3-input-package.json")
    ledger = load(plan / "pilot20-grader-ledger.json")
    disposition = load(plan / "plan-a-disposition.json")
    canonical_bindings = load(agent_dir / "canonical-target-bindings.json")
    coverage_projection = load(agent_dir / "assignment-coverage.json")
    snapshot_binding = load(agent_dir / "lightweight-snapshot-binding.json")
    agent_readiness = load(agent_dir / "readiness.json")
    canonical_handoff = load(args.canonical_handoff)
    fingerprint_manifest = load(args.fingerprint_manifest)
    assignments = load(args.assignments)

    binding_by_id = {row["canonical_id"]: row for row in canonical_bindings["targets"]}
    package_by_id = {row["canonical_id"]: row for row in package["ready_targets"]}
    ledger_by_id = {row["canonical_id"]: row for row in ledger["rows"]}
    expected_ids = set(ledger_by_id)
    ready_ids = {row["canonical_id"] for row in package["ready_targets"]}
    blocker_id = "django__django-13265"

    evidence_rows = []
    evidence_failures = []
    for canonical_id in sorted(expected_ids):
        binding = binding_by_id.get(canonical_id)
        ledger_row = ledger_by_id[canonical_id]
        row_result = {
            "canonical_id": canonical_id,
            "ledger_grader_ready": ledger_row["grader_ready"],
            "agent_readiness": binding.get("readiness") if binding else None,
            "retained_in_240_denominator": binding.get("retained_in_240_denominator") if binding else None,
            "assignment_rows": binding.get("assignment_rows") if binding else None,
            "checks": [],
        }
        if not binding:
            row_result["checks"].append({"check": "binding_present", "pass": False})
            evidence_failures.append(canonical_id)
            evidence_rows.append(row_result)
            continue
        if canonical_id == blocker_id:
            blocker_package = package["django_13265_blocker"]["evidence"]
            blocker_contract_refs = {
                name: ref_check(blocker_package[name])
                for name in ("contract_audit", "contract_resolution")
            }
            expected_f2p = disposition["django_13265"]["preserve_f2p_method_ids"]
            checks = [
                ("blocker_readiness", binding.get("readiness") == "blocked_contract_baseline_mismatch" and not ledger_row["grader_ready"]),
                ("blocker_denominator", binding.get("retained_in_240_denominator") is True and binding.get("assignment_rows") == 12),
                ("blocker_disposition_hash", binding["contract_blocker"]["disposition"]["sha256"] == sha(plan / "plan-a-disposition.json")),
                ("blocker_f2p_ids_preserved", len(blocker_package["f2p_method_ids"]) == 4 and blocker_package["f2p_method_ids"] == expected_f2p),
                ("blocker_contract_evidence_hashes", all(item["match"] for item in blocker_contract_refs.values())),
            ]
            row_result["blocker_contract_reference_checks"] = blocker_contract_refs
            for name, passed in checks:
                row_result["checks"].append({"check": name, "pass": passed})
                if not passed:
                    evidence_failures.append(canonical_id + ":" + name)
        else:
            package_row = package_by_id.get(canonical_id)
            checks = [
                ("ready_membership", canonical_id in ready_ids and ledger_row["grader_ready"] is True and binding.get("readiness") == "grader_ready"),
                ("denominator", binding.get("retained_in_240_denominator") is True and binding.get("assignment_rows") == 12),
                ("package_calibration_receipt", package_row is not None and binding["preflight_evidence"]["calibration_receipt"] == ref_check(package_row["calibration_receipt"])),
            ]
            # Compare each reference independently against actual bytes and against the Plan A package.
            if package_row is None:
                checks[2] = ("package_calibration_receipt", False)
                ref_checks = []
            else:
                ref_checks = []
                for field in ("calibration_receipt", "collection_evidence", "known_good_receipt", "attempt"):
                    package_ref = package_row[field]
                    actual_ref = ref_check(package_ref)
                    projection_ref = binding["preflight_evidence"][field]
                    same_projection = projection_ref["path"] == package_ref["path"] and projection_ref["sha256"] == (package_ref.get("sha256") or package_ref.get("receipts_sha256"))
                    passed = actual_ref["match"] and same_projection
                    ref_checks.append({"field": field, **actual_ref, "projection_matches_package": same_projection, "pass": passed})
                    if not passed:
                        evidence_failures.append(canonical_id + ":" + field)
            row_result["reference_checks"] = ref_checks
            for name, passed in checks[:2]:
                row_result["checks"].append({"check": name, "pass": passed})
                if not passed:
                    evidence_failures.append(canonical_id + ":" + name)
            row_result["checks"].append({"check": "all_reference_hashes", "pass": bool(ref_checks) and all(item["pass"] for item in ref_checks)})
        evidence_rows.append(row_result)

    task_to_canonical = {row["agent_task_id"]: row["canonical_id"] for row in canonical_bindings["targets"]}
    combos = Counter((task_to_canonical.get(row["task_id"]), row["variant"], row["organization_seed"]) for row in assignments)
    assignment_ids = [row["assignment_id"] for row in assignments]
    coverage_checks = {
        "source_path": str(args.assignments.resolve()),
        "source_sha256": sha(args.assignments),
        "expected_source_sha256": agent_manifest["inputs"]["assignments"],
        "source_hash_match": sha(args.assignments) == agent_manifest["inputs"]["assignments"],
        "row_count": len(assignments),
        "unique_assignment_ids": len(set(assignment_ids)),
        "unique_cells": len(combos),
        "duplicate_cells": [list(key) for key, count in combos.items() if count != 1],
        "target_count": len({key[0] for key in combos}),
        "variants": sorted({key[1] for key in combos}),
        "organization_seeds": sorted({key[2] for key in combos}),
        "variant_counts": dict(sorted(Counter(row["variant"] for row in assignments).items())),
        "seed_counts": {str(k): v for k, v in sorted(Counter(row["organization_seed"] for row in assignments).items())},
        "all_planned_not_started": all(row.get("state") == "planned_not_started" for row in assignments),
        "all_provider_seed_null": all(row.get("provider_seed") is None for row in assignments),
        "all_run_attempt_zero": all(row.get("run_attempt") == 0 for row in assignments),
        "django_13265_rows": sum(task_to_canonical.get(row["task_id"]) == blocker_id for row in assignments),
    }
    coverage_checks["pass"] = (
        coverage_checks["source_hash_match"] and coverage_checks["row_count"] == 240 and
        coverage_checks["unique_assignment_ids"] == 240 and coverage_checks["unique_cells"] == 240 and
        not coverage_checks["duplicate_cells"] and coverage_checks["target_count"] == 20 and
        coverage_checks["variants"] == ["B0", "B1", "B2", "B3"] and coverage_checks["organization_seeds"] == [42, 43, 44] and
        coverage_checks["all_planned_not_started"] and coverage_checks["all_provider_seed_null"] and
        coverage_checks["all_run_attempt_zero"] and coverage_checks["django_13265_rows"] == 12
    )

    snapshot_path = args.snapshot.resolve()
    snapshot_manifest_path = args.snapshot_manifest.resolve()
    snapshot_lines = [json.loads(line) for line in snapshot_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    snapshot_manifest = load(snapshot_manifest_path)
    line_checks = []
    for row in snapshot_lines:
        expected_line_hash = row.get("line_sha256")
        actual_line_hash = hashlib.sha256(canonical_bytes({k: v for k, v in row.items() if k != "line_sha256"})).hexdigest()
        line_checks.append({"source_id": row.get("source_id"), "expected": expected_line_hash, "actual": actual_line_hash, "match": expected_line_hash == actual_line_hash})
    snapshot_checks = {
        "snapshot_path": str(snapshot_path),
        "snapshot_sha256": sha(snapshot_path),
        "expected_snapshot_sha256": snapshot_binding["snapshot"]["sha256"],
        "snapshot_hash_match": sha(snapshot_path) == snapshot_binding["snapshot"]["sha256"] == snapshot_manifest.get("snapshot_hash"),
        "manifest_path": str(snapshot_manifest_path),
        "manifest_sha256": sha(snapshot_manifest_path),
        "expected_manifest_sha256": snapshot_binding["manifest"]["sha256"],
        "manifest_hash_match": sha(snapshot_manifest_path) == snapshot_binding["manifest"]["sha256"],
        "record_count": len(snapshot_lines),
        "manifest_record_count": snapshot_manifest.get("n_records"),
        "unique_source_ids": len({row.get("source_id") for row in snapshot_lines}),
        "line_checks": line_checks,
        "all_pending_validator_reconstruction": all(row.get("status") == "pending_validator_reconstruction" for row in snapshot_binding["records"]),
        "internal_validated_count": snapshot_binding.get("internal_validated_count"),
        "promotion_permitted": snapshot_binding.get("promotion_permitted"),
    }
    snapshot_checks["pass"] = (
        snapshot_checks["snapshot_hash_match"] and snapshot_checks["manifest_hash_match"] and
        snapshot_checks["record_count"] == 11 and snapshot_checks["manifest_record_count"] == 11 and
        snapshot_checks["unique_source_ids"] == 11 and all(item["match"] for item in line_checks) and
        snapshot_checks["all_pending_validator_reconstruction"] and snapshot_checks["internal_validated_count"] == 0 and
        snapshot_checks["promotion_permitted"] is False
    )

    current_harness_fingerprint = source_fingerprint(Path(__file__).resolve().parents[1])
    fingerprint_checks = {
        "manifest_path": str(args.fingerprint_manifest.resolve()),
        "manifest_sha256": sha(args.fingerprint_manifest),
        "manifest_status": fingerprint_manifest.get("status"),
        "frozen_harness_source_fingerprint": fingerprint_manifest.get("harness_source_fingerprint"),
        "current_harness_source_fingerprint": current_harness_fingerprint,
        "harness_fingerprint_match": current_harness_fingerprint == fingerprint_manifest.get("harness_source_fingerprint"),
        "agent_fingerprint_in_old_manifest": fingerprint_manifest.get("coding_agent_source_fingerprint"),
        "agent_current_fingerprint_supplied": False,
        "pass": False,
    }

    binding_set_pass = set(binding_by_id) == expected_ids == set(package_by_id) | {blocker_id}
    review = {
        "schema": "a5.h3-dual-end-review.v1",
        "status": "review_complete_not_h3_passed",
        "conclusion": "offline evidence binding and matrix checks completed; H3 remains blocked pending dual fingerprint refreeze and snapshot validator reconstruction",
        "agent_artifact_manifest": {
            "path": str(agent_manifest_path),
            "sha256": agent_manifest_hash,
            "expected_updated_sha256": expected_manifest_hash,
            "sha_match": agent_manifest_hash == expected_manifest_hash,
            "artifacts_internal_hashes_pass": all(item["match"] for item in manifest_artifact_checks),
        },
        "target_binding": {
            "target_count": len(binding_by_id),
            "ready_count": len(ready_ids),
            "blocked_ids": [blocker_id],
            "id_set_pass": binding_set_pass,
            "evidence_hashes_pass": not evidence_failures,
            "rows": evidence_rows,
        },
        "coverage": coverage_checks,
        "snapshot": snapshot_checks,
        "fingerprints": fingerprint_checks,
        "canonical_state": {
            "runnable_frozen": canonical_handoff.get("runnable_frozen"),
            "execution_enabled": canonical_handoff.get("execution", {}).get("enabled"),
            "provider_calls": canonical_handoff.get("execution", {}).get("provider_calls_this_handoff"),
            "paid_build_started": canonical_handoff.get("execution", {}).get("paid_build_started"),
            "paid_pilot_started": canonical_handoff.get("execution", {}).get("paid_pilot_started"),
        },
        "pending_gates": [
            "dual_source_fingerprint_refreeze_after_both_sides_final_changes",
            "current_harness_fingerprint_drift_from_old_freeze",
            "agent_current_fingerprint_not_supplied_for_dual_refreeze",
            "snapshot_validator_reconstruction_and_nonpromotion_review",
            "final H3 receipt-schema/injection-semantics cross-check",
        ],
        "model_calls": 0,
        "paid": False,
        "provider_started": False,
        "memory_build_started": False,
        "docker_paid_run_started": False,
        "pilot_started": False,
    }
    save(output / "h3-dual-end-review.json", review)
    save(output / "target-evidence-recheck.json", {
        "schema": "a5.h3-target-evidence-recheck.v1",
        "agent_manifest_sha256": agent_manifest_hash,
        "target_count": len(evidence_rows),
        "ready_count": len(ready_ids),
        "blocked_target": blocker_id,
        "evidence_hashes_pass": not evidence_failures,
        "failures": evidence_failures,
        "rows": evidence_rows,
    })
    save(output / "matrix-coverage-recheck.json", {
        "schema": "a5.h3-matrix-coverage-recheck.v1",
        **coverage_checks,
        "agent_projection": coverage_projection,
    })
    save(output / "snapshot-recheck.json", {
        "schema": "a5.h3-snapshot-recheck.v1",
        **snapshot_checks,
        "agent_projection": snapshot_binding,
    })
    save(output / "pending.json", {
        "schema": "a5.h3-dual-end-pending.v1",
        "items": review["pending_gates"],
        "reason": "The projection is eligible for review, but this audit does not authorize H3, runnable_frozen, paid execution, or pilot start.",
    })

    files = {}
    for path in sorted(output.rglob("*")):
        if path.is_file() and path.name != "artifact-manifest.json":
            files[path.relative_to(output).as_posix()] = sha(path)
    save(output / "artifact-manifest.json", {
        "schema": "a5.h3-dual-end-review-artifact-manifest.v1",
        "source_agent_artifact_manifest_sha256": agent_manifest_hash,
        "artifacts": files,
        "manifest_self_hash": "excluded (self-referential); hash externally",
    })
    print(json.dumps({"output": str(output), "status": review["status"], "artifacts": files}, indent=2))


if __name__ == "__main__":
    main()
