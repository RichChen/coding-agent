#!/usr/bin/env python3
"""Run B0 on SWE-bench tasks listed in a dev manifest.

Gold patches, test patches, and FAIL_TO_PASS / PASS_TO_PASS stay on the host
grader path. They are not copied into the agent workspace or the prompt.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import json
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.eval.grader import tree_hash
from src.eval.image_grader import ImageGrader
from src.eval.repo_grader import RepositoryGrader, RepositorySpec
from src.execution.baseline_image_backend import BaselineImageBackend
from src.execution.docker import MAX_FILES
from src.harness.factory import build_agent, load_config
from src.llm.client import LLMClient, LLMResponse, LLMStreamEvent, StreamCapability
from src.policy.cny_budget import A5BudgetPlan, CnyBudgetLedger, PriceSnapshot
from src.runtime.session import RunSession, compatibility, plain

# Pilot targets from coding-agent assignments.json. Never tune on these.
HOLDOUT = {
    "pytest-dev__pytest-9359",
    "pytest-dev__pytest-7432",
    "pytest-dev__pytest-8365",
    "pytest-dev__pytest-7220",
    "scikit-learn__scikit-learn-25747",
    "scikit-learn__scikit-learn-25500",
    "scikit-learn__scikit-learn-25570",
    "scikit-learn__scikit-learn-25638",
    "sphinx-doc__sphinx-8595",
    "sphinx-doc__sphinx-8713",
    "sphinx-doc__sphinx-10451",
    "sphinx-doc__sphinx-8721",
    "sympy__sympy-20442",
    "sympy__sympy-20154",
    "sympy__sympy-24152",
    "sympy__sympy-18532",
    "django__django-15781",
    "django__django-13265",
    "django__django-13448",
    "django__django-13590",
}
class _MockLLM(LLMClient):
    def __init__(self):
        self.model = "mock-model"
        self.supports_streaming = False
        self._owns_http_client = False
        self._http = None
        self._closed = False

    async def chat(self, messages, tools=None):
        return LLMResponse(
            text="mock finish without edits",
            finish_reason="stop",
            usage={"prompt_tokens": 0, "completion_tokens": 0, "provenance": "unknown"},
        )

    async def stream_chat(self, messages, tools=None):
        response = await self.chat(messages, tools)
        yield LLMStreamEvent(
            "llm_stream_done",
            {
                "finish_reason": "stop",
                "usage": response.usage,
                "has_tool_calls": False,
                "capability": StreamCapability.NON_STREAMING.value,
                "response": response,
            },
        )

    async def aclose(self):
        self._closed = True


EDIT_TOOLS = {"edit_file", "search_replace", "write_file"}
PYTHON_PATHS = {
    "django": (".",),
    "pytest-dev": ("src",),
    "scikit-learn": (".",),
    "sympy": (".",),
}


def load_yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def git_state(repo: Path) -> dict:
    def run(*args):
        return subprocess.run(
            ["git", *args], cwd=repo, capture_output=True, text=True, check=False
        )

    head = run("rev-parse", "HEAD")
    dirty = run("status", "--porcelain")
    return {
        "path": str(repo),
        "head": head.stdout.strip() if head.returncode == 0 else None,
        "dirty": bool(dirty.stdout.strip()) if dirty.returncode == 0 else None,
    }


def read_tree(root: Path) -> dict[str, bytes]:
    files = {}
    for path in root.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        relative = path.relative_to(root).as_posix()
        if ".git" in relative.split("/"):
            continue
        files[relative] = path.read_bytes()
    return files


def usable_nodeid(node: str) -> bool:
    if not isinstance(node, str) or not node or node.startswith(("[", "-")):
        return False
    return "\n" not in node and "\x00" not in node


def parse_id_list(value) -> list[str]:
    if isinstance(value, str):
        return list(json.loads(value))
    return list(value or [])


def prefix_sympy_nodeids(nodes: list[str], test_paths) -> list[str]:
    test_file = next((path for path in test_paths if "/tests/" in path and str(path).endswith(".py")), None)
    if not test_file:
        return list(nodes)
    prefixed = []
    for node in nodes:
        prefixed.append(node if "::" in node or node.endswith(".py") else f"{test_file}::{node}")
    return prefixed


def django_nodeids(raw: list[str]) -> list[str]:
    converted = []
    for node in raw:
        if " (" in node and node.endswith(")"):
            name, rest = node.split(" ", 1)
            converted.append(rest.strip("()") + "." + name)
        else:
            converted.append(node)
    return converted


def public_issue(task: dict) -> str:
    public = load_json(Path(task["public_task"]))
    issue = public.get("issue_text") or ""
    if public.get("gold_patch") or public.get("test_patch") or public.get("FAIL_TO_PASS"):
        raise ValueError("public task embeds private grader fields")
    repo = (public.get("repo_ref") or {}).get("repo_id", task.get("repo", ""))
    revision = (public.get("repo_ref") or {}).get("revision", "")
    if task.get("family") == "django":
        test_command = "python tests/runtests.py <module>"
    else:
        test_command = "python -m pytest <test path>"
    return (
        "You are repairing an open-source repository from a public issue only.\n"
        f"Repository: {repo}\nBase revision: {revision}\n"
        "The source tree is mounted in the workspace. Dependencies are already installed. "
        "There is no network. Do not pip install. "
        f"Run tests from the repository root with `{test_command}`.\n"
        "Inspect the tree, reproduce the bug, edit the source, and stop when you believe the fix is in place.\n\n"
        f"Public issue:\n{issue}"
    )


def grader_spec(task: dict, base: dict[str, bytes] | None = None) -> RepositorySpec:
    receipt = load_json(ROOT / task["receipt"])
    binding = receipt["private_source_binding"]
    private = load_json(Path(binding["path"]))
    if private.get("instance_id") != task["id"]:
        raise ValueError("private source row does not match the task id")
    family = task["family"]
    f2p = parse_id_list(private.get("FAIL_TO_PASS"))
    p2p = parse_id_list(private.get("PASS_TO_PASS"))
    if family == "django":
        f2p = django_nodeids(f2p)
        p2p = django_nodeids(p2p)
    test_paths = tuple(binding.get("test_patch_paths") or [])
    if family == "sympy":
        f2p = prefix_sympy_nodeids(f2p, test_paths)
        p2p = prefix_sympy_nodeids(p2p, test_paths)
    f2p = [node for node in f2p if usable_nodeid(node)]
    p2p = [node for node in p2p if usable_nodeid(node)]
    excluded = set(task.get("p2p_excluded") or [])
    if excluded:
        p2p = [node for node in p2p if node not in excluded]
    editable = tuple(binding.get("gold_patch_paths") or [])
    baseline_root = ROOT / task["baseline"]
    original_root = ROOT / task["original"]
    overlay = {}
    for relative in test_paths:
        candidate_path = baseline_root / relative
        if not candidate_path.is_file():
            continue
        updated = candidate_path.read_bytes()
        original = None if base is None else base.get(relative)
        if original is None:
            original_path = original_root / relative
            original = original_path.read_bytes() if original_path.is_file() else b""
        if updated != original:
            overlay[relative] = base64.b64encode(updated).decode("ascii")
    return RepositorySpec(
        task_id=task["id"],
        base_hash=hashlib.sha256(task["id"].encode()).hexdigest(),
        image=receipt["baseline_image_digest"],
        editable_paths=editable,
        test_paths=test_paths,
        python_paths=PYTHON_PATHS[family],
        expected_nodeids=tuple(f2p + p2p),
        test_overlay=overlay,
        baseline_passed=tuple(p2p),
        timeout_seconds=float(task.get("grader_timeout_seconds", 300)),
    )


def apply_delta(base: dict[str, bytes], delta: dict | None) -> dict[str, bytes]:
    candidate = dict(base)
    if not delta:
        return candidate
    for name in delta.get("deleted") or []:
        candidate.pop(name, None)
    for name, change in (delta.get("changed") or {}).items():
        candidate[name] = base64.b64decode(change["content"])
    return candidate


class _NodeidGrader(RepositoryGrader):
    """Run the declared node ids. test_paths stays a file prefix for the overlay check."""

    def __init__(self, nodeids: tuple[str, ...]):
        super().__init__(context="desktop-linux")
        self._nodeids = list(nodeids)

    async def execute(self, files, **kwargs):
        kwargs["selectors"] = self._nodeids
        return await super().execute(files, **kwargs)


def solved(evaluation: dict) -> bool:
    cases = evaluation.get("cases") or []
    if not cases or evaluation.get("status") != "pass":
        return False
    f2p_failed = evaluation.get("failed") or 0
    assigned = evaluation.get("regression_assigned")
    passed = evaluation.get("regression_passed")
    regression_ok = assigned in (None, 0) or passed == assigned
    return f2p_failed == 0 and regression_ok and all(case.get("satisfied") is True for case in cases)


def _event_tool_name(event: dict) -> str:
    payload = event.get("payload") or {}
    return str(payload.get("name") or payload.get("tool") or "")


def summarize_events(events: list[dict], result_plain: dict | None, run_error: str | None) -> dict:
    """Count tool.intent events. Edit round is the model.started count before the first edit."""
    tool_calls = 0
    model_rounds = 0
    first_edit = None
    saw_edit = False
    for event in events:
        kind = event.get("event_type")
        if kind == "model.started":
            model_rounds += 1
        elif kind == "tool.intent":
            tool_calls += 1
            if _event_tool_name(event) in EDIT_TOOLS:
                saw_edit = True
                if first_edit is None:
                    first_edit = model_rounds
    return {
        "tool_calls": tool_calls,
        "first_edit_step": first_edit,
        "saw_edit": saw_edit,
        "stop_reason": _stop_reason(events, result_plain or {}, run_error),
    }


def _stop_reason(events: list[dict], result_plain: dict, run_error: str | None) -> str:
    if run_error:
        return run_error
    finished = None
    for event in events:
        if event.get("event_type") == "run.finished":
            finished = event.get("payload") or {}
    source = finished if finished is not None else result_plain
    reason = source.get("failure_reason") or source.get("stop_reason")
    if reason and str(reason).lower() not in {"none", "null"}:
        return str(reason)
    if source:
        raw = {key: source.get(key) for key in ("failure_reason", "stop_reason", "success", "termination_kind")}
        return "unknown: " + json.dumps(raw, default=str)
    return "unknown"


def delta_changes(delta: dict | None) -> list[str]:
    if not delta:
        return []
    names = list((delta.get("changed") or {}).keys())
    names.extend(delta.get("deleted") or [])
    return sorted(names)


def delta_lost(events_summary: dict, delta: dict | None) -> bool:
    return bool(events_summary.get("saw_edit")) and not delta_changes(delta)


def make_ledger(state_path: Path) -> CnyBudgetLedger:
    price = PriceSnapshot(
        provider="DeepSeek",
        model="deepseek-flash",
        snapshot_id="deepseek-flash@DeepSeek-V4.1-Flash",
        currency="CNY",
        prompt_cache_hit_per_million=Decimal("0.040"),
        prompt_cache_miss_per_million=Decimal("2.000"),
        completion_per_million=Decimal("8.000"),
        source_url="https://api-docs.deepseek.com/quick_start/pricing",
        retrieved_on="2026-09-21",
        verified=True,
    )
    # One run stays inside the sprint cap of 1 CNY. USD budget is not used.
    plan = A5BudgetPlan(
        total_cny=Decimal("1.000"),
        build_cny=Decimal("0.000"),
        pilot_cny=Decimal("1.000"),
        reserve_cny=Decimal("0.000"),
        build_calls=0,
        pilot_calls=40,
    )
    return CnyBudgetLedger(price, plan, state_path=state_path)


def select_tasks(manifest: dict, requested: list[str]) -> list[dict]:
    tasks = manifest["tasks"]
    if requested:
        wanted = set(requested)
        tasks = [task for task in tasks if task["id"] in wanted]
        missing = wanted - {task["id"] for task in tasks}
        if missing:
            raise SystemExit("unknown task id: " + ", ".join(sorted(missing)))
    blocked = [task["id"] for task in tasks if task["id"] in HOLDOUT]
    if blocked:
        raise SystemExit("hold-out task refused: " + ", ".join(blocked))
    return tasks


async def run_task(task: dict, profile: Path, output: Path, *, mock: bool) -> dict:
    if task["id"] in HOLDOUT:
        raise SystemExit("hold-out task refused: " + task["id"])
    output.mkdir(parents=True, exist_ok=True)
    workspace = output / "workspace"
    workspace.mkdir()
    spec = grader_spec(task)
    receipt = load_json(ROOT / task["receipt"])
    backend = BaselineImageBackend(
        image=receipt["baseline_image_digest"],
        context="desktop-linux",
        memory_bytes=1024**3,
        workspace_bytes=256 * 1024**2,
        tmpfs_bytes=64 * 1024**2,
        network="none",
    )
    config = load_config(profile)
    # CNY ledger is the only budget that stops a run. Do not set max_cost_usd here.
    if mock:
        config["llm"]["api_key"] = config["llm"]["api_key"] or "mock"
    prompt = public_issue(task)
    agent = build_agent(config, workspace, execution_backend=backend)
    if mock:
        agent.llm = _MockLLM()
    ledger = make_ledger(output / "cny-ledger.json")
    before = ledger.cost_committed
    agent.retry.cny_ledger = ledger
    expected = compatibility(
        workspace=workspace,
        code_id="sprint-b0",
        config={"profile": str(profile)},
        backend=backend.capabilities,
    )
    run_error = None
    result = None
    try:
        with RunSession.create(output / "session", task_id=task["id"], expected=expected, timeout_seconds=config["runtime"]["total_timeout_seconds"]) as session:
            result = await session.run(agent, prompt)
            session.store.export_jsonl(output / "events.jsonl")
    except Exception as exc:
        run_error = type(exc).__name__
    finally:
        close = getattr(agent.llm, "aclose", None)
        if close is not None:
            await close()
    delta = backend.candidate_delta
    snapshot_error = getattr(backend, "snapshot_error", None)
    if delta is not None:
        (output / "candidate-delta.json").write_text(json.dumps(delta, indent=2), encoding="utf-8")
    f2p = [node for node in spec.expected_nodeids if node not in spec.baseline_passed]
    evaluation = await ImageGrader().evaluate(
        image=receipt["baseline_image_digest"],
        delta=delta,
        test_overlay=spec.test_overlay,
        f2p=f2p,
        p2p=list(spec.baseline_passed),
        django=task.get("family") == "django",
        sympy=False,
        timeout=float(task.get("grader_timeout_seconds", 300)),
    )
    # Drop nothing the grader needs, but do not copy this file into the workspace.
    (output / "grader-result.json").write_text(
        json.dumps(evaluation, indent=2, default=str), encoding="utf-8"
    )
    events = []
    events_path = output / "events.jsonl"
    if events_path.exists():
        events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    result_plain = plain(result) if result else {}
    attempts = result_plain.get("llm_attempts") or []
    stats = summarize_events(events, result_plain, run_error)
    changed = delta_changes(delta) or list(evaluation.get("changed_paths") or [])
    lost = delta_lost(stats, delta)
    if lost:
        print(f"DELTA_LOST {task['id']}: edit tools ran but the collected delta is empty. snapshot_error={snapshot_error}", flush=True)
    summary = {
        "task_id": task["id"],
        "variant": "B0",
        "solved": False if lost else bool(evaluation.get("solved")),
        "status": "delta_lost" if lost else evaluation.get("status"),
        "grader_status": evaluation.get("status"),
        "changed_files": changed,
        "first_edit_step": stats["first_edit_step"],
        "model_calls": len(attempts),
        "tool_calls": stats["tool_calls"],
        "peak_context": _peak_context(result_plain, events),
        "cost_cny": str(ledger.cost_committed - before),
        "stop_reason": stats["stop_reason"],
        "snapshot_error": snapshot_error,
        "git": {
            "coding-harness": git_state(ROOT),
            "coding-agent": git_state(ROOT.parent / "coding-agent"),
        },
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def _peak_context(result_plain: dict, events: list[dict]):
    stats = list(result_plain.get("context_events") or [])
    if not stats:
        stats = [((event.get("payload") or {}).get("stats") or {}) for event in events if event.get("event_type") == "context.prepared"]
    if not stats:
        return None
    peak = max(stats, key=lambda item: item.get("admission_input_tokens") or 0)
    return {
        "admission_input_tokens": peak.get("admission_input_tokens"),
        "step": peak.get("step"),
    }


def _score_cases(evaluation: dict, spec: RepositorySpec) -> dict:
    f2p = [node for node in spec.expected_nodeids if node not in spec.baseline_passed]
    by_id = {case.get("nodeid"): case for case in evaluation.get("cases") or []}
    return {
        "f2p_passed": sum(1 for node in f2p if (by_id.get(node) or {}).get("outcome") == "passed"),
        "f2p_total": len(f2p),
        "p2p_passed": int(evaluation.get("regression_passed") or 0),
        "p2p_total": len(spec.baseline_passed),
    }


def _memory_task(source_id: str, manifest: dict) -> dict | None:
    for task in manifest["tasks"]:
        if task["id"] == source_id:
            return task
    roots = [
        ROOT / "docs/upgrade/evidence/A5-harness-preflight-62-history-baseline-retry/tasks",
        ROOT / "docs/upgrade/evidence/A5-harness-preflight-57-remaining16-baseline/tasks",
    ]
    receipt = next((root / source_id / "receipt.json" for root in roots if (root / source_id / "receipt.json").exists()), None)
    if receipt is None:
        return None
    public = {}
    for path in (ROOT / "docs/upgrade/evidence").glob("A5-memory-pool-*/**/public-input.json"):
        data = load_json(path)
        if data.get("source_id") == source_id:
            public = data
            break
    repo = load_json(receipt).get("repo", "")
    family = repo.split("/")[0]
    base = receipt.parent
    return {
        "id": source_id,
        "repo": repo,
        "family": family,
        "receipt": str(receipt.relative_to(ROOT)).replace("\\", "/"),
        "original": str((base / "staging/original").relative_to(ROOT)).replace("\\", "/"),
        "baseline": str((base / "staging/baseline").relative_to(ROOT)).replace("\\", "/"),
        "public_task": public.get("public_task_path", ""),
        "transport_manifest": public.get("typed_tree_manifest_ref", ""),
    }


async def verify_memory(manifest: dict, destination: Path) -> list[dict]:
    snapshot = ROOT / "docs/upgrade/evidence/A5-real240-77-harness-preflight/memory-snapshot.jsonl"
    rows = []
    for line in snapshot.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        source_id = record["source_id"]
        task = _memory_task(source_id, manifest)
        delta_path = Path(record["source_dir"]) / "candidate-delta.json"
        if task is None or not delta_path.is_file():
            rows.append({"source_id": source_id, "status": "grader_unavailable", "f2p_passed": 0, "f2p_total": 0, "p2p_passed": 0, "p2p_total": 0})
            continue
        base = read_tree(ROOT / task["original"])
        if len(base) > MAX_FILES:
            rows.append({"source_id": source_id, "status": "grader_unavailable", "reason": "file_cap", "f2p_passed": 0, "f2p_total": 0, "p2p_passed": 0, "p2p_total": 0})
            print(json.dumps(rows[-1]), flush=True)
            continue
        try:
            spec = grader_spec(task, base)
            delta = load_json(delta_path)
            evaluation = await _NodeidGrader(spec.expected_nodeids).evaluate(base, apply_delta(base, delta), spec)
        except ValueError as exc:
            rows.append({"source_id": source_id, "status": "grader_unavailable", "reason": str(exc)[:200], "f2p_passed": 0, "f2p_total": 0, "p2p_passed": 0, "p2p_total": 0})
            print(json.dumps(rows[-1]), flush=True)
            continue
        counts = _score_cases(evaluation, spec)
        status = evaluation.get("status")
        if status == "pass" and solved(evaluation):
            label = "pass"
        elif status in ("partial", "fail"):
            label = status
        else:
            label = "grader_unavailable"
        rows.append({"source_id": source_id, "status": label, **counts})
        print(json.dumps(rows[-1]), flush=True)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks", default="configs/sprint/dev-tasks.yaml")
    parser.add_argument("--task", action="append", default=[])
    parser.add_argument("--profile", default="configs/sprint/b0.yaml")
    parser.add_argument("--variant", default="B0")
    parser.add_argument("--output", default="runs/sprint")
    parser.add_argument("--mock", action="store_true", help="zero-model finish, still grades in Docker")
    parser.add_argument("--verify-memory", action="store_true")
    args = parser.parse_args()
    if args.variant != "B0":
        raise SystemExit("only B0 is supported in this sprint")
    manifest = load_yaml(ROOT / args.tasks)
    if args.verify_memory:
        asyncio.run(verify_memory(manifest, ROOT / "docs/sprint/memory-source-verification.json"))
        return
    selected = select_tasks(manifest, args.task)
    out_root = Path(args.output)
    if not out_root.is_absolute():
        out_root = ROOT / out_root

    async def _go():
        summaries = []
        for task in selected:
            summaries.append(await run_task(task, ROOT / args.profile, out_root / task["id"], mock=args.mock))
        print(json.dumps(summaries, indent=2))

    asyncio.run(_go())


if __name__ == "__main__":
    main()
