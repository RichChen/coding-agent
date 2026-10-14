"""Export and audit a cold validated_lightweight memory snapshot.

This module copies already-reviewed public memory records into a new snapshot.
It does not promote failed/blocked rows, does not run a model, and does not
rewrite old evidence files.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "docs" / "upgrade" / "evidence"

SNAPSHOT_RECORD_SCHEMA = "a5.memory-snapshot.record.v1"
SNAPSHOT_MANIFEST_SCHEMA = "a5.memory-snapshot.manifest.v1"
CONSUMPTION_SCHEMA = "a5.memory-consumption-contract.v1"
BOUNDARY_SCHEMA = "a5.public-boundary-audit.v1"
FAILURE_REF_SCHEMA = "a5.failure-ledger-ref.v1"
RECORD_STATE = "validated_lightweight"
VALIDATION_SCOPE = "public_independent_smoke_receipt"

FORBIDDEN_MARKERS = (
    "gold_patch",
    "test_patch",
    "FAIL_TO_PASS",
    "PASS_TO_PASS",
    "test_overlay",
    "private_source_binding",
    "hints_text",
    "EvaluationSpec",
    "hidden_tests",
)
PUBLIC_SCAN_FILES = (
    "public-input.json",
    "public-trajectory.json",
    "memory-candidate.json",
    "validation/receipt.json",
    "candidate-delta.json",
)
CARRY_FORWARD_IDS = (
    "django__django-10914",
    "django__django-10924",
    "sympy__sympy-11400",
    "scikit-learn__scikit-learn-10297",
    "pytest-dev__pytest-5103",
)
CONSUMABLE_FIELDS = (
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
)
FORBIDDEN_FIELDS = (
    "gold_patch",
    "test_patch",
    "FAIL_TO_PASS",
    "PASS_TO_PASS",
    "hidden tests",
    "private grader output",
    "raw private source row",
    "target gold patch",
    "target test patch",
    "EvaluationSpec",
    "hints_text",
)


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha_obj(value: Any) -> str:
    return sha_bytes(canonical_bytes(value))


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_jsonl(path: Path) -> list[tuple[str, dict[str, Any]]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rows.append((sha_bytes(line.encode("utf-8")), json.loads(line)))
    return rows


def scan_text_markers(text: str) -> list[str]:
    return [marker for marker in FORBIDDEN_MARKERS if marker in text]


def path_out_of_evidence(path: Path) -> bool:
    try:
        path.resolve().relative_to(EVIDENCE.resolve())
    except ValueError:
        return True
    return "private" in path.resolve().parts


def scan_record_boundary(record: dict[str, Any], source_dir: Path) -> dict[str, Any]:
    hits = []
    hits.extend(scan_text_markers(json.dumps(record, ensure_ascii=False)))
    missing = []
    hash_mismatches = []
    path_errors = []
    if path_out_of_evidence(source_dir):
        path_errors.append("source_dir_outside_evidence_or_private")
    for relative in PUBLIC_SCAN_FILES:
        path = source_dir / relative
        if not path.is_file():
            if relative == "candidate-delta.json":
                missing.append(relative)
            else:
                missing.append(relative)
            continue
        if path_out_of_evidence(path):
            path_errors.append(relative)
            continue
        hits.extend(scan_text_markers(path.read_text(encoding="utf-8", errors="replace")))
        expected = None
        hashes = record.get("hashes") if isinstance(record.get("hashes"), dict) else {}
        if relative == "public-input.json":
            expected = hashes.get("public_input_sha256")
        elif relative == "public-trajectory.json":
            expected = hashes.get("trajectory_sha256")
        elif relative == "validation/receipt.json":
            expected = hashes.get("validation_receipt_sha256")
        elif relative == "candidate-delta.json":
            expected = hashes.get("candidate_delta_sha256")
        actual = sha_file(path)
        if expected and expected != actual:
            hash_mismatches.append({"file": relative, "expected": expected, "actual": actual})
    return {
        "source_id": record.get("source_id"),
        "marker_hits": sorted(set(hits)),
        "missing_public_files": missing,
        "hash_mismatches": hash_mismatches,
        "path_errors": path_errors,
    }


def _require_exportable(record: dict[str, Any]) -> list[str]:
    errors = []
    if record.get("schema") != "a5.memory-record.validated.v1":
        errors.append("schema")
    if record.get("state") != "validated":
        errors.append("state_not_validated")
    if record.get("validation_scope") != VALIDATION_SCOPE:
        errors.append("validation_scope")
    if record.get("private_grader_run") is not False:
        errors.append("private_grader_run")
    if not isinstance(record.get("source_id"), str) or not record["source_id"]:
        errors.append("source_id")
    bindings = record.get("bindings")
    hashes = record.get("hashes")
    if not isinstance(bindings, dict):
        errors.append("bindings")
    else:
        for key in ("repo", "base_revision", "source_tree_hash", "transport_image_digest"):
            if not bindings.get(key):
                errors.append(key)
    if not isinstance(hashes, dict):
        errors.append("hashes")
    else:
        for key in ("public_input_sha256", "trajectory_sha256", "validation_receipt_sha256", "candidate_delta_sha256"):
            value = hashes.get(key)
            if not (isinstance(value, str) and len(value) == 64):
                errors.append(key)
    return errors


def build_snapshot_row(source_line_sha256: str, record: dict[str, Any]) -> dict[str, Any]:
    errors = _require_exportable(record)
    if errors:
        raise ValueError("record not exportable as validated_lightweight: " + ",".join(errors))
    source_id = record["source_id"]
    wave = "carry-forward" if source_id in CARRY_FORWARD_IDS else "expand"
    row = {
        "schema": SNAPSHOT_RECORD_SCHEMA,
        "record_state": RECORD_STATE,
        "validation_scope": VALIDATION_SCOPE,
        "private_grader_run": False,
        "full_grader_validated": False,
        "source_id": source_id,
        "wave": wave,
        "source_state": record.get("state"),
        "source_line_sha256": source_line_sha256,
        "source_record": record,
        "bindings": record["bindings"],
        "hashes": record["hashes"],
        "source_dir": record.get("source_dir"),
        "reviewed_at": record.get("reviewed_at"),
    }
    row["line_sha256"] = sha_obj({k: v for k, v in row.items() if k != "line_sha256"})
    return row


def default_paths() -> dict[str, Path]:
    s2 = EVIDENCE / "A5-memory-pool-76-s2"
    return {
        "input": s2 / "validated-memory-records.jsonl",
        "s2_status": s2 / "s2-status.json",
        "failure_ledger": s2 / "failure-ledger.jsonl",
        "carry_forward": s2 / "provenance-review-carry-forward" / "validated-memory-records.jsonl",
        "expand": s2 / "provenance-review-expand" / "validated-memory-records.jsonl",
        "authorization": s2 / "authorization.json",
        "anomaly": EVIDENCE / "A5-harness-preflight-71-memory-gates-final" / "anomaly-dispositions.json",
        "pilot_manifest": ROOT / "configs" / "a5" / "pilot20-harness-manifest.json",
        "image_handoff": ROOT / "configs" / "a5" / "image-backed-handoff.json",
        "canonical_handoff": Path(r"D:/crq/src/coding-agent/configs/a5/canonical-handoff.json"),
        "consumption_manifest": Path(r"D:/crq/src/coding-agent/configs/a5/pilot20-harness-consumption-manifest.json"),
        "funding": Path(r"D:/crq/src/coding-agent/configs/a5/funding-cny-v1.json"),
        "contract_carry_forward_missing": ROOT / "docs" / "upgrade" / "evidence" / "A5-memory-pool-75-s1-smoke" / "provenance-review-carry-forward" / "validated-memory-records.jsonl",
    }


def _input_hashes(paths: dict[str, Path]) -> dict[str, Any]:
    rows = {}
    for key, path in paths.items():
        if key == "contract_carry_forward_missing":
            rows[key] = {
                "path": str(path.as_posix()),
                "exists": path.is_file(),
                "sha256": sha_file(path) if path.is_file() else None,
                "note": "contract listed this 75-s1 path; actual carry-forward records live in 76-s2 provenance-review-carry-forward",
            }
            continue
        rows[key] = {"path": str(path.as_posix()), "exists": path.is_file(), "sha256": sha_file(path) if path.is_file() else None}
    return rows


def failure_ledger_ref(paths: dict[str, Path]) -> dict[str, Any]:
    status = load_json(paths["s2_status"])
    failed_rows = load_jsonl(paths["failure_ledger"])
    anomaly = load_json(paths["anomaly"]) if paths["anomaly"].is_file() else {"rows": []}
    anomaly_map = {row["task_id"]: row for row in anomaly.get("rows", []) if isinstance(row, dict)}
    failed = []
    for source_id in status.get("failed_sources", []):
        ledger = next((row for _sha, row in failed_rows if row.get("source_id") == source_id), {})
        failed.append({
            "source_id": source_id,
            "state": "failed_retained",
            "promoted": False,
            "reason": ledger.get("reason"),
            "wave": ledger.get("wave"),
            "refs": [
                {"path": str(paths["failure_ledger"].as_posix()), "sha256": sha_file(paths["failure_ledger"])},
                {"path": str(paths["s2_status"].as_posix()), "sha256": sha_file(paths["s2_status"])},
            ],
        })
    blocked = []
    for source_id in status.get("blocked_sources", []):
        row = anomaly_map.get(source_id, {})
        refs = [
            {"path": str(paths["s2_status"].as_posix()), "sha256": sha_file(paths["s2_status"])},
            {"path": str(paths["authorization"].as_posix()), "sha256": sha_file(paths["authorization"])},
        ]
        if paths["anomaly"].is_file():
            refs.append({"path": str(paths["anomaly"].as_posix()), "sha256": sha_file(paths["anomaly"])})
        evidence = row.get("evidence")
        if evidence:
            evidence_path = EVIDENCE / evidence if not Path(evidence).is_absolute() else Path(evidence)
            if evidence_path.is_file():
                refs.append({"path": str(evidence_path.as_posix()), "sha256": sha_file(evidence_path)})
        blocked.append({
            "source_id": source_id,
            "state": "blocked",
            "promoted": False,
            "disposition": row.get("disposition"),
            "refs": refs,
        })
    return {
        "schema": FAILURE_REF_SCHEMA,
        "failed_count": len(failed),
        "blocked_count": len(blocked),
        "promoted_failed_or_blocked": False,
        "failed": failed,
        "blocked": blocked,
        "note": "failed and blocked rows are referenced, not copied into the lightweight snapshot",
    }


def consumption_contract(snapshot_hash: str) -> dict[str, Any]:
    return {
        "schema": CONSUMPTION_SCHEMA,
        "cold_snapshot_version": "a5.validated-lightweight.v1",
        "record_state": RECORD_STATE,
        "validation_scope": VALIDATION_SCOPE,
        "private_grader_run": False,
        "full_grader_validated": False,
        "source_ready_20_of_20": False,
        "snapshot_hash": snapshot_hash,
        "agent_consumable_fields": list(CONSUMABLE_FIELDS),
        "forbidden_fields": list(FORBIDDEN_FIELDS),
        "agent_may_see": ["public issue", "public source", "allowed memory view hashes and public trajectory refs"],
        "host_only": ["gold patch", "test patch", "hidden tests", "private grader", "target answers", "raw private source row"],
        "claim_boundary": "lightweight public smoke validation plus rule provenance review; not target causal proof",
    }


def write_artifact_manifest(output_dir: Path) -> dict[str, str]:
    manifest = {path.relative_to(output_dir).as_posix(): sha_file(path)
                for path in sorted(output_dir.rglob("*")) if path.is_file() and path.name != "artifact-manifest.json"}
    dump_json(output_dir / "artifact-manifest.json", {
        "schema": "a5.artifact-manifest.v1",
        "files": manifest,
    })
    return manifest


def export_snapshot(*, input_path: Path, output_dir: Path, paths: dict[str, Path] | None = None) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise ValueError("output directory must not already exist")
    output_dir.mkdir(parents=True)
    paths = dict(default_paths() if paths is None else paths)
    paths["input"] = input_path
    raw_rows = load_jsonl(input_path)
    if len(raw_rows) != 11:
        raise ValueError(f"expected 11 validated records, got {len(raw_rows)}")
    snapshot_rows = []
    source_ids = []
    for line_sha, record in raw_rows:
        row = build_snapshot_row(line_sha, record)
        snapshot_rows.append(row)
        source_ids.append(row["source_id"])
    if len(set(source_ids)) != 11:
        raise ValueError("source IDs are not unique")

    jsonl_path = output_dir / "memory-snapshot.jsonl"
    with jsonl_path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in snapshot_rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    snapshot_hash = sha_file(jsonl_path)

    audits = []
    for row in snapshot_rows:
        source_dir = Path(row["source_dir"])
        audits.append(scan_record_boundary(row["source_record"], source_dir))
    marker_hits = [item for audit in audits if audit["marker_hits"]]
    path_errors = [item for audit in audits if audit["path_errors"]]
    hash_mismatches = [item for audit in audits if audit["hash_mismatches"]]
    boundary = {
        "schema": BOUNDARY_SCHEMA,
        "snapshot_hash": snapshot_hash,
        "records_scanned": len(audits),
        "private_marker_hits": marker_hits,
        "path_errors": path_errors,
        "hash_mismatches": hash_mismatches,
        "passed": not marker_hits and not path_errors and not hash_mismatches,
        "forbidden_markers": list(FORBIDDEN_MARKERS),
    }

    records_manifest = []
    for row in snapshot_rows:
        records_manifest.append({
            "source_id": row["source_id"],
            "line_sha256": row["line_sha256"],
            "source_line_sha256": row["source_line_sha256"],
            "record_state": row["record_state"],
            "wave": row["wave"],
            "repo": row["bindings"]["repo"],
            "base_revision": row["bindings"]["base_revision"],
            "source_tree_hash": row["bindings"]["source_tree_hash"],
            "transport_image_digest": row["bindings"]["transport_image_digest"],
            "trajectory_sha256": row["hashes"]["trajectory_sha256"],
            "validation_receipt_sha256": row["hashes"]["validation_receipt_sha256"],
            "public_input_sha256": row["hashes"]["public_input_sha256"],
            "candidate_delta_sha256": row["hashes"]["candidate_delta_sha256"],
            "source_dir": row["source_dir"],
        })
    snapshot_manifest = {
        "schema": SNAPSHOT_MANIFEST_SCHEMA,
        "record_state": RECORD_STATE,
        "validation_scope": VALIDATION_SCOPE,
        "private_grader_run": False,
        "full_grader_validated": False,
        "n_records": 11,
        "source_ids": source_ids,
        "source_ids_unique": True,
        "snapshot_path": str(jsonl_path.as_posix()),
        "snapshot_hash": snapshot_hash,
        "records": records_manifest,
        "source_ready_20_of_20": False,
    }
    failure_ref = failure_ledger_ref(paths)
    if failure_ref["failed_count"] != 4 or failure_ref["blocked_count"] != 5:
        raise ValueError("expected 4 failed + 5 blocked references")
    contract = consumption_contract(snapshot_hash)
    dump_json(output_dir / "memory-snapshot-manifest.json", snapshot_manifest)
    dump_json(output_dir / "public-boundary-audit.json", boundary)
    dump_json(output_dir / "memory-consumption-contract.json", contract)
    dump_json(output_dir / "failure-ledger-ref.json", failure_ref)
    dump_json(output_dir / "schema.json", {
        "snapshot_record": SNAPSHOT_RECORD_SCHEMA,
        "snapshot_manifest": SNAPSHOT_MANIFEST_SCHEMA,
        "consumption_contract": CONSUMPTION_SCHEMA,
        "public_boundary_audit": BOUNDARY_SCHEMA,
        "failure_ledger_ref": FAILURE_REF_SCHEMA,
        "record_state": RECORD_STATE,
    })
    audit_snapshot(snapshot_path=jsonl_path, manifest_path=output_dir / "memory-snapshot-manifest.json",
                   output_path=output_dir / "snapshot-audit.json")
    input_hashes = _input_hashes(paths)
    readiness = {
        "schema": "a5.real240.h0-readiness.v1",
        "status": "lightweight_snapshot_frozen" if boundary["passed"] else "blocked_boundary_audit",
        "record_state": RECORD_STATE,
        "n_records": 11,
        "snapshot_hash": snapshot_hash,
        "boundary_passed": boundary["passed"],
        "source_ready_20_of_20": False,
        "full_grader_validated": False,
        "paid_pilot_started": False,
        "model_calls": 0,
        "paid": False,
        "input_hashes": input_hashes,
        "success_conditions": [
            "11 unique source IDs",
            "hashes and receipts readable",
            "snapshot independently recomputable",
            "no private markers",
            "records exported only as validated_lightweight",
        ],
        "failure_conditions": [
            "duplicate or missing source IDs",
            "private marker or path escape",
            "hash mismatch against public artifacts",
            "failed/blocked rows promoted",
        ],
        "stop_conditions": [
            "do not start provider/model/memory build/pilot from this snapshot",
            "do not claim full-repo grader validation",
        ],
        "pending": [
            "H3 agent consumption manifest/hash for these 11 records",
            "H3 B0-B3 runtime semantics",
            "H3 20 target grader readiness",
        ],
    }
    dump_json(output_dir / "readiness.json", readiness)
    files = write_artifact_manifest(output_dir)
    return {
        "status": readiness["status"],
        "snapshot_hash": snapshot_hash,
        "output_dir": str(output_dir.as_posix()),
        "n_records": 11,
        "boundary_passed": boundary["passed"],
        "model_calls": 0,
        "paid": False,
        "files": files,
    }


def audit_snapshot(*, snapshot_path: Path, manifest_path: Path, output_path: Path | None = None) -> dict[str, Any]:
    rows = load_jsonl(snapshot_path)
    manifest = load_json(manifest_path)
    errors = []
    if manifest.get("schema") != SNAPSHOT_MANIFEST_SCHEMA:
        errors.append("manifest_schema")
    if len(rows) != 11 or manifest.get("n_records") != 11:
        errors.append("record_count")
    snapshot_hash = sha_file(snapshot_path)
    if manifest.get("snapshot_hash") != snapshot_hash:
        errors.append("snapshot_hash_drift")
    source_ids = []
    recomputed = []
    audits = []
    for line_sha, row in rows:
        source_ids.append(row.get("source_id"))
        if row.get("schema") != SNAPSHOT_RECORD_SCHEMA:
            errors.append("record_schema")
        if row.get("record_state") != RECORD_STATE:
            errors.append("record_state")
        if row.get("validation_scope") != VALIDATION_SCOPE:
            errors.append("validation_scope")
        if row.get("private_grader_run") is not False or row.get("full_grader_validated") is not False:
            errors.append("overclaimed_validation")
        expected_line = sha_obj({k: v for k, v in row.items() if k != "line_sha256"})
        if row.get("line_sha256") != expected_line:
            errors.append("line_hash_mismatch")
        recomputed.append({"source_id": row.get("source_id"), "line_sha256": expected_line, "file_line_sha256": line_sha})
        source_dir = Path(row.get("source_dir") or "")
        audits.append(scan_record_boundary(row.get("source_record") or {}, source_dir))
    if len([sid for sid in source_ids if sid]) != 11 or len(set(source_ids)) != 11:
        errors.append("source_id_unique")
    if [row["source_id"] for row in manifest.get("records", [])] != source_ids:
        errors.append("manifest_source_order")
    marker_hits = [item for item in audits if item["marker_hits"]]
    path_errors = [item for item in audits if item["path_errors"]]
    hash_mismatches = [item for item in audits if item["hash_mismatches"]]
    if marker_hits:
        errors.append("private_markers")
    if path_errors:
        errors.append("path_boundary")
    if hash_mismatches:
        errors.append("public_artifact_hash")
    result = {
        "schema": "a5.memory-snapshot.audit.v1",
        "status": "pass" if not errors else "fail",
        "snapshot_hash": snapshot_hash,
        "recomputed_records": recomputed,
        "errors": sorted(set(errors)),
        "private_marker_hits": marker_hits,
        "path_errors": path_errors,
        "hash_mismatches": hash_mismatches,
        "model_calls": 0,
        "paid": False,
    }
    if output_path is not None:
        dump_json(output_path, result)
    if errors:
        raise ValueError("snapshot audit failed: " + ",".join(result["errors"]))
    return result
