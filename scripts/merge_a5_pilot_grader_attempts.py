"""Merge a full calibration attempt with later target retries without hiding failures."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_refs(value, old_root: str, new_root: str):
    if isinstance(value, str):
        return value.replace(old_root, new_root)
    if isinstance(value, list):
        return [replace_refs(item, old_root, new_root) for item in value]
    if isinstance(value, dict):
        return {key: replace_refs(item, old_root, new_root) for key, item in value.items()}
    return value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--retry", action="append", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--pilot-matrix", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    base = args.base.resolve()
    retries = [path.resolve() for path in args.retry]
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    base_rows = {row["task_id"]: row for row in load(base / "receipts.json")["rows"]}
    selected = dict(base_rows)
    selected_from = {task_id: base for task_id in selected}
    for retry in retries:
        for row in load(retry / "receipts.json")["rows"]:
            task_id = row["task_id"]
            if task_id not in selected:
                raise ValueError(f"retry target is outside base denominator: {task_id}")
            selected[task_id] = row
            selected_from[task_id] = retry

    base_ids = list(base_rows)
    if set(selected) != set(base_ids) or len(selected) != 20:
        raise ValueError("merged calibration must preserve the exact 20-target denominator")

    merged_rows = []
    provenance = []
    for task_id in base_ids:
        row = selected[task_id]
        source_root = selected_from[task_id]
        task_source = source_root / "tasks" / task_id
        task_dest = output / "tasks" / task_id
        shutil.copytree(task_source, task_dest)
        row = replace_refs(row, str(task_source), str(task_dest))
        calibration_path = task_dest / "calibration.json"
        if calibration_path.is_file():
            save(calibration_path, row)
        merged_rows.append(row)
        provenance.append({
            "task_id": task_id,
            "source_attempt": str(source_root),
            "source_attempt_sha256": sha(source_root / "receipts.json"),
            "grader_ready": row.get("grader_ready", False),
        })

    input_path = args.input.resolve()
    pilot_path = args.pilot_matrix.resolve()
    input_rows = {row["task_id"]: row for row in load(input_path)["rows"]}
    django = next(row for row in merged_rows if row["task_id"] == "django__django-13265")
    django_input = input_rows["django__django-13265"]
    save(output / "django-contract-audit.json", {
        "schema": "a5.django-f2p-contract-audit.v1",
        "task_id": django["task_id"],
        "repo": django.get("repo"),
        "base_revision": django.get("base_revision"),
        "contract_status": "blocked_requires_contract_revision",
        "reason": "declared_f2p_does_not_match_fixed_base_behavior",
        "expected_f2p_count": django_input.get("expected_f2p_count"),
        "actual_baseline_failed": django_input.get("actual_baseline_failed"),
        "unexpected_baseline_passed": django_input.get("unexpected_baseline_passed"),
        "baseline_receipt_ref": django_input.get("baseline_receipt_ref"),
        "known_good_receipt_ref": django_input.get("known_good_receipt_ref"),
        "canonical_bound": False,
        "action_required": "version_contract_and_rebaseline_before_grader_binding",
    })
    save(output / "manifest.json", {
        "schema": "a5.image-backed-full-repo-grader-calibration.merged.v1",
        "assigned": len(merged_rows),
        "selected": base_ids,
        "input_hashes": {str(path): sha(path) for path in (input_path, pilot_path)},
        "source_attempts": [str(base), *(str(path) for path in retries)],
        "provenance": provenance,
        "canonical_bound": False,
        "model_calls": 0,
        "paid": False,
    })
    save(output / "receipts.json", {
        "schema": "a5.image-backed-full-repo-grader-calibration-receipts.merged.v1",
        "rows": merged_rows,
        "full_denominator": len(merged_rows),
        "model_calls": 0,
        "paid": False,
    })
    ready = sum(bool(row.get("grader_ready")) for row in merged_rows)
    save(output / "readiness.json", {
        "schema": "a5.image-backed-full-repo-grader-calibration-readiness.merged.v1",
        "status": "ready" if ready == len(merged_rows) else "blocked",
        "assigned": len(merged_rows),
        "collection_ready": sum(row.get("full_collection_status") == "ready" for row in merged_rows),
        "grader_ready": ready,
        "negative_checks_passed": all(row.get("negative_checks_passed") is True for row in merged_rows),
        "canonical_bound": False,
        "model_calls": 0,
        "paid": False,
        "blocking_tasks": [row["task_id"] for row in merged_rows if not row.get("grader_ready")],
        "contract_blockers": ["django__django-13265"],
    })
    save(output / "artifact-manifest.json", {
        path.relative_to(output).as_posix(): sha(path)
        for path in sorted(output.rglob("*"))
        if path.is_file() and path.name != "artifact-manifest.json"
    })


if __name__ == "__main__":
    main()
