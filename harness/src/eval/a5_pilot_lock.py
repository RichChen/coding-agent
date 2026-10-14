"""Audit and lock the 240-run A5 pilot matrix, receipt schema, and budget.

This lock is fail-closed. Missing target graders, model-binding problems, or
fingerprint drift produce a blocked report. It never starts a provider call.
"""
from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from src.eval.a5_memory_snapshot import dump_json, sha_file, write_artifact_manifest
from src.eval.a5_receipts import PILOT_RECEIPT_SCHEMA, PILOT_REQUIRED_FIELDS, PILOT_SEEDS, VARIANTS
from src.policy.cny_budget import PriceSnapshot
from src.runtime.session import source_fingerprint

ROOT = Path(__file__).resolve().parents[2]
AGENT_ROOT = Path(r"D:/crq/src/coding-agent")
REPEAT_TO_SEED = {0: 42, 1: 43, 2: 44}


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def scoped_fingerprint(root: Path, scopes: tuple[str, ...]) -> tuple[str, int]:
    rows = []
    for raw in scopes:
        path = root / raw
        candidates = [path] if path.is_file() else sorted(path.rglob("*")) if path.exists() else []
        for item in candidates:
            if not item.is_file() or ".git" in item.parts or "__pycache__" in item.parts:
                continue
            if item.suffix.lower() not in {".py", ".json", ".toml", ".yaml", ".yml"}:
                continue
            rows.append((item.relative_to(root).as_posix(), sha_file(item)))
    rows = sorted(set(rows))
    return hashlib.sha256(_canonical(rows)).hexdigest(), len(rows)


def load_price_binding(path: Path) -> tuple[dict[str, Any], str | None, list[str]]:
    errors = []
    if not path.is_file():
        return {}, None, ["model_binding_missing"]
    data = json.loads(path.read_text(encoding="utf-8"))
    required = ("provider", "model", "snapshot_id", "currency", "source_url", "retrieved_on")
    if data.get("schema") != "a5.model-price-binding.v1" or data.get("verified") is not True:
        errors.append("model_price_not_verified")
    if any(not data.get(key) for key in required) or data.get("currency") != "CNY":
        errors.append("model_price_provenance")
    try:
        price = PriceSnapshot(
            data["provider"], data["model"], data["snapshot_id"], data["currency"],
            Decimal(str(data["prompt_cache_hit_per_million"])),
            Decimal(str(data["prompt_cache_miss_per_million"])),
            Decimal(str(data["completion_per_million"])),
            data["source_url"], data["retrieved_on"], True,
        )
        return data, price.binding_hash, errors
    except Exception:
        errors.append("model_price_invalid")
        return data, None, errors


def default_inputs() -> dict[str, Path]:
    return {
        "assignments": AGENT_ROOT / "reports" / "upgrade" / "a5-pilot20-preparation-20260921-v4" / "assignments.json",
        "experiment_contract": AGENT_ROOT / "reports" / "upgrade" / "a5-pilot20-preparation-20260921-v4" / "experiment-contract.provisional.json",
        "canonical_handoff": AGENT_ROOT / "configs" / "a5" / "canonical-handoff.json",
        "consumption_manifest": AGENT_ROOT / "configs" / "a5" / "pilot20-harness-consumption-manifest.json",
        "funding": AGENT_ROOT / "configs" / "a5" / "funding-cny-v1.json",
        "pilot_manifest": ROOT / "configs" / "a5" / "pilot20-harness-manifest.json",
        "model_binding": ROOT / "configs" / "a5" / "model-price-binding.json",
        "fingerprint": ROOT / "configs" / "a5" / "source-fingerprint.pending.json",
        "image_handoff": ROOT / "configs" / "a5" / "image-backed-handoff.json",
    }


