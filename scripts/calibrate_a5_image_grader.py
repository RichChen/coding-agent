"""Calibrate image-backed full-repository grader readiness for A5 targets.

The command makes no model calls. A target is ready only when its pinned
known-good image supports a complete full-repository collection, a bound
known-good target receipt verifies the task-specific regression tests, cleanup
is verified, and the host grader's rejection behavior passes executable
policy-fixture checks. This does not bind the target into a pilot canonical.
"""
from __future__ import annotations

import argparse
import asyncio
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import tarfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.preflight_a5_repo_baseline import outcomes, run_pytest
from src.eval.grader import tree_hash
from src.eval.repo_grader import RepositoryGrader, RepositorySpec


ROOT = Path(__file__).resolve().parents[1]
POLICY_FIXTURE_BASE = {
    "src/target.py": b"def target():\n    return 1\n",
    "tests/test_target.py": b"def test_target():\n    assert True\n",
}
POLICY_FIXTURE_NODEID = "tests/test_target.py::test_target"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _receipt_image(evidence: dict):
    """Read the pinned image from current or legacy host-runner evidence."""
    direct = evidence.get("image") or evidence.get("image_digest")
    if direct:
        return direct
    isolation = evidence.get("isolation") or {}
    config = isolation.get("Config") or {}
    return config.get("Image")


def _legacy_source_seed(row: dict):
    """Materialize only the pinned public archive for images without /opt/repo."""
    if not row.get("grader_input_restored_from_history"):
        return None, None
    inventory_ref = (row.get("source") or {}).get("inventory_ref")
    if not inventory_ref:
        raise ValueError("legacy source inventory reference missing")
    inventory = Path(inventory_ref)
    archive_path = inventory.with_name("source.tar.gz")
    if not archive_path.is_file():
        raise ValueError(f"legacy source archive missing: {archive_path}")
    from src.eval.a5_image_tree import archive_manifest
    manifest = archive_manifest(archive_path, row["repo"], row["base_revision"])
    if manifest["file_count"] > 2048 or manifest["total_bytes"] > 8 * 1024 * 1024:
        raise ValueError("legacy source archive exceeds runtime transfer limits")
    if any(meta["kind"] == "symlink" for meta in manifest["entries"].values()):
        raise ValueError("legacy source archive contains unsupported symlink")
    prefix = row["repo"].split("/", 1)[1] + "-" + row["base_revision"] + "/"
    files = {}
    with tarfile.open(archive_path, "r:gz") as archive:
        for name, meta in manifest["entries"].items():
            if meta["kind"] != "file":
                continue
            member = archive.extractfile(prefix + name)
            if member is None:
                raise ValueError(f"legacy source member missing: {name}")
            data = member.read()
            if len(data) != meta["size"]:
                raise ValueError(f"legacy source member truncated: {name}")
            files[name] = data
    generated = {}
    for name, binding in (row.get("runtime_generated_files") or {}).items():
        generated_path = Path(binding["ref"])
        if not generated_path.is_file() or sha(generated_path) != binding.get("sha256"):
            raise ValueError(f"legacy generated environment file binding mismatch: {name}")
        data = generated_path.read_bytes()
        if name in files:
            raise ValueError(f"legacy generated file collides with source archive: {name}")
        files[name] = data
        generated[name] = {"ref": str(generated_path.resolve()), "sha256": sha(generated_path)}
    return files, {
        "mode": "explicit_archive_files",
        "archive_ref": str(archive_path.resolve()),
        "archive_sha256": sha(archive_path),
        "source_tree_hash": manifest["source_tree_hash"],
        "file_count": len(files),
        "total_bytes": sum(len(data) for data in files.values()),
        "generated_files": generated,
    }


