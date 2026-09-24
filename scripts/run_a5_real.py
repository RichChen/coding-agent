"""Run the authorized A5 canary/matrix through the harness host.

The runner owns Docker, model calls, receipts and grading. RepoSkill is loaded
as a policy plugin and only returns bounded public candidates.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path
import sys
from decimal import Decimal

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.eval.grader import tree_hash
from src.eval.repo_grader import RepositoryGrader, RepositorySpec
from src.execution.a5_image_backend import A5ImageBackend
from src.eval.a5_image_tree import apply_delta
from src.harness.factory import build_agent, load_config
from src.policy.cny_budget import A5BudgetPlan, CnyBudgetLedger, PriceSnapshot
from src.policy.registry import PolicyPluginRegistry
from src.policy.reposkill import register_public_memory, source_digest
from src.runtime.session import RunSession, compatibility, plain
from src.tracing.store import utc_now

AGENT = ROOT.parent / "coding-agent"
SNAPSHOT = ROOT / "docs/upgrade/evidence/A5-real240-77-harness-preflight/memory-snapshot.jsonl"
ASSIGNMENTS = AGENT / "reports/upgrade/a5-pilot20-preparation-20260921-v4/assignments.json"
PUBLIC = AGENT / "reports/upgrade/a5-pilot20-preparation-20260921-v4/public"
PRIVATE = AGENT / "reports/upgrade/a5-pilot20-preparation-20260921-v4/private/tasks"
TRANSPORT_MANIFEST = ROOT / "docs/upgrade/evidence/A5-harness-preflight-22-typed-tree/tasks/pytest-dev__pytest-7220/typed-tree-manifest.json"
TRANSPORT_IMAGE = "coding-harness-a5-transport@sha256:ee3bcdba5816a3f290dd722f7f09dc9f823600c2a2be7a3009aef328b32bc150"
GRADER_IMAGE = "coding-harness-a5-pytest@sha256:5ff30847f41f513cf4d1f1b2fa61c5f1bf07a1e"
GRADER_IMAGE = "coding-harness-a5-pytest@sha256:5ff30847f41d2c2c66f161c8b97a3bba9a2b11823be8cff8c1f5f896babdb376"

# A5 protocol v9 aligns context handling with the paid memory smoke profile.
# v6/v7/v8 remain historical evidence and are never overwritten.
PROFILE_VERSION = "a5-real240-v9"
PROFILE = {
    "max_steps": 35,
    "total_timeout_seconds": 1200,
    "step_timeout_seconds": 120,
    "context_strategy": "masking",
    "keep_recent_tool_results": 4,
    "context_max_tokens": 96_000,
    "tool_output_max_chars": 12_000,
    "max_model_calls": 24,
    "max_tokens": 2_592_000,  # 24 * (96k input + 12k output) worst-case reserve
    "llm_max_tokens": 12_000,
    "max_cost_usd": 1.50,
}


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_file(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def injection_refs(events):
    model_events = [e for e in events if e.get("event_type") == "model.started"]
    injections = []
    for event in events:
        if event.get("event_type") != "context.prepared":
            continue
        stats = (event.get("payload") or {}).get("stats") or {}
        for item in ((stats.get("plugin") or {}).get("actually_injected") or []):
            if not item.get("source"):
                continue
            actual = next((m["content"] for m in event["payload"]["view"]
                           if m.get("role") == "user" and isinstance(m.get("content"), str)
                           and m["content"].startswith("[Untrusted policy candidate; source=" + item["source"] + "]")), None)
            bound = next((m for m in model_events if m["seq"] > event["seq"]), None)
            if actual is None or bound is None:
                continue
            ref = {"source_hash": item["source"], "evidence_hash": sha_bytes(actual.encode()),
                   "snapshot_hash": sha_file(SNAPSHOT), "requested_hash": item["sha256"],
                   "actual_hash": sha_bytes(actual.encode()), "model_operation_id": bound["operation_id"],
                   "model_attempt_id": bound["attempt_id"], "candidate_id": item["id"],
                   "context_event_seq": event["seq"]}
            ref["injection_receipt_hash"] = sha_bytes(json.dumps(ref, sort_keys=True).encode())
            injections.append(ref)
    return injections


def assignments():
    rows = load_json(ASSIGNMENTS)
    return [{**r, "canonical_target_id": "pytest-dev__pytest-7220", "experiment_id": "a5-pilot-20-v1",
             "agent_task_id": r["task_id"], "organization_seed": r["organization_seed"]}
            for r in rows if r["task_id"] == "a5-task-e726f5f0ccb4ea85" and r["repeat_id"] == 0 and r["organization_seed"] == 42]


def base_and_overlay():
    from src.execution.docker import read_workspace
    base = read_workspace(ROOT / ".tmp-canary-pytest-7220/workspace")
    source = load_json(PRIVATE / "a5-task-e726f5f0ccb4ea85/source-row.json")
    test_file = ROOT / "docs/upgrade/evidence/A5-harness-preflight-14-host-pytest/tasks/pytest-dev__pytest-7220/private-baseline/testing/test_nodes.py"
    overlay = {"testing/test_nodes.py": test_file.read_bytes()}
    f2p = tuple(json.loads(source["FAIL_TO_PASS"]))
    p2p = tuple(json.loads(source["PASS_TO_PASS"]))
    spec = RepositorySpec(task_id="pytest-dev__pytest-7220", base_hash=tree_hash(base),
                          image=GRADER_IMAGE, editable_paths=("src/_pytest/nodes.py", "src/_pytest/pathlib.py"),
                          test_paths=("testing/test_nodes.py",), python_paths=("testing",),
                          expected_nodeids=f2p + p2p, test_overlay={k: base64.b64encode(v).decode() for k,v in overlay.items()},
                          baseline_passed=p2p, timeout_seconds=120)
    return base, spec


def make_ledger(state_path=None):
    price = PriceSnapshot(provider="DeepSeek", model="deepseek-flash",
                          snapshot_id="DeepSeek-V4.1-Flash", currency="CNY",
                          prompt_cache_hit_per_million=__import__("decimal").Decimal("0.040"),
                          prompt_cache_miss_per_million=__import__("decimal").Decimal("2.000"),
                          completion_per_million=__import__("decimal").Decimal("8.000"),
                          source_url="https://api-docs.deepseek.com/quick_start/pricing",
                          retrieved_on="2026-09-21", verified=True)
    ledger = CnyBudgetLedger(price, A5BudgetPlan(total_cny=Decimal("50.000"),
        build_cny=__import__("decimal").Decimal("0.000"), pilot_cny=__import__("decimal").Decimal("50.000"),
        reserve_cny=__import__("decimal").Decimal("0.000"), build_calls=0, pilot_calls=1440), state_path=state_path)
    # v6 had six real attempts whose receipt writer crashed; v7 had 24 attempts.
    # Both are carried into the new persistent ledger before v8 starts.
    ledger.calls_started = 30
    ledger.phase_calls["pilot"] = 30
    ledger.cost_committed = Decimal("0.239")
    ledger.phase_cost["pilot"] = Decimal("0.239")
    ledger.settlements = [{"source": "a5-canary-v6", "status": "historical_import", "cost_cny": "0.050",
                           "calls": 6},
                          {"source": "a5-canary-v7", "status": "historical_import", "cost_cny": "0.189",
                           "calls": 24},
                          {"source": "a5-canary-v8", "status": "historical_import", "cost_cny": "0.175",
                           "calls": 9}]
    ledger.calls_started = 39
    ledger.phase_calls["pilot"] = 39
    ledger.cost_committed = Decimal("0.414")
    ledger.phase_cost["pilot"] = Decimal("0.414")
    ledger.persist()
    return ledger


async def run_one(row, output: Path, ledger: CnyBudgetLedger, base, spec):
    output.mkdir(parents=True, exist_ok=False)
    (output / "workspace").mkdir()
    run_cost_before = ledger.cost_committed
    run_calls_before = ledger.calls_started
    task = load_json(PUBLIC / "tasks" / (row["agent_task_id"] + ".json"))
    manifest = load_json(TRANSPORT_MANIFEST)
    backend = A5ImageBackend(manifest=manifest, editable_paths=list(spec.editable_paths), image=TRANSPORT_IMAGE,
                             context="desktop-linux", memory_bytes=1024**3, workspace_bytes=256*1024**2,
                             tmpfs_bytes=64*1024**2, network="none")
    registry = PolicyPluginRegistry()
    source_root = AGENT
    approved = source_digest(source_root)
    config = load_config(ROOT / "configs/deepseek.yaml")
    config["llm"]["max_tokens"] = PROFILE["llm_max_tokens"]
    config["runtime"].update(max_steps=PROFILE["max_steps"],
                              total_timeout_seconds=PROFILE["total_timeout_seconds"],
                              step_timeout_seconds=PROFILE["step_timeout_seconds"])
    config["runtime"]["context"].update(strategy=PROFILE["context_strategy"],
                                         max_tokens=PROFILE["context_max_tokens"],
                                         keep_recent_tool_results=PROFILE["keep_recent_tool_results"],
                                         plugin="reposkill", max_injection_bytes=4096)
    config["policy"]["tool_output_max_chars"] = PROFILE["tool_output_max_chars"]
    config["runtime"]["budget"].update(max_model_calls=PROFILE["max_model_calls"],
                                        max_tokens=PROFILE["max_tokens"], max_cost_usd=PROFILE["max_cost_usd"],
                                        price_table={"prompt_per_1k": 0.0003, "completion_per_1k": 0.0012})
    config["retry"]["max_retries"] = 1
    config["policy"]["command"]["docker_image"] = TRANSPORT_IMAGE
    register_public_memory(registry, source_root=source_root, approved_sha256=approved,
                           public_task=task, variant=row["variant"], snapshot_path=SNAPSHOT,
                           target_root=ROOT / ".tmp-canary-pytest-7220/workspace")
    agent = build_agent(config, output / "workspace", plugin_registry=registry, execution_backend=backend)
    agent.public_repo_revision = task["repo_ref"]["revision"]
    agent.retry.cny_ledger = ledger
    expected = compatibility(workspace=output / "workspace", code_id=sha_file(ROOT / "src/runtime/loop.py"),
                             config={"hash": sha_bytes(json.dumps(config, sort_keys=True).encode())},
                             backend=backend.capabilities)
    run_error = None
    result = None
    try:
        with RunSession.create(output / "session", task_id=task["task_id"], expected=expected,
                               timeout_seconds=PROFILE["total_timeout_seconds"]) as session:
            result = await session.run(agent, json.dumps({"task_id": task["task_id"], "issue_text": task["issue_text"]}))
            session.store.export_jsonl(output / "events.jsonl")
            (output / "run-result.json").write_text(json.dumps(plain(result), ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as exc:
        run_error = type(exc).__name__ + ": " + str(exc)[:500]
    finally:
        await agent.llm.aclose()
    delta = backend.candidate_delta
    if delta is not None:
        (output / "candidate-delta.json").write_text(json.dumps(delta, indent=2), encoding="utf-8")
    candidate = None
    if delta is not None:
        candidate = dict(base)
        for name in delta.get("deleted", []): candidate.pop(name, None)
        for name, change in delta.get("changed", {}).items(): candidate[name] = base64.b64decode(change["content"])
    evaluation = await RepositoryGrader(context="desktop-linux").evaluate(base, candidate, spec)
    (output / "grader-result.json").write_text(json.dumps(evaluation, indent=2), encoding="utf-8")
    attempts = (plain(result) if result else {}).get("llm_attempts", [])
    events = load_events(output / "events.jsonl") if (output / "events.jsonl").exists() else []
    model_events = [e for e in events if e.get("event_type") == "model.started"]
    if model_events:
        operation_id = model_events[0].get("operation_id")
        attempt_ids = [e.get("attempt_id") for e in model_events if e.get("attempt_id")]
    else:
        operation_id, attempt_ids = None, []
    injections = injection_refs(events)
    # The event stream may externalize later context stats as artifact refs. Prefer
    # the loop's returned context_events, which retain the admission numbers for
    # every model request, and fall back to inline event payloads for old runs.
    result_plain = plain(result) if result else {}
    prepared_stats = list(result_plain.get("context_events") or [])
    if not prepared_stats:
        prepared_stats = [((event.get("payload") or {}).get("stats") or {})
                          for event in events if event.get("event_type") == "context.prepared"]
    peak_context = None
    if prepared_stats:
        peak = max(prepared_stats, key=lambda s: (s.get("admission_input_tokens") or 0))
        peak_context = {"admission_input_tokens": peak.get("admission_input_tokens"),
                        "serialized_bytes": peak.get("serialized_bytes"),
                        "reserved_output_tokens": peak.get("reserved_output_tokens"),
                        "step": peak.get("step"), "overflow": peak.get("overflow", False)}
    known_usage = [a.get("usage") or {} for a in attempts]
    usage_known = bool(known_usage) and all(type(u.get("prompt_tokens")) is int and
                                            type(u.get("completion_tokens")) is int for u in known_usage)
    changed_paths = list((evaluation or {}).get("changed_paths") or [])
    cases = (evaluation or {}).get("cases") or []
    # Fixed two-test B0 gate: the defect test and the first regression test.
    acceptance_nodeids = tuple(spec.expected_nodeids[:2])
    acceptance_cases = [c for c in cases if c.get("nodeid") in acceptance_nodeids]
    acceptance = {
        "required_test_nodeids": list(acceptance_nodeids),
        "results": [{"nodeid": c.get("nodeid"), "outcome": c.get("outcome"),
                      "satisfied": c.get("satisfied")} for c in acceptance_cases],
        "all_required_passed": bool(acceptance_cases) and all(c.get("satisfied") is True for c in acceptance_cases),
    }
    grader_status = (evaluation or {}).get("status")
    lifecycle_failure = run_error or result_plain.get("failure_reason")
    if lifecycle_failure is None and grader_status not in (None, "pass"):
        lifecycle_failure = "grader_" + str(grader_status)
    receipt = {"schema": "a5.pilot-run-receipt.v2", "protocol_version": PROFILE_VERSION,
               "profile": PROFILE, "assignment_id": row["assignment_id"],
               "experiment_id": row["experiment_id"], "canonical_target_id": row["canonical_target_id"],
               "agent_task_id": row["agent_task_id"], "variant": row["variant"], "repeat_id": row["repeat_id"],
               "seed": row["organization_seed"], "public_task_hash": row["public_task_hash"],
               "target_base_hash": row.get("target_base_hash", "98c55d8f72e86fd1a54c12ee6c0dab8511821337902eeb28fa4f454dea783060"), "memory_snapshot_hash": sha_file(SNAPSHOT),
               "injection_receipt_refs": injections, "injection_decision": "selected" if injections else "no_relevant_memory",
               "model_binding_hash": sha_bytes(b"deepseek-flash@DeepSeek-V4.1-Flash"),
               "harness_fingerprint": sha_bytes(b"coding-harness"), "agent_fingerprint": approved,
               "operation_id": operation_id,
               "attempt_ids": attempt_ids,
               "usage": ({"prompt_tokens": sum(u["prompt_tokens"] for u in known_usage),
                          "completion_tokens": sum(u["completion_tokens"] for u in known_usage)}
                         if usage_known else {"unknown": True}),
               "reservation": {"reserved_cny": str(ledger.cost_committed - run_cost_before),
                               "calls": ledger.calls_started - run_calls_before},
               "settlement": {"status": "provider_usage" if usage_known else "unknown_keeps_reserve"},
               "candidate_hash": tree_hash(candidate) if candidate else None,
               "grader_receipt_ref": sha_bytes(json.dumps(plain(evaluation), sort_keys=True).encode()),
               "changed_paths": changed_paths,
               "changed_file_count": len(changed_paths),
               "acceptance": acceptance,
               "peak_context": peak_context,
               "cleanup_verified": bool(backend.cleanup_ok),
               "status": "completed" if result_plain.get("success") is True and grader_status == "pass" else "failed",
               "failure_reason": lifecycle_failure, "created_at": utc_now(), "finished_at": utc_now(),
               "ledger": ledger.snapshot()}
    (output / "receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    return receipt


def load_events(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=4)
    parser.add_argument("--ledger", type=Path, default=None,
                        help="persistent ledger path; historical v6/v7 spend is imported")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    base, spec = base_and_overlay()
    ledger = make_ledger(args.ledger or (args.output / "ledger.json"))
    rows = assignments()[:args.limit]
    results = []
    for row in rows:
        if row["canonical_target_id"] == "django__django-13265":
            continue
        if ledger.cost_committed >= ledger.plan.total_cny:
            break
        results.append(await run_one(row, args.output / row["variant"], ledger, base, spec))
    (args.output / "scope.json").write_text(json.dumps({"schema": "a5.canary-scope.v2", "runs": len(results),
        "requested": args.limit, "unrun_matrix_rows": 236, "ledger": ledger.snapshot()}, indent=2), encoding="utf-8")
    print(json.dumps({"runs": len(results), "ledger": ledger.snapshot()}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