def audit_assignments(assignments: list[dict[str, Any]], canonical_targets: list[dict[str, Any]],
                      consumption_targets: list[dict[str, Any]]) -> tuple[dict[str, Any], list[str]]:
    errors = []
    if len(assignments) != 240:
        errors.append("assignment_count")
    ids = [row.get("assignment_id") for row in assignments]
    if len(set(ids)) != len(ids) or any(not isinstance(x, str) or len(x) != 64 for x in ids):
        errors.append("assignment_id_unique")
    variants = {row.get("variant") for row in assignments}
    if variants != set(VARIANTS):
        errors.append("variants")
    seeds = {row.get("organization_seed") for row in assignments}
    if seeds != set(PILOT_SEEDS):
        errors.append("seeds")
    repeats = {row.get("repeat_id") for row in assignments}
    if repeats != {0, 1, 2}:
        errors.append("repeat_id")
    pair_ok = all(REPEAT_TO_SEED.get(row.get("repeat_id")) == row.get("organization_seed") for row in assignments)
    if not pair_ok:
        errors.append("repeat_seed_mapping")
    exp = {row.get("experiment_id") for row in assignments}
    if exp != {"a5-pilot-20-v1"}:
        errors.append("experiment_id")
    cons_map = {row["agent_task_id"]: row for row in consumption_targets}
    can_map = {row["agent_task_id"]: row for row in canonical_targets}
    if set(cons_map) != set(can_map) or len(cons_map) != 20:
        errors.append("target_mapping_count")
    mapping_mismatch = []
    for task_id, cons in cons_map.items():
        can = can_map.get(task_id, {})
        for key in ("canonical_id", "expected_repo", "expected_base_commit"):
            if cons.get(key) != can.get(key):
                mapping_mismatch.append(task_id)
    if mapping_mismatch:
        errors.append("canonical_consumption_mapping")
    task_ids = {row.get("task_id") for row in assignments}
    if task_ids != set(cons_map):
        errors.append("assignment_task_coverage")
    triples = [(row.get("task_id"), row.get("variant"), row.get("organization_seed")) for row in assignments]
    if len(set(triples)) != 240:
        errors.append("matrix_not_unique")
    counts = {}
    for task_id in sorted(cons_map):
        counts[task_id] = sum(1 for row in assignments if row.get("task_id") == task_id)
    if set(counts.values()) != {12}:
        errors.append("per_target_12")
    locked_rows = []
    for row in assignments:
        mapping = cons_map.get(row.get("task_id"), {})
        canonical = can_map.get(row.get("task_id"), {})
        seed = row.get("organization_seed")
        target_base_hash = hashlib.sha256(str(mapping.get("expected_base_commit") or "").encode()).hexdigest()
        locked_rows.append({
            "assignment_id": row.get("assignment_id"),
            "experiment_id": row.get("experiment_id"),
            "canonical_target_id": mapping.get("canonical_id"),
            "agent_task_id": row.get("task_id"),
            "variant": row.get("variant"),
            "repeat_id": row.get("repeat_id"),
            "seed": seed,
            "public_task_hash": row.get("public_task_hash"),
            "canonical_public_task_model_hash": canonical.get("public_task_model_hash"),
            "target_base_commit": mapping.get("expected_base_commit"),
            "target_base_hash": target_base_hash,
            "expected_repo": mapping.get("expected_repo"),
            "injection_required": row.get("variant") != "B0",
            "state": row.get("state"),
            "target_grader_readiness": canonical.get("readiness"),
        })
        if row.get("public_task_hash") != canonical.get("public_task_model_hash"):
            errors.append("public_task_hash")
        if canonical.get("readiness") != "awaiting_repo_grader_readiness":
            # Keep this visible even if some targets later become ready.
            pass
    variant_counts = {variant: sum(1 for row in assignments if row.get("variant") == variant) for variant in VARIANTS}
    seed_counts = {str(seed): sum(1 for row in assignments if row.get("organization_seed") == seed) for seed in PILOT_SEEDS}
    lock = {
        "schema": "a5.pilot-matrix-lock.v1",
        "experiment_id": "a5-pilot-20-v1",
        "assigned": len(assignments),
        "targets": 20,
        "variants": list(VARIANTS),
        "repeats": [0, 1, 2],
        "seeds": list(PILOT_SEEDS),
        "matrix": "20x4x3",
        "variant_counts": variant_counts,
        "seed_counts": seed_counts,
        "b0_injection": False,
        "b1_b3_injection_required": True,
        "rows": locked_rows,
        "errors": sorted(set(errors)),
        "lock_status": "matrix_locked" if not errors else "matrix_invalid",
    }
    return lock, sorted(set(errors))


def receipt_schema_lock() -> dict[str, Any]:
    return {
        "schema": "a5.receipt-schema-lock.v1",
        "pilot_receipt_schema": PILOT_RECEIPT_SCHEMA,
        "legacy_host_receipt_schema": "a5.receipt.v1",
        "required_fields": list(PILOT_REQUIRED_FIELDS),
        "variants": list(VARIANTS),
        "seeds": list(PILOT_SEEDS),
        "repeat_to_seed": {str(k): v for k, v in REPEAT_TO_SEED.items()},
        "b0": "injection_receipt_refs must be empty",
        "b1_b3": "each injection needs source_hash, evidence_hash, snapshot_hash, injection_receipt_hash",
        "unknown_usage": "settlement.status=unknown_keeps_reserve",
        "missing_binding": "status remains missing/invalid; not rewritten as fail or pass",
        "fixture_cannot_be_paid": True,
    }