def _known_good_binding(row: dict):
    """Check a prior task-specific positive receipt against its pinned image."""
    grader = row.get("grader") or {}
    image = row.get("known_good_image_digest")
    receipt_ref = row.get("known_good_receipt_ref")
    declared_status = grader.get("known_good")
    if declared_status is None and row.get("known_good_pass") is True:
        declared_status = "pass"
    declared_outcomes = grader.get("known_good_outcomes") or row.get("known_good_outcomes") or {}
    if not declared_outcomes:
        frozen_targets = row.get("actual_baseline_failed") or (row.get("baseline") or {}).get("failure_nodeids") or []
        declared_outcomes = {str(node): "passed" for node in frozen_targets}
    if not image or not receipt_ref:
        return {"status": "blocked", "reason": "known_good_image_or_receipt_ref_missing"}
    if declared_status != "pass" or not declared_outcomes:
        return {"status": "blocked", "reason": "known_good_target_status_or_outcomes_missing"}
    receipt_path = Path(receipt_ref)
    if not receipt_path.is_file():
        return {"status": "blocked", "reason": "known_good_receipt_unreadable", "receipt_ref": str(receipt_path)}
    try:
        evidence = load(receipt_path)
    except (OSError, json.JSONDecodeError) as exc:
        return {"status": "blocked", "reason": "known_good_receipt_invalid", "detail": type(exc).__name__}

    execution = evidence.get("execution") or {}
    receipt = evidence.get("receipt") or {}
    actual_outcomes = outcomes(receipt)
    expected_outcomes = {str(node): status for node, status in declared_outcomes.items()}
    receipt_image = _receipt_image(evidence)
    valid = (
        receipt_image == image
        and evidence.get("cleanup_verified") is True
        and execution.get("status") == "succeeded"
        and execution.get("exit_code") == 0
        and receipt.get("complete") is True
        and receipt.get("exit_code") == 0
        and receipt.get("collection_errors") == []
        and bool(expected_outcomes)
        and all(status == "passed" for status in expected_outcomes.values())
        and all(actual_outcomes.get(node) == status for node, status in expected_outcomes.items())
    )
    return {
        "status": "pass" if valid else "blocked",
        "reason": None if valid else "known_good_receipt_binding_or_outcome_mismatch",
        "receipt_ref": str(receipt_path.resolve()),
        "receipt_sha256": sha(receipt_path),
        "image": image,
        "receipt_image": receipt_image,
        "expected_outcomes": expected_outcomes,
        "verified_outcomes": {node: actual_outcomes.get(node) for node in expected_outcomes},
        "cleanup_verified": evidence.get("cleanup_verified"),
    }


def _validate_pilot_binding(row: dict, pilot_rows: dict[str, dict] | None):
    if pilot_rows is None:
        return {"status": "not_requested"}
    task_id = row.get("task_id")
    pilot = pilot_rows.get(task_id)
    if pilot is None:
        return {"status": "blocked", "reason": "task_not_in_locked_pilot_matrix"}
    actual = (row.get("repo"), row.get("base_revision"))
    expected = (pilot.get("expected_repo"), pilot.get("target_base_commit"))
    matched = actual == expected and bool(task_id)
    return {
        "status": "pass" if matched else "blocked",
        "reason": None if matched else "pilot_repo_or_base_commit_mismatch",
        "canonical_target_id": task_id,
        "repo": row.get("repo"),
        "expected_repo": pilot.get("expected_repo"),
        "base_revision": row.get("base_revision"),
        "expected_base_commit": pilot.get("target_base_commit"),
        "pilot_base_hash": pilot.get("target_base_hash"),
    }


def pilot_rows_from_lock(path: Path | None):
    if path is None:
        return None
    data = load(path.resolve())
    targets = {}
    for row in data.get("rows", []):
        target_id = row.get("canonical_target_id")
        if target_id is None:
            continue
        identity = (row.get("expected_repo"), row.get("target_base_commit"), row.get("target_base_hash"))
        previous = targets.setdefault(target_id, identity)
        if previous != identity:
            raise ValueError(f"pilot matrix has conflicting identity rows for {target_id}")
    if not targets:
        raise ValueError("pilot matrix has no target rows")
    return {
        task_id: {"expected_repo": identity[0], "target_base_commit": identity[1], "target_base_hash": identity[2]}
        for task_id, identity in targets.items()
    }


def _fixture_receipt():
    phases = ("setup", "call", "teardown")
    return {
        "schema": "repo.pytest.receipt.v1",
        "complete": True,
        "exit_code": 0,
        "collected": [POLICY_FIXTURE_NODEID],
        "collection_errors": [],
        "reports": [
            {"nodeid": POLICY_FIXTURE_NODEID, "when": phase, "outcome": "passed", "wasxfail": None}
            for phase in phases
        ],
    }


class _PolicyFixtureGrader(RepositoryGrader):
    """Use the real grader policy with controlled execution evidence, no Docker."""

    def __init__(self, evidence):
        self.fixture_evidence = evidence

    async def execute(self, *args, **kwargs):
        return deepcopy(self.fixture_evidence)


