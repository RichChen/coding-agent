#!/usr/bin/env python3
"""Offline A5 readiness gate; never builds, calls a model, or starts a pilot."""
from __future__ import annotations

import argparse
import hashlib
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.eval.a5_receipts import VARIANTS
from src.eval.a5_snapshot import TRANSFER_LIMIT
from src.policy.cny_budget import A5BudgetPlan, money
from src.runtime.session import source_fingerprint


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(manifest_path, *, model_binding=None, environments=None, fingerprint=None, fingerprint_manifest=None, output=None):
    manifest = load(manifest_path)
    errors = []
    targets = manifest.get("targets", [])
    history = manifest.get("historical_pool", [])
    if manifest.get("schema") != "a5.harness.manifest.v1": errors.append("manifest_schema")
    if len(targets) != 20 or len(set(targets)) != 20: errors.append("target_count_or_duplicates")
    if len(history) != 4 or len(set(history)) != 4 or set(targets) & set(history): errors.append("history_count_or_overlap")
    if manifest.get("variants") != list(VARIANTS) or manifest.get("repeats") != 3 or manifest.get("planned_task_runs") != 240: errors.append("schedule_contract")
    source = manifest.get("source_dataset", {})
    if source.get("revision") != "6ec7bb89b9342f664a54a6e0a6ea6501d3437cc2": errors.append("source_revision")
    expected_plan = A5BudgetPlan()
    if sum(money(x) for x in (expected_plan.build_cny, expected_plan.pilot_cny, expected_plan.reserve_cny)) != expected_plan.total_cny: errors.append("budget_arithmetic")

    if model_binding is None:
        errors.append("model_snapshot_and_current_price_missing")
    else:
        binding = load(model_binding)
        if (binding.get("schema") != "a5.model-price-binding.v1" or not binding.get("verified")
                or not binding.get("snapshot_id") or binding.get("currency") != "CNY"):
            errors.append("model_price_not_verified")
        if (not binding.get("provider") or not binding.get("model") or not binding.get("source_url")
                or not binding.get("retrieved_on")):
            errors.append("model_price_provenance")
        for field in ("prompt_cache_hit_per_million", "prompt_cache_miss_per_million", "completion_per_million"):
            try:
                if Decimal(str(binding.get(field))).is_nan() or Decimal(str(binding.get(field))) < 0:
                    raise InvalidOperation
            except (InvalidOperation, ValueError, TypeError):
                errors.append("model_price_invalid")
                break

    if environments is None:
        errors.append("24_environment_baseline_receipts_missing")
        env_rows = []
    else:
        loaded = load(environments)
        if isinstance(loaded, dict) and loaded.get("schema") not in (None, "a5.environment-baseline.v1"):
            errors.append("environment_schema")
        env_rows = loaded.get("rows", []) if isinstance(loaded, dict) else loaded
        expected_tasks = set(targets + history)
        if isinstance(loaded, dict) and "task_inventory" in loaded:
            inventory = loaded.get("task_inventory")
            if (not isinstance(inventory, list) or len(inventory) != 24 or set(inventory) != expected_tasks):
                errors.append("environment_task_inventory")
        if not isinstance(env_rows, list):
            env_rows = []
            errors.append("environment_rows_invalid")
        if len(env_rows) != 24: errors.append("environment_row_count")
        seen_tasks = []
        for row in env_rows:
            if not isinstance(row, dict):
                errors.append("environment_row_invalid")
                continue
            task_id = row.get("task_id")
            if task_id not in expected_tasks: errors.append("environment_unknown_task")
            seen_tasks.append(task_id)
            if row.get("baseline_status") not in ("baseline_failed_reproduced", "baseline_preflighted"):
                errors.append("environment_not_baselined")
            if not isinstance(row.get("baseline_failed_nodeids"), list) or not row.get("baseline_failed_nodeids"):
                errors.append("baseline_failure_evidence_missing")
            required = ("repo", "base_revision", "source_tree_hash", "image_digest", "python_version",
                        "pytest_version", "test_collection_hash", "collected_count", "cleanup_verified", "model_calls")
            if any(row.get(field) in (None, "") for field in required):
                errors.append("environment_identity_or_runtime_missing")
            if row.get("cleanup_verified") is not True or type(row.get("model_calls")) is not int or row.get("model_calls") != 0:
                errors.append("environment_safety_not_verified")
        if len(seen_tasks) != len(set(seen_tasks)) or set(seen_tasks) != expected_tasks:
            errors.append("environment_task_coverage")

    current_fp = source_fingerprint(Path(__file__).resolve().parents[1])
    if fingerprint_manifest is None:
        errors.append("dual_source_fingerprint_not_refrozen")
    else:
        fp = load(fingerprint_manifest)
        if (fp.get("status") != "frozen_after_both_sides_stable" or
                not isinstance(fp.get("harness_source_fingerprint"), str) or len(fp["harness_source_fingerprint"]) != 64 or
                not isinstance(fp.get("coding_agent_source_fingerprint"), str) or len(fp["coding_agent_source_fingerprint"]) != 64):
            errors.append("dual_source_fingerprint_invalid")
        elif fp["harness_source_fingerprint"] != current_fp:
            errors.append("harness_source_fingerprint_drift")
    if fingerprint is not None:
        if not isinstance(fingerprint, str) or len(fingerprint) != 64:
            errors.append("source_fingerprint_invalid")
        elif fingerprint != current_fp:
            errors.append("source_fingerprint_mismatch")

    result = {
        "schema": "a5.preflight.result.v1", "status": "ready" if not errors else "blocked",
        "model_calls": 0, "paid_build_started": False, "paid_pilot_started": False,
        "targets": len(targets), "historical_pool": len(history), "planned_task_runs": manifest.get("planned_task_runs"),
        "environment_rows": len(env_rows), "runtime_transfer_limit_bytes": TRANSFER_LIMIT,
        "errors": list(dict.fromkeys(errors)), "source_lock_sha256": source.get("source_lock_sha256"),
        "public_review_sha256": source.get("public_review_sha256"),
        "current_harness_source_fingerprint": current_fp,
        "next_gates": ["model_snapshot_and_current_price", "24_environment_and_baseline_receipts", "dual_side_source_fingerprint", "B0-B3 receipt importer"] if errors else ["explicit paid build authorization boundary", "B0-B3 build receipts"]
    }
    if output:
        out = Path(output).resolve()
        if out.exists(): raise ValueError("output must be a new directory")
        out.mkdir(parents=True)
        (out / "readiness.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        (out / "manifest.sha256").write_text(sha(manifest_path) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("configs/a5/pilot20-harness-manifest.json"))
    parser.add_argument("--model-binding", type=Path)
    parser.add_argument("--environments", type=Path)
    parser.add_argument("--source-fingerprint")
    parser.add_argument("--fingerprint-manifest", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run(args.manifest, model_binding=args.model_binding, environments=args.environments,
                 fingerprint=args.source_fingerprint, fingerprint_manifest=args.fingerprint_manifest, output=args.output)
    raise SystemExit(0 if result["status"] == "ready" else 2)