def budget_lock(funding: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "a5.pilot-budget-lock.v1",
        "currency": "CNY",
        "pilot_hard_cap": "50.000",
        "pilot_reference_ceiling": "46.080",
        "per_run_reference": "0.192",
        "runs": 240,
        "unknown_usage": "keep_reservation",
        "do_not_expand_runs_if_budget_remains": True,
        "memory_build_ledger": "separate_not_deducted_from_pilot",
        "legacy_combined_plan_not_used_as_pilot_mix": {
            "A5BudgetPlan_total": "50.000",
            "A5BudgetPlan_build": "3.840",
            "A5BudgetPlan_pilot": "46.080",
            "A5BudgetPlan_reserve": "0.080",
            "note": "obsolete mixed cap; this lock uses 50.000 as pilot hard cap and keeps memory build separate",
        },
        "funding_pilot_cap": funding.get("pilot_cap"),
        "funding_reference_ceiling": funding.get("pilot_reference_ceiling"),
        "execution_enabled": False,
        "paid": False,
        "model_calls": 0,
    }


def gate_report(*, canonical: dict[str, Any], image_handoff: dict[str, Any], binding_errors: list[str],
                binding_hash: str | None, frozen_fp: dict[str, Any], live_harness_fp: str,
                live_agent_fp: str, matrix_errors: list[str]) -> dict[str, Any]:
    targets = canonical.get("target_tasks") or []
    grader_ready = [row for row in targets if row.get("readiness") == "grader_ready"]
    awaiting = [row for row in targets if row.get("readiness") == "awaiting_repo_grader_readiness"]
    execution = canonical.get("execution") or {}
    frozen_harness = frozen_fp.get("harness_source_fingerprint")
    frozen_agent = frozen_fp.get("coding_agent_source_fingerprint")
    gates = [
        {
            "id": "target_grader_readiness",
            "status": "missing" if len(grader_ready) != 20 else "present",
            "grader_ready": len(grader_ready),
            "awaiting_repo_grader_readiness": len(awaiting),
            "assigned_targets": len(targets),
            "image_backed_initial24_grader_ready": (image_handoff.get("initial24") or {}).get("grader_ready"),
        },
        {
            "id": "model_binding",
            "status": "present" if binding_hash and not binding_errors else "missing",
            "hash": binding_hash,
            "errors": binding_errors,
        },
        {
            "id": "harness_fingerprint",
            "status": "drifted" if frozen_harness and frozen_harness != live_harness_fp else ("present" if live_harness_fp else "missing"),
            "frozen": frozen_harness,
            "live": live_harness_fp,
        },
        {
            "id": "agent_fingerprint",
            "status": "drifted" if frozen_agent and frozen_agent != live_agent_fp else ("present" if live_agent_fp else "missing"),
            "frozen": frozen_agent,
            "live": live_agent_fp,
        },
        {
            "id": "agent_b0b3_runtime_semantics",
            "status": "pending_h3",
        },
        {
            "id": "agent_snapshot_consumption",
            "status": "pending_h3",
            "canonical_validated_memory_records": execution.get("validated_memory_records"),
            "runnable_frozen": canonical.get("runnable_frozen"),
        },
        {
            "id": "paid_pilot_authorization",
            "status": "missing",
            "paid_pilot_started": execution.get("paid_pilot_started"),
        },
        {
            "id": "matrix",
            "status": "locked" if not matrix_errors else "invalid",
            "errors": matrix_errors,
        },
    ]
    blocking = [gate["id"] for gate in gates if gate["status"] in ("missing", "drifted", "invalid", "pending_h3")]
    return {
        "schema": "a5.missing-target-gates.v1",
        "status": "blocked",
        "blocking_gates": blocking,
        "gates": gates,
        "real_240_started": False,
        "paid": False,
        "model_calls": 0,
        "note": "H1 locks matrix/schema/budget but cannot start provider calls while target grader, fingerprint freeze, agent B0-B3 semantics, or paid authorization are missing",
    }