async def run_negative_checks(image: str):
    """Execute host-side rejection paths through RepositoryGrader.evaluate."""
    spec = RepositorySpec(
        task_id="calibration-policy-fixture",
        base_hash=tree_hash(POLICY_FIXTURE_BASE),
        image=image,
        editable_paths=("src/target.py",),
        test_paths=("tests",),
        python_paths=("src",),
        expected_nodeids=(POLICY_FIXTURE_NODEID,),
    )
    successful = {
        "status": "executed",
        "integrity_verified": True,
        "cleanup_ok": True,
        "receipt": _fixture_receipt(),
        "input_changes_during_tests": [],
        "execution": {"status": "succeeded", "exit_code": 0, "truncated": False, "stdout": ""},
    }
    checks = []

    tampered = dict(POLICY_FIXTURE_BASE)
    tampered["tests/test_target.py"] = b"def test_fake():\n    pass\n"
    result = await _PolicyFixtureGrader(successful).evaluate(POLICY_FIXTURE_BASE, tampered, spec)
    checks.append({
        "case": "protected_path_change",
        "status": "rejected" if result.get("reason") == "protected_or_unassigned_path_changed" else "failed",
        "observed_status": result.get("status"),
        "observed_reason": result.get("reason"),
    })

    missing_receipt = {**successful, "receipt": None}
    result = await _PolicyFixtureGrader(missing_receipt).evaluate(POLICY_FIXTURE_BASE, POLICY_FIXTURE_BASE, spec)
    checks.append({
        "case": "missing_receipt",
        "status": "rejected" if result.get("reason") == "missing_or_incomplete_receipt" else "failed",
        "observed_status": result.get("status"),
        "observed_reason": result.get("reason"),
    })

    changed_input = {**successful, "input_changes_during_tests": ["src/target.py"]}
    result = await _PolicyFixtureGrader(changed_input).evaluate(POLICY_FIXTURE_BASE, POLICY_FIXTURE_BASE, spec)
    checks.append({
        "case": "input_integrity_change",
        "status": "rejected" if result.get("reason") == "frozen_input_changed_during_tests" else "failed",
        "observed_status": result.get("status"),
        "observed_reason": result.get("reason"),
    })

    return {
        "scope": "executed_host_policy_fixture_not_target_specific",
        "checks": checks,
        "passed": bool(checks) and all(check["status"] == "rejected" for check in checks),
    }


async def calibrate(row: dict, output: Path, *, pilot_rows: dict[str, dict] | None = None):
    task_id = row["task_id"]
    image = row.get("known_good_image_digest")
    result = {
        "task_id": task_id,
        "status": "blocked",
        "grader_ready": False,
        "repo": row.get("repo"),
        "base_revision": row.get("base_revision"),
        "image": image,
        "model_calls": 0,
        "paid": False,
        "canonical_binding_required": True,
        "input_baseline_status": row.get("status"),
    }
    pilot_binding = _validate_pilot_binding(row, pilot_rows)
    result["pilot_binding"] = pilot_binding
    if pilot_binding["status"] == "blocked":
        result["reason"] = pilot_binding["reason"]
        save(output / "calibration.json", result)
        return result
    if row.get("status") != "baseline_ready":
        result.update({
            "reason": "input_baseline_status_not_ready",
            "full_collection_status": "not_run",
            "negative_checks_passed": False,
            "input_blocker": row.get("reason"),
        })
        save(output / "calibration.json", result)
        return result

    known_good = _known_good_binding(row)
    result["known_good_binding"] = known_good
    if known_good["status"] != "pass":
        result["reason"] = known_good["reason"]
        save(output / "calibration.json", result)
        return result

    family = row["repo"].split("/", 1)[0]
    root = "testing" if family == "pytest-dev" else ("sklearn" if family == "scikit-learn" else ("sympy" if family == "sympy" else ""))
    args = [] if family == "django" else ["--collect-only", "-q", root]
    seed_files, seed_binding = _legacy_source_seed(row)
    if family == "django":
        evidence = await run_pytest(image, [], output / "full-repo", timeout=300, django=True, collect_only=True, seed_files=seed_files)
    else:
        evidence = await run_pytest(
            image,
            args,
            output / "full-repo",
            timeout=300,
            collect_only=True,
            sympy_native_helpers=family == "sympy",
            seed_files=seed_files,
            legacy_observer=bool(seed_files),
        )
    receipt = evidence.get("receipt") or {}
    collected = receipt.get("collected", [])
    execution = evidence.get("execution") or {}
    complete = (
        evidence.get("cleanup_verified") is True
        and execution.get("status") == "succeeded"
        and execution.get("exit_code") == 0
        and receipt.get("complete") is True
        and receipt.get("exit_code") == 0
        and receipt.get("collection_errors") == []
        and isinstance(collected, list)
        and bool(collected)
        and all(isinstance(node, str) and node for node in collected)
        and len(collected) == len(set(collected))
    )
    negative = await run_negative_checks(image)
    grader_ready = complete and negative["passed"] and known_good["status"] == "pass" and pilot_binding["status"] != "blocked"
    result.update({
        "status": "ready" if grader_ready else "blocked",
        "grader_ready": grader_ready,
        "reason": None if grader_ready else "collection_or_executable_grader_policy_check_failed",
        "full_collection_status": "ready" if complete else "invalid_env",
        "full_collection_count": len(collected) if isinstance(collected, list) else 0,
        "full_collection_hash": hashlib.sha256(json.dumps(collected, sort_keys=False).encode()).hexdigest() if complete else None,
        "collection_evidence_ref": str((output / "full-repo" / "evidence.json").resolve()),
        "collection_evidence_sha256": sha(output / "full-repo" / "evidence.json") if (output / "full-repo" / "evidence.json").is_file() else None,
        "source_seed": seed_binding,
        "cleanup_verified": evidence.get("cleanup_verified"),
        "calibration_mode": "full_repo_collection_plus_bound_known_good_target_plus_executed_host_grader_policy_checks",
        "negative_checks": negative,
        "negative_checks_passed": negative["passed"],
        "model_calls": 0,
        "paid": False,
    })
    save(output / "calibration.json", result)
    return result


