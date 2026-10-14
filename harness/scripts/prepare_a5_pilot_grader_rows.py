"""Build the immutable 20-target input snapshot for pilot grader calibration."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


RESTORED_TARGETS = {
    "pytest-dev__pytest-7220",
    "pytest-dev__pytest-8365",
    "pytest-dev__pytest-9359",
}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _unique_rows(data: dict, source: str):
    rows = {}
    for row in data.get("rows", []):
        task_id = row.get("task_id")
        if not task_id:
            raise ValueError(f"{source} contains a row without task_id")
        if task_id in rows:
            raise ValueError(f"{source} contains duplicate task_id {task_id}")
        rows[task_id] = row
    return rows


def _pilot_ids(data: dict):
    identities = {}
    ordered = []
    for row in data.get("rows", []):
        task_id = row.get("canonical_target_id")
        if not task_id:
            continue
        identity = (row.get("expected_repo"), row.get("target_base_commit"))
        if task_id not in identities:
            identities[task_id] = identity
            ordered.append(task_id)
        elif identities[task_id] != identity:
            raise ValueError(f"pilot matrix has conflicting identity rows for {task_id}")
    return ordered, identities


def reconcile(current: dict, history: dict, pilot: dict, generated_root: Path | None = None):
    current_rows = _unique_rows(current, "current receipts")
    history_rows = _unique_rows(history, "history receipts")
    pilot_ids, identities = _pilot_ids(pilot)
    if len(pilot_ids) != 20:
        raise ValueError(f"pilot matrix must contain exactly 20 targets, found {len(pilot_ids)}")

    rows = []
    provenance = []
    for task_id in pilot_ids:
        if task_id not in current_rows:
            raise ValueError(f"pilot target missing from current receipts: {task_id}")
        row = dict(current_rows[task_id])
        source = "current"
        if task_id in RESTORED_TARGETS:
            old = history_rows.get(task_id)
            if old is None:
                raise ValueError(f"restored target missing from history receipts: {task_id}")
            known_good = (old.get("phase_artifacts") or {}).get("known-good") or {}
            failures = (old.get("baseline") or {}).get("failure_nodeids") or []
            if old.get("status") != "ready" or old.get("grader", {}).get("known_good") != "pass":
                raise ValueError(f"history grader is not ready for {task_id}")
            if not old.get("image_digest") or not known_good.get("path") or not failures:
                raise ValueError(f"history grader binding is incomplete for {task_id}")
            row.update({
                "known_good_image_digest": old["image_digest"],
                "known_good_receipt_ref": known_good["path"],
                "actual_baseline_failed": failures,
                "known_good_pass": True,
                "grader": {
                    **old["grader"],
                    "known_good_outcomes": {node: "passed" for node in failures},
                },
                "grader_input_restored_from_history": True,
            })
            if generated_root is not None:
                generated = generated_root / task_id / "src" / "_pytest" / "_version.py"
                if not generated.is_file():
                    raise ValueError(f"generated environment file missing for {task_id}")
                row["runtime_generated_files"] = {
                    "src/_pytest/_version.py": {
                        "ref": str(generated.resolve()),
                        "sha256": sha(generated),
                    }
                }
            source = "history_grader_fields_over_current_identity"

        expected_repo, expected_base = identities[task_id]
        if (row.get("repo"), row.get("base_revision")) != (expected_repo, expected_base):
            raise ValueError(f"pilot identity mismatch for {task_id}")
        rows.append(row)
        provenance.append({"task_id": task_id, "source": source})

    return rows, provenance


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--history", type=Path, required=True)
    parser.add_argument("--pilot-matrix", type=Path, required=True)
    parser.add_argument("--generated-root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    paths = [args.current.resolve(), args.history.resolve(), args.pilot_matrix.resolve()]
    rows, provenance = reconcile(
        *(load(path) for path in paths),
        generated_root=args.generated_root.resolve() if args.generated_root else None,
    )
    generated_paths = [
        Path(binding["ref"])
        for row in rows
        for binding in (row.get("runtime_generated_files") or {}).values()
    ]
    save(args.output.resolve(), {
        "schema": "a5.pilot-grader-calibration-input.v1",
        "rows": rows,
        "assigned": len(rows),
        "provenance": provenance,
        "input_hashes": {str(path): sha(path) for path in [*paths, *generated_paths]},
        "restored_targets": sorted(RESTORED_TARGETS),
        "model_calls": 0,
        "paid": False,
    })


if __name__ == "__main__":
    main()
