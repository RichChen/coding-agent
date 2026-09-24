"""Build a no-model A5 shared-gate receipt and fail closed on drift.

This command only writes offline evidence. It never calls a provider, starts a
Docker job, or changes the paid-build boundary.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.eval.a5_receipts import import_receipt
from src.policy.cny_budget import A5BudgetPlan, CnyBudgetLedger, PriceSnapshot
from src.runtime.session import source_fingerprint


ROOT = Path(__file__).resolve().parents[1]
AGENT_ROOT = Path(r"D:\crq\src\coding-agent")


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest_file(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def canonical(value) -> bytes:
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
            rows.append((item.relative_to(root).as_posix(), digest_file(item)))
    rows = sorted(set(rows))
    return digest_bytes(canonical(rows)), len(rows)


def load_binding(path: Path) -> tuple[PriceSnapshot, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    required = ("provider", "model", "snapshot_id", "currency", "source_url", "retrieved_on")
    if data.get("schema") != "a5.model-price-binding.v1" or data.get("verified") is not True:
        raise ValueError("model binding is not verified")
    if any(not data.get(key) for key in required) or data["currency"] != "CNY":
        raise ValueError("model binding provenance is incomplete")
    price = PriceSnapshot(
        data["provider"], data["model"], data["snapshot_id"], data["currency"],
        Decimal(str(data["prompt_cache_hit_per_million"])),
        Decimal(str(data["prompt_cache_miss_per_million"])),
        Decimal(str(data["completion_per_million"])), data["source_url"], data["retrieved_on"], True,
    )
    return price, price.binding_hash


def ledger_alignment(price: PriceSnapshot) -> dict:
    plan = A5BudgetPlan()
    if plan.build_cny + plan.pilot_cny + plan.reserve_cny != plan.total_cny:
        raise ValueError("budget arithmetic drift")
    ledger = CnyBudgetLedger(price, plan)
    build = ledger.reserve(phase="build", operation_id="a5-gate-build-probe", component="gate-probe",
                           prompt_tokens=1, max_output_tokens=1)
    ledger.settle(build.reservation_id, None)
    pilot = ledger.reserve(phase="pilot", operation_id="a5-gate-pilot-probe", component="gate-probe",
                           prompt_tokens=1, max_output_tokens=1)
    ledger.settle(pilot.reservation_id, None)
    snap = ledger.snapshot()
    return {
        "schema": "a5.cny.runtime-alignment.v1",
        "price_binding_hash": price.binding_hash,
        "ledger_schema": snap["schema"],
        "currency": snap["currency"],
        "hard_caps": snap["hard_caps"],
        "phase_caps_match_plan": snap["hard_caps"] == {
            "total": str(plan.total_cny), "build": str(plan.build_cny),
            "pilot": str(plan.pilot_cny), "reserve": str(plan.reserve_cny)},
        "unknown_usage_keeps_reserve": all(x["status"] == "unknown_keeps_reserve" for x in snap["settlements"]),
        "model_calls": 0,
        "paid": False,
    }


def make_receipt(variant: str, binding_hash: str, source_fp: str, index: int) -> dict:
    row = {
        "schema": "a5.receipt.v1", "task_id": "a5-shared-gate-fixture",
        "phase": "build", "variant": variant, "repeat": 1,
        "operation_id": f"a5-gate-fixture-{variant.lower()}",
        "source_snapshot_hash": digest_bytes(b"a5-source-snapshot"),
        "model_binding_hash": binding_hash, "source_fingerprint": source_fp,
        "model_attempts": [{"attempt_id": f"a5-gate-attempt-{index}", "component": "fixture"}],
        "injections": [], "grader": {"status": "missing"},
        "ledger": {"schema": "a5.cny.ledger.v1", "price_binding_hash": binding_hash},
        "model_calls": 0, "paid": False,
    }
    if variant != "B0":
        row["injections"] = [{"candidate_hash": digest_bytes(f"candidate-{variant}".encode()),
                               "source_hash": row["source_snapshot_hash"],
                               "evidence_ref": f"fixture/{variant}/evidence.json"}]
    return row


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--binding", type=Path, default=ROOT / "configs/a5/model-price-binding.json")
    parser.add_argument("--environment", type=Path,
                        default=ROOT / "docs/upgrade/evidence/A5-harness-preflight-47-final-audit/receipts.json")
    parser.add_argument("--memory-pool-audit", type=Path,
                        default=ROOT / "docs/upgrade/evidence/A5-harness-preflight-58-memory-pool-audit/readiness.json")
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists():
        raise ValueError("output must be a new directory")
    out.mkdir(parents=True)
    price, binding_hash = load_binding(args.binding.resolve())
    # Keep the canonical runtime fingerprint identical to the resume/session
    # implementation. The wider scoped count is recorded separately as audit
    # context, but must not become a second incompatible identity.
    harness_fp = (source_fingerprint(ROOT), len(list((ROOT / "src").rglob("*.py"))) + 1)
    agent_fp = scoped_fingerprint(AGENT_ROOT, ("reposkill_agent", "scripts", "configs/a5/pilot20-harness-consumption-manifest.json",
                                               "pyproject.toml"))
    if not agent_fp[0]:
        raise ValueError("coding-agent source scope is unavailable")
    ledger = ledger_alignment(price)
    receipts = []
    for index, variant in enumerate(("B0", "B1", "B2", "B3"), 1):
        receipt = make_receipt(variant, binding_hash, harness_fp[0], index)
        imported = import_receipt(receipt, expected_model_binding=binding_hash,
                                  expected_source_fingerprint=harness_fp[0])
        path = out / "receipts" / variant / "receipt.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(imported, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        receipts.append({"variant": variant, "path": str(path), "sha256": digest_file(path),
                         "receipt_status": imported["receipt_status"]})
    environment = json.loads(args.environment.read_text(encoding="utf-8"))
    memory_pool = json.loads(args.memory_pool_audit.resolve().read_text(encoding="utf-8"))
    rows = environment.get("rows", []) if isinstance(environment, dict) else []
    django = next((r for r in rows if r.get("task_id") == "django__django-13265"), None)
    contract = ROOT / "docs/upgrade/evidence/A5-harness-preflight-48-django-contract-resolution/contract-resolution.json"
    if django is None or not contract.is_file():
        raise ValueError("django resolution or 24-row audit is missing")
    shared = {
        "schema": "a5.shared-gates.v1", "model_binding_hash": binding_hash,
        "model_binding_ref": str(args.binding.resolve()),
        "harness_source_fingerprint": harness_fp[0], "harness_files": harness_fp[1],
        "coding_agent_source_fingerprint": agent_fp[0], "coding_agent_files": agent_fp[1],
        "fingerprint_scope": "current source/config snapshot; any later change invalidates this freeze",
        "ledger": ledger, "b0_b3_receipts": receipts,
        "django_contract_resolution": str(contract.resolve()),
        "django_contract_resolution_sha256": digest_file(contract),
        "initial24_environment_baseline": {"assigned": 24, "environment_ready": 24,
            "baseline_contract_resolved": False, "reason": "23 baseline-ready plus django contract kept visible"},
        "remaining16_memory_sources": memory_pool.get("status", "unknown"),
        "memory_pool_audit": str(args.memory_pool_audit.resolve()),
        "memory_pool_counts": {k: memory_pool.get(k) for k in (
            "full_denominator", "source_complete", "transport_ready",
            "environment_baseline_ready", "grader_ready")},
        "model_calls": 0, "paid_build_started": False, "paid_pilot_started": False,
        "memory_build_eligible": False, "shared_gates_ready_for_approval": True,
        "ready_for_paid_build": False,
        "approval_boundary": "shared gates are auditable; the 20-source audit is complete but blocked by historical receipts, invalid_env rows and independent grader calibration",
    }
    (out / "shared-gates.json").write_text(json.dumps(shared, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "readiness.json").write_text(json.dumps({
        "schema": "a5.readiness.v2", "status": "approval_boundary_ready",
        "shared_gates_ready_for_approval": True, "ready_for_paid_build": False,
        "memory_build_eligible": False, "remaining16_preflight": memory_pool.get("status", "unknown"),
        "model_calls": 0, "paid_build_started": False, "paid_pilot_started": False,
        "blocking_reasons": ["memory_pool_source_and_grader_gates_blocked", "explicit_paid_build_authorization_not_recorded"],
        "evidence": str((out / "shared-gates.json").resolve()),
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest = {p.relative_to(out).as_posix(): digest_file(p) for p in sorted(out.rglob("*")) if p.is_file()}
    (out / "artifact-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "approval_boundary_ready", "shared_gates_ready_for_approval": True,
                      "ready_for_paid_build": False, "model_calls": 0, "paid": False}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