def lock_pilot(*, output_dir: Path, inputs: dict[str, Path] | None = None) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise ValueError("output directory must not already exist")
    output_dir.mkdir(parents=True)
    paths = inputs or default_inputs()
    assignments = json.loads(paths["assignments"].read_text(encoding="utf-8"))
    canonical = json.loads(paths["canonical_handoff"].read_text(encoding="utf-8"))
    consumption = json.loads(paths["consumption_manifest"].read_text(encoding="utf-8"))
    funding = json.loads(paths["funding"].read_text(encoding="utf-8"))
    image_handoff = json.loads(paths["image_handoff"].read_text(encoding="utf-8"))
    frozen_fp = json.loads(paths["fingerprint"].read_text(encoding="utf-8")) if paths["fingerprint"].is_file() else {}
    binding, binding_hash, binding_errors = load_price_binding(paths["model_binding"])
    live_harness_fp = source_fingerprint(ROOT)
    live_agent_fp, agent_files = scoped_fingerprint(
        AGENT_ROOT,
        ("reposkill_agent", "scripts", "configs/a5/pilot20-harness-consumption-manifest.json", "pyproject.toml"),
    )
    matrix, matrix_errors = audit_assignments(
        assignments, canonical.get("target_tasks") or [], consumption.get("target_id_mapping") or [],
    )
    schema = receipt_schema_lock()
    budget = budget_lock(funding)
    gates = gate_report(
        canonical=canonical, image_handoff=image_handoff, binding_errors=binding_errors,
        binding_hash=binding_hash, frozen_fp=frozen_fp, live_harness_fp=live_harness_fp,
        live_agent_fp=live_agent_fp, matrix_errors=matrix_errors,
    )
    execution_blocked = True
    input_hashes = {key: {"path": str(path.as_posix()), "sha256": sha_file(path) if path.is_file() else None}
                    for key, path in paths.items()}
    dump_json(output_dir / "pilot-matrix-lock.json", matrix)
    dump_json(output_dir / "receipt-schema-lock.json", schema)
    dump_json(output_dir / "pilot-budget-lock.json", budget)
    dump_json(output_dir / "missing-target-gates.json", gates)
    dump_json(output_dir / "fingerprint-live.json", {
        "schema": "a5.fingerprint-live.v1",
        "harness_source_fingerprint": live_harness_fp,
        "coding_agent_source_fingerprint": live_agent_fp,
        "coding_agent_files": agent_files,
        "frozen_harness_source_fingerprint": frozen_fp.get("harness_source_fingerprint"),
        "frozen_coding_agent_source_fingerprint": frozen_fp.get("coding_agent_source_fingerprint"),
        "model_binding_hash": binding_hash,
        "model_snapshot_id": binding.get("snapshot_id"),
    })
    readiness = {
        "schema": "a5.real240.h1-readiness.v1",
        "status": "blocked",
        "matrix_lock_status": matrix["lock_status"],
        "execution_status": "blocked",
        "real_240_started": False,
        "paid_pilot_started": False,
        "model_calls": 0,
        "paid": False,
        "blocking_gates": gates["blocking_gates"],
        "input_hashes": input_hashes,
        "success_conditions": [
            "240 unique assignment rows",
            "20 targets x B0/B1/B2/B3 x seeds 42/43/44",
            "B0 has no injection; B1-B3 require injection receipts",
            "receipt schema frozen",
            "pilot cap 50.000 CNY and reference ceiling 46.080 frozen",
        ],
        "failure_conditions": [
            "duplicate or missing assignment rows",
            "target/variant/repeat/seed mismatch",
        ],
        "stop_conditions": [
            "target grader missing",
            "model binding missing or unverified",
            "fingerprint missing or drifted",
            "do not start provider, model, memory build, or paid 240",
        ],
        "pending": [
            "H3 agent B0-B3 runtime semantics and injection receipts",
            "H3 20 target grader readiness",
            "H3 agent consumption of 11-record snapshot",
            "H3 dual hash re-freeze after both sides stabilize",
            "H4 explicit paid pilot authorization",
        ],
    }
    dump_json(output_dir / "readiness.json", readiness)
    write_artifact_manifest(output_dir)
    return {
        "status": "blocked",
        "matrix_lock_status": matrix["lock_status"],
        "assigned": matrix["assigned"],
        "blocking_gates": gates["blocking_gates"],
        "model_calls": 0,
        "paid": False,
        "real_240_started": False,
        "execution_blocked": execution_blocked,
        "output_dir": str(output_dir.as_posix()),
    }
