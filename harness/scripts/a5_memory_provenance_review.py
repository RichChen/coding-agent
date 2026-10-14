#!/usr/bin/env python3
"""Rule-based provenance review for A5 S2 lightweight memory records.

Promotes candidate → validated only when public trajectory, independent
validation receipt, hashes, and public/private boundary checks all pass.
Never copies private grader/gold content into the review artifacts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


FORBIDDEN_KEYS = (
    "gold_patch",
    "test_patch",
    "FAIL_TO_PASS",
    "PASS_TO_PASS",
    "test_overlay",
    "private_source_binding",
)


def scan_public_leak(path: Path) -> list[str]:
    hits = []
    text = path.read_text(encoding="utf-8", errors="replace")
    for key in FORBIDDEN_KEYS:
        if key in text:
            hits.append(key)
    return hits


def review_attempt(source_dir: Path, source_id: str) -> dict:
    reasons = []
    required = {
        "public-input.json": source_dir / "public-input.json",
        "public-trajectory.json": source_dir / "public-trajectory.json",
        "validation/receipt.json": source_dir / "validation" / "receipt.json",
        "memory-candidate.json": source_dir / "memory-candidate.json",
        "cleanup.json": source_dir / "cleanup.json",
        "readiness.json": source_dir / "readiness.json",
        "cost-entry.json": source_dir / "cost-entry.json",
    }
    missing = [name for name, path in required.items() if not path.exists()]
    if missing:
        return {
            "source_id": source_id,
            "decision": "rejected",
            "reasons": ["missing_artifacts:" + ",".join(missing)],
            "source_dir": str(source_dir),
        }

    public_input = load(required["public-input.json"])
    trajectory = load(required["public-trajectory.json"])
    validation = load(required["validation/receipt.json"])
    candidate = load(required["memory-candidate.json"])
    cleanup = load(required["cleanup.json"])
    readiness = load(required["readiness.json"])

    if readiness.get("source_id") != source_id or candidate.get("source_id") != source_id:
        reasons.append("source_id_mismatch")
    if public_input.get("private_specs_host_only") is not True:
        reasons.append("private_specs_host_only_not_asserted")
    if not public_input.get("transport_image_digest") or not public_input.get("source_tree_hash"):
        reasons.append("missing_transport_or_tree_hash")
    if not public_input.get("base_revision") or not public_input.get("repo"):
        reasons.append("missing_repo_or_base_revision")

    traj_sha = sha_file(required["public-trajectory.json"])
    if candidate.get("trajectory_sha256") != traj_sha:
        reasons.append("trajectory_hash_mismatch")
    if not trajectory.get("issue_summary") or not trajectory.get("public_verification"):
        reasons.append("trajectory_missing_required_public_fields")
    if not trajectory.get("actions"):
        reasons.append("trajectory_missing_actions")

    if validation.get("status") != "pass":
        reasons.append("validation_not_pass:" + str(validation.get("status")))
    if validation.get("private_grader") and "not_run" not in str(validation.get("private_grader")):
        # Keep private grader details out of public review; only accept smoke-marked receipts.
        reasons.append("unexpected_private_grader_payload")
    changed = int(validation.get("delta_changed_files") or 0)
    deleted = int(validation.get("delta_deleted_files") or 0)
    if changed + deleted <= 0:
        reasons.append("empty_candidate_delta")
    if not (source_dir / "candidate-delta.json").exists():
        reasons.append("missing_candidate_delta_file")
    else:
        delta_sha = sha_file(source_dir / "candidate-delta.json")
        if candidate.get("candidate_delta_sha256") and candidate.get("candidate_delta_sha256") != delta_sha:
            reasons.append("candidate_delta_hash_mismatch")

    if cleanup.get("cleanup_verified") is not True:
        reasons.append("cleanup_not_verified")
    if readiness.get("paid") is not True or int(readiness.get("model_calls") or 0) <= 0:
        reasons.append("not_a_paid_real_run")

    leaks = []
    for name in ("public-input.json", "public-trajectory.json", "memory-candidate.json", "validation/receipt.json"):
        leaks.extend(scan_public_leak(required[name] if name != "validation/receipt.json" else required["validation/receipt.json"]))
    if (source_dir / "candidate-delta.json").exists():
        # Delta is public candidate content; still forbid gold/test patch keys if somehow embedded.
        leaks.extend(scan_public_leak(source_dir / "candidate-delta.json"))
    leaks = sorted(set(leaks))
    if leaks:
        reasons.append("forbidden_private_markers:" + ",".join(leaks))

    decision = "validated" if not reasons else "rejected"
    if readiness.get("status") == "failed" or candidate.get("state") in {"rejected_or_failed", "failed"}:
        # Do not promote failed smoke rows.
        if decision == "validated":
            decision = "rejected"
            reasons.append("source_attempt_marked_failed")

    # Lightweight pool: public independent validation is acceptable; record scope explicitly.
    return {
        "schema": "a5.memory-pool.provenance-review.v1",
        "source_id": source_id,
        "source_dir": str(source_dir.as_posix()),
        "decision": decision,
        "reasons": reasons,
        "reviewed": True,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "review_method": "rule_based",
        "validation_scope": "public_independent_smoke_receipt",
        "private_grader_run": False,
        "hashes": {
            "public_input_sha256": sha_file(required["public-input.json"]),
            "trajectory_sha256": traj_sha,
            "validation_receipt_sha256": sha_file(required["validation/receipt.json"]),
            "candidate_delta_sha256": sha_file(source_dir / "candidate-delta.json")
            if (source_dir / "candidate-delta.json").exists()
            else None,
        },
        "bindings": {
            "repo": public_input.get("repo"),
            "base_revision": public_input.get("base_revision"),
            "source_tree_hash": public_input.get("source_tree_hash"),
            "transport_image_digest": public_input.get("transport_image_digest"),
            "run_attempt_id": candidate.get("run_attempt_id") or readiness.get("operation_id"),
            "delta_changed_files": changed,
            "model_calls": readiness.get("model_calls"),
            "paid": readiness.get("paid"),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True, help="JSON list of {source_id,source_dir}")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)
    rows = load(args.manifest)
    reviews = []
    for row in rows:
        source_id = row["source_id"]
        source_dir = Path(row["source_dir"])
        if not source_dir.is_absolute():
            source_dir = (ROOT / source_dir).resolve()
        review = review_attempt(source_dir, source_id)
        reviews.append(review)
        save(output / "reviews" / f"{source_id}.json", review)
        print(json.dumps({"source_id": source_id, "decision": review["decision"], "reasons": review["reasons"]}, ensure_ascii=False))

    validated = [r for r in reviews if r["decision"] == "validated"]
    rejected = [r for r in reviews if r["decision"] == "rejected"]
    save(
        output / "summary.json",
        {
            "schema": "a5.memory-pool.provenance-review-summary.v1",
            "reviewed": len(reviews),
            "validated": len(validated),
            "rejected": len(rejected),
            "model_calls": 0,
            "paid": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    with (output / "validated-memory-records.jsonl").open("w", encoding="utf-8") as handle:
        for review in validated:
            handle.write(
                json.dumps(
                    {
                        "schema": "a5.memory-record.validated.v1",
                        "state": "validated",
                        "source_id": review["source_id"],
                        "validation_scope": review["validation_scope"],
                        "private_grader_run": False,
                        "bindings": review["bindings"],
                        "hashes": review["hashes"],
                        "source_dir": review["source_dir"],
                        "reviewed_at": review["reviewed_at"],
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    with (output / "rejected.jsonl").open("w", encoding="utf-8") as handle:
        for review in rejected:
            handle.write(json.dumps(review, ensure_ascii=False) + "\n")
    return 0 if not rejected else 2


if __name__ == "__main__":
    raise SystemExit(main())
