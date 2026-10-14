#!/usr/bin/env python3
"""Zero-model receipt/importer/ledger fail-closed fixture. Not a real pilot."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.eval.a5_memory_snapshot import dump_json, sha_file, write_artifact_manifest
from src.eval.a5_pilot_fixture import (
    expected_kwargs,
    fixture_assignment,
    fixture_bindings,
    make_fixture_receipt,
    run_fail_closed_cases,
)
from src.eval.a5_receipts import import_pilot_receipt as import_receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if output.exists():
        raise ValueError("output directory must not already exist")
    output.mkdir(parents=True)
    bindings = fixture_bindings()
    assignment = fixture_assignment()
    imported = []
    for variant in ("B0", "B1", "B2", "B3"):
        receipt = make_fixture_receipt(variant, bindings=bindings, assignment=assignment)
        row = import_receipt(receipt, **expected_kwargs({**assignment, "variant": variant}, bindings))
        path = output / "receipts" / variant / "receipt.json"
        dump_json(path, row)
        imported.append({
            "variant": variant,
            "path": str(path.as_posix()),
            "sha256": sha_file(path),
            "injection_count": len(row["injection_receipt_refs"]),
            "fixture_only": True,
            "model_calls": 0,
            "paid": False,
            "pilot_claim": row["pilot_claim"],
        })
    cases = run_fail_closed_cases()
    dump_json(output / "fail-closed-cases.json", cases)
    dump_json(output / "fixture-ledger.json", {
        "schema": "a5.pilot-fixture-ledger.v1",
        "fixture_only": True,
        "model_calls": 0,
        "paid": False,
        "real_240_started": False,
        "unknown_usage_keeps_reserve": True,
        "rows": imported,
        "note": "fixture wiring only; do not import as pilot-240 results",
    })
    dump_json(output / "readiness.json", {
        "schema": "a5.real240.h2-readiness.v1",
        "status": "fixture_wiring_verified" if cases["all_ok"] else "fixture_wiring_failed",
        "fixture_only": True,
        "model_calls": 0,
        "paid": False,
        "real_240_started": False,
        "fail_closed_all_ok": cases["all_ok"],
        "success_conditions": [
            "B0 accepted with no injection",
            "B1-B3 accepted only with source/evidence/snapshot/injection hashes",
            "assignment mismatch, snapshot drift, duplicate attempt, unknown usage, missing grader, cleanup false rejected",
            "fixture_only=true, model_calls=0, paid=false",
        ],
        "failure_conditions": ["any fail-closed case does not match expected error"],
        "stop_conditions": [
            "do not copy fixture receipts into real pilot ledgers",
            "do not start provider or paid 240",
        ],
        "pending": ["H3 agent-side B0-B3 runtime and target graders", "H4 paid authorization"],
    })
    write_artifact_manifest(output)
    result = {
        "status": "fixture_wiring_verified" if cases["all_ok"] else "fixture_wiring_failed",
        "fixture_only": True,
        "model_calls": 0,
        "paid": False,
        "real_240_started": False,
        "fail_closed_all_ok": cases["all_ok"],
        "output_dir": str(output.as_posix()),
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0 if cases["all_ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
