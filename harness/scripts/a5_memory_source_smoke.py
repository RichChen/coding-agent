#!/usr/bin/env python3
"""Paid S1 smoke/build for one A5 memory source (image-backed + DeepSeek).

Public agent sees only the public issue/source image. Private gold/test patches
and hidden grader details stay on the host and are never written into the public
trajectory. Requires --allow-paid.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
import sys
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.eval.a5_image_tree import canonical, validate_delta
from src.eval.contracts import canonical_hash
from src.execution.a5_image_backend import A5ImageBackend
from src.harness.factory import build_agent, load_config
from src.policy.cny_budget import CnyBudgetLedger, PriceSnapshot, money
from src.runtime.session import RunSession, compatibility, plain, source_fingerprint
from src.tracing.store import utc_now

AGENT_ROOT = ROOT.parent / "coding-agent"
FUNDED = AGENT_ROOT / "reports/upgrade/a5-funded-build-preparation-20260921-v12"
CONSUMPTION = AGENT_ROOT / "configs/a5/pilot20-harness-consumption-manifest.json"
HISTORY_BASELINE = ROOT / "docs/upgrade/evidence/A5-harness-preflight-62-history-baseline-retry"
REMAINING_BASELINE = ROOT / "docs/upgrade/evidence/A5-harness-preflight-57-remaining16-baseline"
TRANSPORT_HISTORY = ROOT / "docs/upgrade/evidence/A5-harness-preflight-23-transport-smoke"
TRANSPORT_REMAINING = ROOT / "docs/upgrade/evidence/A5-harness-preflight-55-remaining16-transport"
HISTORY_IDS = {
    "django__django-10914",
    "sympy__sympy-11400",
    "scikit-learn__scikit-learn-10297",
    "pytest-dev__pytest-5103",
}
PREFIXES = {
    # Broad enough for explore-then-edit smoke: package + docs; still only public tree files.
    "django/django": ("django/", "docs/", "tests/"),
    "sympy/sympy": ("sympy/", "doc/", "docs/"),
    "scikit-learn/scikit-learn": ("sklearn/", "doc/", "examples/"),
    "pytest-dev/pytest": ("src/", "testing/", "doc/", "docs/", "changelog/"),
}


def load(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def price_from_binding(path: Path) -> PriceSnapshot:
    data = load(path)
    return PriceSnapshot(
        provider=data["provider"],
        model=data["model"],
        snapshot_id=data["snapshot_id"],
        currency=data["currency"],
        prompt_cache_hit_per_million=money(data["prompt_cache_hit_per_million"]),
        prompt_cache_miss_per_million=money(data["prompt_cache_miss_per_million"]),
        completion_per_million=money(data["completion_per_million"]),
        source_url=data["source_url"],
        retrieved_on=data["retrieved_on"],
        verified=bool(data.get("verified")),
    )


def editable_paths(manifest: dict, repo: str) -> list[str]:
    prefixes = PREFIXES.get(repo)
    if not prefixes:
        raise ValueError("unsupported repo family for editable allowlist")
    paths = [
        name
        for name, meta in manifest["entries"].items()
        if meta.get("kind") == "file" and any(name == p or name.startswith(p) for p in prefixes)
    ]
    if not paths:
        raise ValueError("empty editable allowlist")
    return paths


def min_gate(source_id: str) -> dict:
    baseline_root = HISTORY_BASELINE if source_id in HISTORY_IDS else REMAINING_BASELINE
    receipt_path = baseline_root / "tasks" / source_id / "receipt.json"
    if not receipt_path.exists():
        return {"ok": False, "status": "missing_receipt", "reason": "baseline_receipt_missing", "ref": str(receipt_path)}
    receipt = load(receipt_path)
    if receipt.get("status") != "baseline_ready":
        return {"ok": False, "status": "invalid_env", "reason": "baseline_not_ready", "ref": str(receipt_path), "environment_status": receipt.get("status")}
    collection = (receipt.get("collection") or {}).get("status")
    if collection != "ready":
        return {"ok": False, "status": "invalid_env", "reason": "collection_not_ready", "ref": str(receipt_path), "collection_status": collection}
    transport = receipt.get("transport_image_digest")
    tree = (receipt.get("snapshot_binding") or {}).get("original_tree_hash")
    if not transport or not tree:
        return {"ok": False, "status": "invalid_env", "reason": "missing_transport_or_tree_hash", "ref": str(receipt_path)}
    return {
        "ok": True,
        "status": "pass",
        "ref": str(receipt_path),
        "transport_image_digest": transport,
        "source_tree_hash": tree,
        "base_revision": receipt.get("base_revision"),
        "repo": receipt.get("repo"),
        "cleanup_verified": receipt.get("cleanup_verified"),
        "baseline_root": str(baseline_root),
    }


def resolve_transport_manifest(source_id: str) -> Path:
    root = TRANSPORT_HISTORY if source_id in HISTORY_IDS else TRANSPORT_REMAINING
    path = root / "tasks" / source_id / "build" / "a5-tree.json"
    if not path.exists():
        raise FileNotFoundError(f"typed tree manifest missing: {path}")
    return path


def public_prompt(task: dict) -> str:
    issue = task.get("issue_text") or ""
    repo = (task.get("repo_ref") or {}).get("repo_id", "")
    rev = (task.get("repo_ref") or {}).get("revision", "")
    return (
        "You are repairing an open-source repository from a public issue only.\n"
        f"Repository: {repo}\nBase revision: {rev}\n"
        "The full source tree is already present under /workspace.\n"
        "Required workflow:\n"
        "1) Use list_dir/read_file/search_replace or edit_file to inspect and change source files.\n"
        "2) You MUST apply at least one real source edit with edit_file or search_replace.\n"
        "3) Do not spend the budget only on shell exploration; avoid creating __pycache__.\n"
        "4) Prefer PYTHONDONTWRITEBYTECODE=1 if you run python.\n"
        "5) Do not invent private tests or hidden oracles.\n\n"
        f"Public issue:\n{issue}"
    )


def trajectory_from_run(run: dict, public_verification: str, failure_notes: list[str]) -> dict:
    actions = []
    evidence = []
    for step in run.get("steps") or []:
        thought = (step.get("llm_text") or step.get("thought") or "").strip()
        if thought:
            evidence.append(thought[:500])
        for call in step.get("tool_calls") or []:
            name = call.get("name") or call.get("tool") or "tool"
            args = call.get("arguments") or call.get("args") or {}
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except Exception:
                    args = {}
            path = ""
            if isinstance(args, dict):
                path = args.get("path") or args.get("file") or ""
            actions.append(f"{name}:{path}" if path else str(name))
        for result in step.get("tool_results") or []:
            obs = result.get("output") or result.get("content") or result.get("observation") or ""
            if isinstance(obs, str) and obs.strip():
                evidence.append(obs.strip()[:300])
    return {
        "issue_summary": "",
        "public_evidence": tuple(evidence[:40]) if evidence else ("agent_ran_without_textual_evidence",),
        "actions": tuple(actions[:80]) if actions else ("no_tool_actions_recorded",),
        "public_verification": public_verification,
        "failure_notes": tuple(failure_notes),
    }


def usage_from_run(run: dict) -> dict:
    attempts = run.get("llm_attempts") or []
    prompt = completion = 0
    known = unknown = 0
    for item in attempts:
        usage = item.get("usage") or {}
        if not usage:
            unknown += 1
            continue
        known += 1
        prompt += int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
        completion += int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
    return {
        "model_attempts": len(attempts),
        "known_usage_attempts": known,
        "unknown_usage_attempts": unknown,
        "prompt_tokens": prompt,
        "completion_tokens": completion,
    }


async def independent_validate(image: str, manifest: dict, editable: list[str], delta: dict | None, out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    if delta is None:
        receipt = {"status": "fail", "reason": "missing_candidate_delta", "cleanup_verified": None}
        save(out / "receipt.json", receipt)
        return receipt
    try:
        validate_delta(manifest, delta, editable)
    except Exception as exc:
        receipt = {"status": "fail", "reason": "delta_invalid:" + type(exc).__name__ + ": " + str(exc)[:300], "cleanup_verified": None}
        save(out / "receipt.json", receipt)
        return receipt
    backend = A5ImageBackend(
        manifest=manifest,
        editable_paths=editable,
        image=image,
        memory_bytes=1024**3,
        workspace_bytes=256 * 1024**2,
        tmpfs_bytes=64 * 1024**2,
    )
    try:
        await backend.start()
        candidate_hash = await backend.apply_candidate(delta)
        # Public smoke only: confirm seeded workspace tree remains present after apply.
        # Transport images are source trees, not fully installed package environments.
        code, stdout, stderr = await backend._control(
            "exec",
            backend.name,
            "/usr/local/bin/python",
            "-I",
            "-S",
            "-c",
            "from pathlib import Path; root=Path('/workspace'); "
            "print('tree-ok' if root.is_dir() and any(root.iterdir()) else 'tree-bad')",
            limit=64 * 1024,
            timeout=60,
        )
        public_ok = code == 0 and b"tree-ok" in stdout
        changed_n = len(delta.get("changed") or {})
        deleted_n = len(delta.get("deleted") or [])
        if public_ok and changed_n + deleted_n == 0:
            receipt = {
                "status": "fail",
                "reason": "no_candidate_changes",
                "candidate_tree_hash": candidate_hash,
                "public_tree_exit_code": code,
                "public_tree_stdout_sha256": sha_bytes(stdout),
                "delta_schema": delta.get("schema"),
                "delta_changed_files": changed_n,
                "delta_deleted_files": deleted_n,
                "model_calls": 0,
                "paid": False,
                "private_grader": "not_run_in_s1_smoke; host_private_specs_retained_offline",
            }
        else:
            receipt = {
                "status": "pass" if public_ok and changed_n + deleted_n > 0 else "fail",
                "reason": None if public_ok and changed_n + deleted_n > 0 else "public_tree_smoke_failed_or_empty_delta",
                "candidate_tree_hash": candidate_hash,
                "public_tree_exit_code": code,
                "public_tree_stdout_sha256": sha_bytes(stdout),
                "public_tree_stderr_sha256": sha_bytes(stderr),
                "delta_schema": delta.get("schema"),
                "delta_changed_files": changed_n,
                "delta_deleted_files": deleted_n,
                "model_calls": 0,
                "paid": False,
                "private_grader": "not_run_in_s1_smoke; host_private_specs_retained_offline",
            }
    except Exception as exc:
        receipt = {
            "status": "invalid_env",
            "reason": type(exc).__name__ + ": " + str(exc)[:500],
            "model_calls": 0,
            "paid": False,
        }
    finally:
        await backend.close()
        receipt["cleanup_verified"] = backend.cleanup_ok
    save(out / "receipt.json", receipt)
    return receipt


async def run_one(args) -> int:
    source_id = args.source
    output = Path(args.output_dir).resolve()
    output.mkdir(parents=True, exist_ok=False)
    started = utc_now()
    gate = min_gate(source_id)
    save(output / "min-gate.json", gate)
    if not gate["ok"]:
        save(
            output / "readiness.json",
            {
                "status": gate["status"],
                "source_id": source_id,
                "model_calls": 0,
                "paid": False,
                "reason": gate.get("reason"),
                "started_at": started,
            },
        )
        return 2

    mapping = {row["canonical_id"]: row for row in load(CONSUMPTION)["memory_source_id_mapping"]}
    meta = mapping[source_id]
    public_task_path = FUNDED / "public" / f"{meta['agent_task_id']}.json"
    public_task = load(public_task_path)
    if public_task.get("gold_patch") or public_task.get("test_patch"):
        raise ValueError("public task must not embed private patches")
    manifest_path = resolve_transport_manifest(source_id)
    manifest = load(manifest_path)
    if manifest["source_tree_hash"] != gate["source_tree_hash"]:
        raise ValueError("transport manifest tree hash drift vs baseline gate")
    image = gate["transport_image_digest"]
    if not re.fullmatch(r"[^\s@]+@sha256:[0-9a-f]{64}", image or ""):
        raise ValueError("transport image digest not pinned")
    editable = editable_paths(manifest, gate["repo"])
    save(
        output / "public-input.json",
        {
            "source_id": source_id,
            "canonical_id": source_id,
            "agent_task_id": meta["agent_task_id"],
            "job_id": meta["job_id"],
            "repo": gate["repo"],
            "base_revision": gate["base_revision"],
            "public_task_path": str(public_task_path),
            "public_task_sha256": sha_file(public_task_path),
            "transport_image_digest": image,
            "source_tree_hash": gate["source_tree_hash"],
            "typed_tree_manifest_ref": str(manifest_path),
            "typed_tree_manifest_sha256": sha_file(manifest_path),
            "editable_path_count": len(editable),
            "editable_prefixes": list(PREFIXES[gate["repo"]]),
            "private_specs_host_only": True,
        },
    )

    config = load_config(args.config)
    if not args.allow_paid:
        raise SystemExit("real API calls require --allow-paid")
    if not config["llm"]["api_key"]:
        raise SystemExit("LLM_API_KEY is not configured")
    if config["llm"]["base_url"] != "https://api.deepseek.com/v1" or config["llm"]["model"] != "deepseek-flash":
        raise SystemExit("memory smoke requires official DeepSeek deepseek-flash binding")
    if config["llm"].get("thinking") != "disabled":
        raise SystemExit("thinking must be disabled")

    price = price_from_binding(ROOT / "configs/a5/model-price-binding.json")
    # Independent memory-build ledger for this attempt (user-authorized; not stolen from pilot).
    ledger = CnyBudgetLedger(
        price,
        plan=__import__("src.policy.cny_budget", fromlist=["A5BudgetPlan"]).A5BudgetPlan(
            total_cny=Decimal("50.000"),
            build_cny=Decimal("20.000"),
            pilot_cny=Decimal("29.920"),
            reserve_cny=Decimal("0.080"),
            build_calls=120,
            pilot_calls=1,
        ),
    )
    operation_id = f"a5-s1-{source_id}-{uuid.uuid4().hex[:12]}"
    reservation = ledger.reserve(
        phase="build",
        operation_id=operation_id,
        component="repair",
        # Reserve for a multi-step explore-then-edit run (aligned with raised smoke caps).
        prompt_tokens=120_000,
        max_output_tokens=24_000,
    )
    save(
        output / "budget-reservation.json",
        {
            "operation_id": operation_id,
            "reservation_id": reservation.reservation_id,
            "phase": "build",
            "reserved_cny": str(reservation.reserved_cny),
            "price_binding_hash": price.binding_hash,
            "authorization": "user_authorized_s1_six_sources_2026-09-22",
        },
    )

    seed_dir = output / "public-seed"
    seed_dir.mkdir()
    backend = A5ImageBackend(
        manifest=manifest,
        editable_paths=editable,
        image=image,
        context=config["policy"]["command"].get("docker_context", "desktop-linux"),
        memory_bytes=config["policy"]["command"].get("docker_memory_bytes", 1024**3),
        workspace_bytes=config["policy"]["command"].get("docker_workspace_bytes", 256 * 1024**2),
        tmpfs_bytes=config["policy"]["command"].get("docker_tmpfs_bytes", 64 * 1024**2),
    )
    backend.seed_files = {}
    agent = build_agent(config, seed_dir, execution_backend=backend)
    prompt = public_prompt(public_task)
    # Fill issue_summary later into trajectory from public task text.
    run_dir = output / "run"
    run_dir.mkdir()
    code_id = source_fingerprint(ROOT)
    expected = compatibility(
        workspace=seed_dir,
        code_id=code_id,
        config={"hash": canonical_hash(config)},
        backend=backend.capabilities,
    )
    failure_notes: list[str] = []
    run_plain = {}
    validation = {"status": "missing_receipt"}
    try:
        with RunSession.create(
            run_dir / "session",
            task_id=meta["agent_task_id"],
            expected=expected,
            timeout_seconds=agent.budget.total_timeout_seconds,
        ) as session:
            result = await session.run(agent, prompt)
            run_plain = plain(result)
            save(run_dir / "run-result.json", run_plain)
            session.store.export_jsonl(run_dir / "events.jsonl")
    except Exception as exc:
        failure_notes.append(type(exc).__name__ + ": " + str(exc)[:500])
        run_plain = {"success": False, "failure_reason": "backend_or_session_error", "steps": [], "llm_attempts": []}
        save(run_dir / "run-result.json", {"error": failure_notes[-1]})
    finally:
        aclose = getattr(agent.llm, "aclose", None)
        if callable(aclose):
            await aclose()

    delta = getattr(backend, "candidate_delta", None)
    if delta is not None:
        save(output / "candidate-delta.json", delta)
    save(
        output / "cleanup.json",
        {
            "cleanup_verified": backend.cleanup_ok,
            "snapshot_error": backend.snapshot_error,
            "lifecycle": backend.lifecycle,
            "capabilities": backend.capabilities,
        },
    )

    validation = await independent_validate(image, manifest, editable, delta, output / "validation")
    usage = usage_from_run(run_plain)
    settle_usage = None
    if usage["unknown_usage_attempts"]:
        settle_usage = None  # keep reserve
    else:
        settle_usage = {
            "prompt_tokens": usage["prompt_tokens"],
            "completion_tokens": usage["completion_tokens"],
            "cache_hit_tokens": 0,
        }
    settled = ledger.settle(reservation.reservation_id, settle_usage)
    save(output / "cost-entry.json", {"usage": usage, "settlement": settled, "ledger_snapshot": ledger.snapshot()})

    if validation.get("status") != "pass":
        failure_notes.append("validation:" + str(validation.get("status")) + ":" + str(validation.get("reason")))
    public_verification = (
        f"independent_delta_apply_and_public_import:{validation.get('status')};"
        f"changed={validation.get('delta_changed_files')};cleanup={validation.get('cleanup_verified')}"
    )
    traj = trajectory_from_run(run_plain, public_verification, failure_notes)
    traj["issue_summary"] = (public_task.get("issue_text") or "")[:800]
    traj_text = json.dumps(
        {
            "issue_summary": traj["issue_summary"],
            "public_evidence": list(traj["public_evidence"]),
            "actions": list(traj["actions"]),
            "public_verification": traj["public_verification"],
            "failure_notes": list(traj["failure_notes"]),
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    traj_path = output / "public-trajectory.json"
    traj_path.write_text(traj_text + "\n", encoding="utf-8")

    # Candidate MemoryRecord shape (not validated). No private grader text.
    decision = "candidate" if validation.get("status") == "pass" and delta else "failed"
    if validation.get("status") == "invalid_env":
        decision = "invalid_env"
    memory_candidate = {
        "schema": "a5.memory-record.candidate.v1",
        "state": decision if decision == "candidate" else "rejected_or_failed",
        "source_id": source_id,
        "repo": gate["repo"],
        "base_revision": gate["base_revision"],
        "source_tree_hash": gate["source_tree_hash"],
        "transport_image_digest": image,
        "trajectory_sha256": sha_file(traj_path),
        "trajectory_ref": str(traj_path.relative_to(output)),
        "run_attempt_id": operation_id,
        "candidate_delta_sha256": sha_file(output / "candidate-delta.json") if delta is not None else None,
        "validation_receipt_ref": "validation/receipt.json",
        "validation_status": validation.get("status"),
        "provenance_review": "pending_human_or_rule_review",
        "model_calls": usage["model_attempts"],
        "paid": usage["model_attempts"] > 0,
        "created_at": utc_now(),
    }
    save(output / "memory-candidate.json", memory_candidate)
    save(
        output / "provenance-review.json",
        {
            "source_id": source_id,
            "reviewed": False,
            "public_private_boundary": "public_transport_image_only",
            "private_data_in_public_artifacts": False,
            "gold_patch_copied": False,
            "decision": decision,
            "notes": failure_notes,
            "reviewed_at": None,
        },
    )
    save(
        output / "readiness.json",
        {
            "status": decision,
            "source_id": source_id,
            "validation_status": validation.get("status"),
            "cleanup_verified": backend.cleanup_ok,
            "model_calls": usage["model_attempts"],
            "paid": usage["model_attempts"] > 0,
            "operation_id": operation_id,
            "started_at": started,
            "finished_at": utc_now(),
        },
    )
    files = {p.relative_to(output).as_posix(): sha_file(p) for p in sorted(output.rglob("*")) if p.is_file()}
    save(output / "artifact-manifest.json", {"schema": "a5.artifact-manifest.v1", "files": files, "model_calls": usage["model_attempts"], "paid": usage["model_attempts"] > 0})
    print(json.dumps({"source_id": source_id, "decision": decision, "validation": validation.get("status"), "model_calls": usage["model_attempts"], "output": str(output)}, ensure_ascii=False))
    return 0 if decision == "candidate" else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--config", default="configs/memory-smoke-a5.yaml")
    parser.add_argument("--allow-paid", action="store_true")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run_one(args)))


if __name__ == "__main__":
    main()