def select_rows(rows: list[dict], requested: list[str]):
    by_id = {}
    for row in rows:
        task_id = row.get("task_id")
        if not isinstance(task_id, str) or not task_id:
            raise ValueError("input receipt has a row without task_id")
        if task_id in by_id:
            raise ValueError(f"duplicate task_id in input receipts: {task_id}")
        by_id[task_id] = row
    selected = requested if requested else list(by_id)
    if len(selected) != len(set(selected)):
        raise ValueError("--only-task contains duplicate task ids")
    missing = sorted(set(selected) - set(by_id))
    if missing:
        raise ValueError("selected tasks missing from input receipts: " + ", ".join(missing))
    return [by_id[task_id] for task_id in selected]


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=Path, required=True, help="baseline receipts.json")
    parser.add_argument("--history-rows", type=Path)
    parser.add_argument("--pilot-matrix", type=Path, help="optional locked pilot-matrix-lock.json")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--only-task", action="append", default=[])
    args = parser.parse_args()

    rows_path = args.rows.resolve()
    input_rows = load(rows_path)["rows"]
    input_hashes = {str(rows_path): sha(rows_path)}
    if args.history_rows:
        history_path = args.history_rows.resolve()
        input_rows += load(history_path)["rows"]
        input_hashes[str(history_path)] = sha(history_path)
    rows = select_rows(input_rows, args.only_task)
    pilot_matrix_path = args.pilot_matrix.resolve() if args.pilot_matrix else None
    pilot_rows = pilot_rows_from_lock(pilot_matrix_path)
    if pilot_matrix_path:
        input_hashes[str(pilot_matrix_path)] = sha(pilot_matrix_path)
        not_in_matrix = sorted(row["task_id"] for row in rows if row["task_id"] not in pilot_rows)
        if not_in_matrix:
            raise ValueError("selected tasks missing from pilot matrix: " + ", ".join(not_in_matrix))

    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    results = []
    for row in rows:
        task_out = out / "tasks" / row["task_id"]
        task_out.mkdir(parents=True)
        result = await calibrate(row, task_out, pilot_rows=pilot_rows)
        results.append(result)
        print(json.dumps({k: result.get(k) for k in ("task_id", "status", "full_collection_count", "reason")}, ensure_ascii=False), flush=True)

    save(out / "manifest.json", {
        "schema": "a5.image-backed-full-repo-grader-calibration.v2",
        "assigned": len(rows),
        "selected": [row["task_id"] for row in rows],
        "input_hashes": input_hashes,
        "pilot_matrix": str(pilot_matrix_path) if pilot_matrix_path else None,
        "pilot_matrix_binding_required_for_canonical": True,
        "model_calls": 0,
        "paid": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    save(out / "receipts.json", {
        "schema": "a5.image-backed-full-repo-grader-calibration-receipts.v2",
        "rows": results,
        "full_denominator": len(results),
        "model_calls": 0,
        "paid": False,
    })
    ready = sum(result["grader_ready"] for result in results)
    save(out / "readiness.json", {
        "schema": "a5.image-backed-full-repo-grader-calibration-readiness.v2",
        "status": "ready" if ready == len(results) and results else "blocked",
        "assigned": len(results),
        "collection_ready": sum(result.get("full_collection_status") == "ready" for result in results),
        "grader_ready": ready,
        "negative_checks_passed": all(result.get("negative_checks_passed") is True for result in results),
        "canonical_bound": False,
        "model_calls": 0,
        "paid": False,
        "paid_build_started": False,
        "paid_pilot_started": False,
        "memory_build_eligible": False,
        "blocking_tasks": [result["task_id"] for result in results if not result["grader_ready"]],
    })
    save(out / "artifact-manifest.json", {
        path.relative_to(out).as_posix(): sha(path)
        for path in sorted(out.rglob("*"))
        if path.is_file() and path.name != "artifact-manifest.json"
    })
    raise SystemExit(0 if ready == len(results) and results else 2)


if __name__ == "__main__":
    asyncio.run(main())
