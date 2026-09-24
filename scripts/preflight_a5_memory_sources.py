"""Acquire complete pinned source archives for the 16 un-preflighted A5 memory sources."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.preflight_a5_sources import source_task, save, sha  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT.parent / "coding-agent"
CANONICAL = AGENT / "configs/a5/canonical-handoff.json"
PROJECTION = AGENT / "configs/a5/pilot20-harness-consumption-manifest.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--jobs", type=int, default=4)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    canonical = json.loads(CANONICAL.read_text(encoding="utf-8"))
    projection = json.loads(PROJECTION.read_text(encoding="utf-8"))
    remaining = set(projection["remaining_memory_source_ids"])
    tasks = [{**task, "role": "memory_source"} for task in canonical["memory_build_source_pool"]
             if task["canonical_id"] in remaining]
    if len(tasks) != 16 or [task["canonical_id"] for task in tasks] != projection["remaining_memory_source_ids"]:
        raise ValueError("remaining16 canonical order/coverage mismatch")
    save(output / "manifest.json", {"schema": "a5.remaining-memory-source-acquisition.v1",
        "canonical_sha256": sha(CANONICAL.read_bytes()), "projection_sha256": sha(PROJECTION.read_bytes()),
        "task_ids": [task["canonical_id"] for task in tasks], "assigned": 16,
        "workers": args.jobs, "model_calls": 0, "paid": False})
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        rows = list(pool.map(lambda task: source_task(task, output), tasks))
    counts = {status: sum(row["status"] == status for row in rows)
              for status in sorted({row["status"] for row in rows})}
    save(output / "receipts.json", {"schema": "a5.remaining-memory-source-receipts.v1", "rows": rows,
                                    "full_denominator": 16, "model_calls": 0, "paid": False})
    save(output / "readiness.json", {"schema": "a5.remaining-memory-source-readiness.v1", "status": "blocked",
        "assigned": 16, "status_counts": counts, "environment_baseline_ready": 0, "model_calls": 0,
        "paid": False, "paid_build_started": False, "paid_pilot_started": False,
        "memory_build_eligible": False, "next_gate": "repo-specific environment and baseline preflight"})
    save(output / "failure-retry-ledger.json", {"schema": "a5.failure-retry-ledger.v1", "entries": [
        {"task_id": row["task_id"], "status": row["status"], "reason": row.get("reason"),
         "attempt": row.get("attempt", 1), "retries": row.get("retries", 0)} for row in rows],
        "model_calls": 0, "model_reservations": 0, "paid": False})
    save(output / "artifact-manifest.json", {p.relative_to(output).as_posix(): sha(p.read_bytes())
        for p in sorted(output.rglob("*")) if p.is_file()})
    print(json.dumps(counts, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
