"""Aggregate the 20 A5 memory-source preflight receipts without paid execution.

This is an evidence audit only.  It keeps the four historical source-only rows
in the denominator and carries every remaining16 environment/baseline result
verbatim.  A row is never made eligible merely because transport or F2P
known-good passed; independent grader calibration remains a separate gate.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "configs/a5/pilot20-harness-manifest.json"
HISTORY_SOURCE_ROOT = ROOT / "docs/upgrade/evidence/A5-harness-preflight-12-host-sources"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def historical_row(task_id: str, source_receipt: Path) -> dict:
    receipt = load(source_receipt)
    source = receipt.get("source", {})
    return {
        "task_id": task_id,
        "role": "historical_pool",
        "source_preflight": {
            "status": receipt.get("status", "unknown"),
            "receipt_ref": str(source_receipt),
            "receipt_sha256": sha(source_receipt),
            "archive_sha256": source.get("archive_sha256"),
            "snapshot_kind": source.get("snapshot_kind"),
            "complete": source.get("snapshot_kind") == "complete_pinned_upstream_archive",
        },
        "transport": {"status": "legacy_source_only_receipt", "receipt_ref": None},
        "environment_baseline": {"status": "missing_own_receipt"},
        "grader": {"status": "blocked_missing_environment_baseline"},
        "eligible": False,
        "blockers": ["historical_source_only_receipt_has_no_own_environment_baseline_or_grader"],
        "model_calls": 0,
        "paid": False,
    }


def remaining_row(row: dict) -> dict:
    status = row.get("status")
    collection = row.get("collection", {})
    baseline = row.get("baseline", {})
    grader = row.get("grader", {})
    source = row.get("source", {})
    blockers = []
    if status != "baseline_ready":
        blockers.append("environment_or_baseline_gate_failed")
    if grader.get("status") != "ready":
        blockers.append("independent_full_repo_grader_pending")
    if grader.get("known_good") != "pass":
        blockers.append("known_good_did_not_pass_target_or_collection_invalid")
    return {
        "task_id": row["task_id"],
        "role": "remaining16_memory_source",
        "source_preflight": {
            "status": "complete" if source.get("snapshot_kind") == "complete_pinned_upstream_archive" else "invalid_env",
            "archive_sha256": source.get("archive_sha256"),
            "archive_bytes": source.get("archive_bytes"),
            "within_runtime_limits": source.get("within_runtime_limits"),
            "receipt_ref": row.get("source_attempt_ref"),
        },
        "transport": {
            "status": "transport_ready",
            "receipt_ref": row.get("transport_receipt_ref"),
            "image_digest": row.get("transport_image_digest"),
            "mode": row.get("transport_mode"),
        },
        "environment_baseline": {
            "status": status,
            "collection_status": collection.get("status"),
            "collection_count": collection.get("count"),
            "baseline_status": baseline.get("status"),
            "baseline_failure_nodeids": baseline.get("failure_nodeids", []),
            "known_good_target_status": grader.get("known_good"),
            "receipt_ref": row.get("baseline", {}).get("receipt_ref"),
        },
        "grader": {
            "status": grader.get("status", "unknown"),
            "known_good_target": grader.get("known_good"),
            "known_good_outcomes": grader.get("known_good_outcomes", {}),
        },
        "eligible": False,
        "blockers": blockers,
        "model_calls": row.get("model_calls", 0),
        "paid": row.get("paid", False),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--remaining-baseline", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = load(MANIFEST)
    source_ids = manifest["memory_build_sources"]
    if len(source_ids) != 20 or len(set(source_ids)) != 20:
        raise ValueError("memory source denominator is not exactly 20")
    remaining = load(args.remaining_baseline.resolve() / "receipts.json")["rows"]
    remaining_by_id = {r["task_id"]: r for r in remaining}
    rows = []
    for task_id in source_ids:
        if task_id in remaining_by_id:
            rows.append(remaining_row(remaining_by_id[task_id]))
            continue
        source_receipt = HISTORY_SOURCE_ROOT / "tasks" / task_id / "source-receipt.json"
        if not source_receipt.is_file():
            raise FileNotFoundError(f"missing historical source receipt: {source_receipt}")
        rows.append(historical_row(task_id, source_receipt))
    counts = Counter(r["environment_baseline"]["status"] for r in rows)
    grader_counts = Counter(r["grader"]["status"] for r in rows)
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    save(out / "manifest.json", {
        "schema": "a5.memory-pool-preflight-audit.v1",
        "memory_source_manifest": str(MANIFEST),
        "memory_source_manifest_sha256": sha(MANIFEST),
        "assigned": 20,
        "remaining16_receipt_dir": str(args.remaining_baseline.resolve()),
        "model_calls": 0,
        "paid": False,
    })
    save(out / "receipts.json", {
        "schema": "a5.memory-pool-preflight-receipts.v1",
        "rows": rows,
        "full_denominator": 20,
        "model_calls": 0,
        "paid": False,
    })
    blockers = sorted({b for r in rows for b in r["blockers"]})
    readiness = {
        "schema": "a5.memory-pool-preflight-readiness.v1",
        "status": "blocked",
        "assigned": 20,
        "full_denominator": 20,
        "source_complete": sum(r["source_preflight"]["complete"] if "complete" in r["source_preflight"] else r["source_preflight"]["status"] == "complete" for r in rows),
        "transport_ready": sum(r["transport"]["status"] == "transport_ready" for r in rows),
        "environment_baseline_ready": sum(r["environment_baseline"]["status"] == "baseline_ready" for r in rows),
        "grader_ready": sum(r["grader"]["status"] == "ready" for r in rows),
        "status_counts": dict(counts),
        "grader_status_counts": dict(grader_counts),
        "blocking_tasks": [r["task_id"] for r in rows if r["blockers"]],
        "blocking_reasons": blockers,
        "model_calls": 0,
        "paid": False,
        "paid_build_started": False,
        "paid_pilot_started": False,
        "memory_build_eligible": False,
        "next_gate": "image_backed_independent_full_repo_grader_calibration_and_historical_baseline_receipts",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    save(out / "readiness.json", readiness)
    save(out / "failure-retry-ledger.json", {"schema": "a5.failure-retry-ledger.v1", "entries": [
        {"task_id": r["task_id"], "status": r["environment_baseline"]["status"], "blockers": r["blockers"], "attempt": 1, "retries": 0}
        for r in rows], "model_calls": 0, "paid": False})
    save(out / "artifact-manifest.json", {p.relative_to(out).as_posix(): sha(p) for p in sorted(out.rglob("*")) if p.is_file()})
    print(json.dumps(readiness, ensure_ascii=False, indent=2))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
