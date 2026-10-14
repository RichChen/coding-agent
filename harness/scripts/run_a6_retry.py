"""Run A6-R: second attempts at the 53 failed A5 B0 runs.

R0 repeats the A5 B0 prompt. R1 appends the frozen previous-attempt record from docs/sprint/a6-attempts.json.
318 slots runs/a6-retry/<task>/<arm>/<first>/r<k> share one queue, shuffled with seed 20261013 after a sort on
(task, arm, first, k). Stop conditions are A6-R-PLAN section 1. run_a5_main.py is reused, not changed.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import random
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import build_a6_attempts as attempts_lib  # noqa: E402
from scripts.handoff_sha import handoff_sha256  # noqa: E402
from scripts.run_a5_main import (  # noqa: E402
    PARALLEL,
    PROFILE,
    _display_path,
    accepted_tasks,
    load_targets,
    materialize_runner_task,
    retire_infra,
    run_checks,
    spent,
)
from scripts.run_a5_main import preflight as pool_preflight  # noqa: E402
from scripts.run_swe_task import build_prompt, run_task  # noqa: E402

ATTEMPTS = attempts_lib.MANIFEST
A5_ROOT = attempts_lib.A5_ROOT
CLEAN_IMAGES = ROOT / "docs" / "sprint" / "clean-images"
LOGS = ROOT / "runs" / "a6-retry-logs"
TOTAL_CAP = Decimal("210")
SEED = 20261013
ARMS = ("r0", "r1")
REPEATS = (1, 2, 3)
EXPECTED_SLOTS = attempts_lib.EXPECTED_ATTEMPTS * len(ARMS) * len(REPEATS)
RUNS_SCHEMA = "a6.retry-runs.v1"
A5_FIRST_REPEATS = attempts_lib.FIRST_REPEATS


def out_root_for(mock: bool) -> Path:
    return ROOT / "runs" / ("a6-retry-mock" if mock else "a6-retry")


def runs_path_for(mock: bool) -> Path:
    return ROOT / "docs" / "sprint" / ("a6-retry-runs.mock.json" if mock else "a6-retry-runs.json")


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# --- frozen records and slots --------------------------------------------------------------------

def load_attempts(path: Path = ATTEMPTS, expected=(attempts_lib.EXPECTED_ATTEMPTS, attempts_lib.EXPECTED_TASKS)) -> tuple[dict, str]:
    """The record manifest and its handoff_sha256. Refuses a manifest the current template did not render."""
    if not path.is_file():
        raise SystemExit("record manifest missing: " + _display_path(path))
    manifest = json.loads(path.read_text(encoding="utf-8"))
    records = manifest.get("records") or []
    keys = [(row.get("task"), row.get("first")) for row in records]
    problems = [name for name, bad in (
        ("schema", manifest.get("schema") != attempts_lib.SCHEMA),
        ("template_sha256", manifest.get("template_sha256") != attempts_lib.template_sha256()),
        ("record count", manifest.get("attempts") != len(records) or len(set(keys)) != len(keys)),
        ("recount", expected is not None and (len(records), len({task for task, _ in keys})) != tuple(expected)),
    ) if bad]
    if problems:
        raise SystemExit("record manifest " + _display_path(path) + " fails: " + ", ".join(problems))
    return manifest, handoff_sha256(path)


def retry_for(row: dict, arm: str) -> dict:
    return {"arm": arm, "first": row["first"], "attempt_sha256": row["sha256"] if arm == "r1" else None}


def all_slots(records: list[dict]) -> list[tuple[str, str, str, int]]:
    return sorted((row["task"], arm, row["first"], k) for row in records for arm in ARMS for k in REPEATS)


def slot_queue(records: list[dict]) -> list[tuple[str, str, str, int]]:
    slots = all_slots(records)
    random.Random(SEED).shuffle(slots)
    return slots


def canary_slots(queue) -> list[tuple[str, str, str, int]]:
    """The first and second R0 and R1 slots of the queue, in queue order."""
    seen = {arm: 0 for arm in ARMS}
    chosen = []
    for slot in queue:
        if seen[slot[1]] < 2:
            seen[slot[1]] += 1
            chosen.append(slot)
    return chosen


def mock_slots(queue, repo_of: dict) -> list[tuple[str, str, str, int]]:
    """Two R0 and two R1 slots in queue order, each from a repo not taken yet."""
    seen = {arm: 0 for arm in ARMS}
    repos, chosen = set(), []
    for slot in queue:
        repo = repo_of[slot[0]]
        if seen[slot[1]] < 2 and repo not in repos:
            seen[slot[1]] += 1
            repos.add(repo)
            chosen.append(slot)
    return chosen


def parse_slot(text: str) -> tuple[str, str, str, int]:
    parts = text.split("/")
    if len(parts) != 4 or parts[1] not in ARMS or not parts[3].startswith("r") or not parts[3][1:].isdigit():
        raise SystemExit("slot must look like <task>/<r0|r1>/b0r<k>/r<k>: " + text)
    return parts[0], parts[1], parts[2], int(parts[3][1:])


def slot_dir(out_root: Path, slot) -> Path:
    task, arm, first, k = slot
    return out_root / task / arm / first / ("r" + str(k))


def expected_prompts(manifest: dict, prepared: dict, record_root: Path = ROOT) -> dict:
    """(task, first, arm) -> the exact first user message, its sha256, the prompt suffix and the retry field.

    R0 must render to the A5 B0 prompt_sha256. R1 is that prompt, one blank line, and the record read back
    against its manifest sha256.
    """
    expected = {}
    for row in manifest["records"]:
        task = prepared[row["task"]]
        base = build_prompt(task)
        if _sha(base) != row["a5_prompt_sha256"]:
            raise SystemExit("R0 prompt for " + row["task"] + " differs from the A5 B0 prompt_sha256")
        record = attempts_lib.load_record(row, record_root)
        with_record = build_prompt(task, record)
        if with_record != base + "\n\n" + record:
            raise SystemExit("R1 prompt for " + row["task"] + " " + row["first"] + " is not the A5 prompt plus the record")
        for arm, suffix, text in (("r0", None, base), ("r1", record, with_record)):
            expected[(row["task"], row["first"], arm)] = {
                "suffix": suffix, "text": text, "sha256": _sha(text), "retry": retry_for(row, arm),
            }
    return expected


# --- stop conditions -----------------------------------------------------------------------------

def resumable(summary: dict, retry: dict, *, mock: bool) -> str | None:
    """Why an existing summary cannot count for this slot, or None."""
    if "mock" not in summary or "profile" not in summary:
        return "summary has no mock/profile field"
    if bool(summary["mock"]) != mock:
        return "summary is a mock run" if summary["mock"] else "summary is a real run"
    if summary["profile"] != PROFILE.stem:
        return "profile is " + str(summary["profile"])
    if summary.get("variant") != "B0":
        return "variant is " + str(summary.get("variant"))
    if summary.get("status") != "answer_isolation_failed" and summary.get("retry") != retry:
        return "retry is " + json.dumps(summary.get("retry")) + ", expected " + json.dumps(retry)
    return None


def slot_summaries(out_root: Path) -> list[tuple[Path, dict]]:
    """Every attempt in the root, including retired r<k>.infra<n> runs."""
    if not out_root.exists():
        return []
    rows = []
    for arm in ARMS:
        for path in sorted(out_root.glob("*/" + arm + "/b0r*/r*/summary.json")):
            rows.append((path, json.loads(path.read_text(encoding="utf-8"))))
    return rows


def first_user_message(run_dir: Path) -> str | None:
    """The first user message the run recorded, reading artifact-stored payloads back. None when unreadable."""
    events = run_dir / "events.jsonl"
    if not events.is_file():
        return None
    try:
        with events.open(encoding="utf-8") as handle:
            for line in handle:
                if '"state.saved"' not in line:
                    continue
                event = json.loads(line)
                if event.get("event_type") != "state.saved":
                    continue
                payload = attempts_lib._payload(run_dir, event.get("payload") or {})
                for message in payload.get("messages") or []:
                    if message.get("role") == "user":
                        content = message.get("content")
                        return content if isinstance(content, str) else None
    except (ValueError, KeyError, TypeError):
        return None
    return None


def injection_problem(run_dir: Path, summary: dict, expected: dict) -> str | None:
    if summary.get("retry") != expected["retry"]:
        return "retry field " + json.dumps(summary.get("retry")) + " differs from " + json.dumps(expected["retry"])
    if summary.get("prompt_sha256") != expected["sha256"]:
        return "prompt_sha256 differs from the expected prompt"
    message = first_user_message(run_dir)
    if message is None:
        return "first user message cannot be read from events.jsonl"
    if message != expected["text"]:
        return "first user message differs from the expected prompt"
    return None


def halt_reason(out_root: Path, expected: dict, verified: set | None = None, cap: Decimal = TOTAL_CAP) -> str | None:
    """Stop conditions checked before every new run. In-flight runs still finish."""
    verified = set() if verified is None else verified
    rows = slot_summaries(out_root)
    reason = run_checks([summary for _, summary in rows])
    if reason:
        return reason
    for path, summary in rows:
        run_dir = path.parent
        if "." in run_dir.name or run_dir in verified or summary.get("status") == "infra_error":
            continue
        task, arm, first = run_dir.parent.parent.parent.name, run_dir.parent.parent.name, run_dir.parent.name
        slot = expected.get((task, first, arm))
        label = task + "/" + arm + "/" + first + "/" + run_dir.name
        if slot is None:
            return "run outside the frozen records: " + label
        problem = injection_problem(run_dir, summary, slot)
        if problem:
            return "injection check failed: " + label + ": " + problem
        verified.add(run_dir)
    identities = set()
    for _, summary in rows:
        model = summary.get("model") or {}
        if model.get("changed_to"):
            return "model changed during a run: " + str(summary.get("task_id"))
        if model:
            identities.add((model.get("name"), model.get("base_url_host")))
    if len(identities) > 1:
        return "model name or base_url host differs between runs: " + json.dumps(sorted(identities, key=str))
    cost = spent(out_root)
    if cost >= cap:
        return "spend " + str(cost) + " CNY reached the cap " + str(cap)
    return None


# --- running -------------------------------------------------------------------------------------

async def run_slots(slots, *, mock: bool, out_root: Path, manifest: dict, expected: dict, prepared: dict,
                    attempts_sha256: str, label: str, record_root: Path = ROOT) -> dict:
    rows = {(row["task"], row["first"]): row for row in manifest["records"]}
    verified = set()
    pending, refused, kept_infra = [], [], []
    for slot in slots:
        task, arm, first, _ = slot
        output = slot_dir(out_root, slot)
        summary_path = output / "summary.json"
        if summary_path.is_file():
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            problem = resumable(summary, expected[(task, first, arm)]["retry"], mock=mock)
            if problem:
                refused.append(_display_path(summary_path) + ": " + problem)
                continue
            if summary.get("status") != "infra_error":
                continue
            if not retire_infra(output):
                kept_infra.append(_display_path(output))
                continue
        elif output.exists():
            refused.append(_display_path(output) + ": directory has no summary.json (an interrupted run)")
            continue
        pending.append((slot, output))
    if refused:
        raise SystemExit("existing summaries do not belong to these slots; not overwriting:\n" + "\n".join(refused))
    state = {"halt": halt_reason(out_root, expected, verified)}
    semaphore = asyncio.Semaphore(PARALLEL)

    async def one(slot, output):
        task, arm, first, _ = slot
        want = expected[(task, first, arm)]
        async with semaphore:
            while True:
                if state["halt"]:
                    return None
                try:
                    suffix = None
                    if arm == "r1":
                        suffix = attempts_lib.load_record(rows[(task, first)], record_root)
                        if suffix != want["suffix"]:
                            raise SystemExit("record " + task + " " + first + " changed after the runner started")
                    output.mkdir(parents=True, exist_ok=True)
                    summary = await run_task(prepared[task], PROFILE, output, mock=mock, variant="B0",
                                             prompt_suffix=suffix, retry=want["retry"])
                except (Exception, SystemExit) as exc:
                    state["halt"] = state["halt"] or ("run crashed: " + "/".join(map(str, slot)) + " "
                                                      + type(exc).__name__ + ": " + str(exc)[:300])
                    return None
                state["halt"] = state["halt"] or halt_reason(out_root, expected, verified)
                if summary.get("status") != "infra_error":
                    return summary
                if state["halt"] or not retire_infra(output):
                    kept_infra.append(_display_path(output))
                    return summary

    results = await asyncio.gather(*(one(*item) for item in pending))
    retired = [path for arm in ARMS for path in out_root.glob("*/" + arm + "/b0r*/r*.infra*")]
    started = [(slot, row) for (slot, _), row in zip(pending, results) if row is not None]
    report = {
        "label": label,
        "mock": mock,
        "parallel": PARALLEL,
        "seed": SEED,
        "total_cap_cny": str(TOTAL_CAP),
        "attempts_sha256": attempts_sha256,
        "template_sha256": manifest["template_sha256"],
        "slots": ["/".join([task, arm, first, "r" + str(k)]) for task, arm, first, k in slots],
        "halt_reason": state["halt"],
        "started": len(started),
        "not_started": len(results) - len(started),
        "started_by_arm": {arm: sum(1 for slot, _ in started if slot[1] == arm) for arm in ARMS},
        "injection_verified_runs": len(verified),
        "infra_kept": sorted(set(kept_infra)),
        "infra_retired": sorted(_display_path(path) for path in retired),
        "spent_cny": str(spent(out_root)),
    }
    out_root.mkdir(parents=True, exist_ok=True)
    (out_root / (label + "-report.json")).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def write_runs(*, manifest: dict, attempts_sha256: str, repo_of: dict, mock: bool, out_root: Path | None = None,
               destination: Path | None = None) -> Path:
    """a6-retry-runs.json in the coding-agent A6-R-PREREG input format: one row per finished slot."""
    out_root = out_root or out_root_for(mock)
    rows = {(row["task"], row["first"]): row for row in manifest["records"]}
    runs = []
    for slot in all_slots(manifest["records"]):
        task, arm, first, k = slot
        run_dir = slot_dir(out_root, slot)
        path = run_dir / "summary.json"
        if not path.is_file():
            continue
        summary = json.loads(path.read_text(encoding="utf-8"))
        problem = resumable(summary, retry_for(rows[(task, first)], arm), mock=mock)
        if problem:
            raise SystemExit("refusing to hand off " + _display_path(path) + ": " + problem)
        runs.append({
            "task_id": task,
            "repo": repo_of[task],
            "arm": arm,
            "first": first,
            "k": k,
            "run_dir": _display_path(run_dir),
            "mock": summary["mock"],
            "status": summary.get("status"),
            "solved": summary.get("solved"),
            "model_calls": summary.get("model_calls"),
            "first_edit_step": summary.get("first_edit_step"),
            "cost_cny": summary.get("cost_cny"),
            "stop_reason": summary.get("stop_reason"),
            "changed_files": summary.get("changed_files"),
            "prompt_sha256": summary.get("prompt_sha256"),
            "retry": summary.get("retry"),
        })
    payload = {
        "schema": RUNS_SCHEMA,
        "scope": "mock" if mock else "a6-retry",
        "attempts_sha256": attempts_sha256,
        "slots_expected": len(all_slots(manifest["records"])),
        "runs": runs,
    }
    if mock:
        payload["note"] = "Zero-model mock runs. This is not the A6-R data."
    destination = destination or runs_path_for(mock)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print("runs", _display_path(destination), len(runs), handoff_sha256(destination), flush=True)
    return destination


# --- preflight -----------------------------------------------------------------------------------

def preflight(manifest: dict, tasks: list[dict], *, destination: Path | None = None, record_root: Path = ROOT) -> dict:
    """Every check before the first model call, on the 22 tasks and 53 records. No model calls.

    The pool checks are run_a5_main.preflight: answer isolation, source-only hash of /opt/repo (which runs the clean
    image, so the digest must exist locally), grader id counts against calibration, the prompt check, a tool smoke.
    """
    destination = destination or LOGS / "preflight.json"
    pool = pool_preflight(tasks, destination.with_name("preflight-pool.json"))
    pool_rows = {row["task_id"]: row for row in pool["tasks"]}
    rows = []
    for task in tasks:
        row = {"task_id": task["id"], "pool_pass": pool_rows[task["id"]]["pass"], "failure": pool_rows[task["id"]].get("failure")}
        try:
            clean = json.loads((CLEAN_IMAGES / (task["id"] + ".json")).read_text(encoding="utf-8"))
            a5 = {json.loads((A5_ROOT / task["id"] / "b0" / ("r" + str(k)) / "summary.json").read_text(encoding="utf-8")).get("clean_image_digest")
                  for k in A5_FIRST_REPEATS}
            row["clean_image_digest"] = clean.get("clean_image_digest")
            row["digest_matches_a5"] = a5 == {clean.get("clean_image_digest")} == {pool_rows[task["id"]].get("image")}
            if row["failure"] is None and not row["digest_matches_a5"]:
                row["failure"] = "clean image digest differs from the A5 B0 runs"
        except (Exception, SystemExit) as exc:
            row["failure"] = row["failure"] or type(exc).__name__ + ": " + str(exc)[:300]
        rows.append(row)
    prompts = {"r0_match_a5": 0, "r1_exact": 0, "failure": None}
    try:
        prepared = {task["id"]: materialize_runner_task(task) for task in tasks}
        expected = expected_prompts(manifest, prepared, record_root)
        prompts["r0_match_a5"] = sum(1 for key, item in expected.items() if key[2] == "r0")
        prompts["r1_exact"] = sum(1 for key, item in expected.items() if key[2] == "r1")
    except (Exception, SystemExit) as exc:
        prompts["failure"] = type(exc).__name__ + ": " + str(exc)[:300]
    records = {"checked": 0, "rendered_identical": 0, "failure": None}
    try:
        targets = {task["id"]: task for task in tasks}
        for row in manifest["records"]:
            text = attempts_lib.load_record(row, record_root)
            records["checked"] += 1
            original = attempts_lib.original_reader(attempts_lib.IMAGES_ROOT / targets[row["task"]]["id"] / "staging" / "original")
            run_dir = ROOT / row["run_dir"]
            summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
            if attempts_lib.render_record(run_dir, summary, original)["text"] == text:
                records["rendered_identical"] += 1
    except (Exception, SystemExit) as exc:
        records["failure"] = type(exc).__name__ + ": " + str(exc)[:300]
    queue = slot_queue(manifest["records"])
    report = {
        "passed": sum(1 for row in rows if row["failure"] is None),
        "total": len(rows),
        "pool": {key: pool[key] for key in ("passed", "total", "tool_smoke_passed", "prompt_passed")},
        "dev_prompts": {key: pool["dev_prompts"][key] for key in ("identical", "total")},
        "prompts": prompts,
        "records": records,
        "slots": len(queue),
        "canary": ["/".join([task, arm, first, "r" + str(k)]) for task, arm, first, k in canary_slots(queue)],
        "model_calls": 0,
        "tasks": rows,
    }
    report["pass"] = (report["passed"] == report["total"] == attempts_lib.EXPECTED_TASKS
                      and report["dev_prompts"]["identical"] == report["dev_prompts"]["total"]
                      and prompts["failure"] is None and prompts["r0_match_a5"] == prompts["r1_exact"] == len(manifest["records"])
                      and records["failure"] is None and records["rendered_identical"] == records["checked"] == len(manifest["records"])
                      and len(queue) == EXPECTED_SLOTS)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


# --- cli -----------------------------------------------------------------------------------------

def pool_tasks(manifest: dict) -> list[dict]:
    wanted = set(manifest["by_task"])
    tasks = [task for task in accepted_tasks(load_targets()) if task["id"] in wanted]
    missing = wanted - {task["id"] for task in tasks}
    if missing:
        raise SystemExit("record tasks not in the accepted pool: " + ", ".join(sorted(missing)))
    return tasks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", action="store_true", help="every pre-run check on the 22 tasks and 53 records, no model calls")
    parser.add_argument("--mock", action="store_true", help="mock LLM, output under runs/a6-retry-mock")
    parser.add_argument("--mock-slots", action="store_true", help="with --mock: two R0 and two R1 slots from different repos")
    parser.add_argument("--canary", action="store_true", help="only the first two R0 and first two R1 slots of the queue")
    parser.add_argument("--slot", action="append", default=[], help="<task>/<r0|r1>/b0r<k>/r<k>; repeatable")
    parser.add_argument("--runs-file", action="store_true", help="rewrite a6-retry-runs.json from existing summaries, no runs")
    args = parser.parse_args()
    if args.mock_slots and not args.mock:
        raise SystemExit("--mock-slots is only allowed with --mock")
    if sum(bool(item) for item in (args.mock_slots, args.canary, args.slot)) > 1:
        raise SystemExit("choose one of --mock-slots, --canary, --slot")
    manifest, attempts_sha = load_attempts()
    tasks = pool_tasks(manifest)
    repo_of = {task["id"]: task["repo"] for task in tasks}
    if args.runs_file:
        write_runs(manifest=manifest, attempts_sha256=attempts_sha, repo_of=repo_of, mock=args.mock)
        return
    if args.preflight:
        report = preflight(manifest, tasks)
        print("preflight", report["passed"], "of", report["total"], "tasks;", "prompts", json.dumps(report["prompts"]),
              "records", json.dumps(report["records"]), "slots", report["slots"], "pass", report["pass"], flush=True)
        if not report["pass"]:
            raise SystemExit("preflight failed")
        return
    queue = slot_queue(manifest["records"])
    if args.mock_slots:
        slots, label = mock_slots(queue, repo_of), "mock"
    elif args.canary:
        slots, label = canary_slots(queue), "canary"
    elif args.slot:
        known = set(queue)
        slots = [parse_slot(text) for text in args.slot]
        unknown = [slot for slot in slots if slot not in known]
        if unknown:
            raise SystemExit("not an A6-R slot: " + ", ".join("/".join(map(str, slot)) for slot in unknown))
        label = "slots"
    else:
        slots, label = queue, "main"
    if args.mock:
        label = "mock" if label == "mock" else "mock-" + label
    prepared = {task["id"]: materialize_runner_task(task) for task in tasks}
    expected = expected_prompts(manifest, prepared)
    out_root = out_root_for(args.mock)
    report = asyncio.run(run_slots(slots, mock=args.mock, out_root=out_root, manifest=manifest, expected=expected,
                                   prepared=prepared, attempts_sha256=attempts_sha, label=label))
    print(json.dumps({key: value for key, value in report.items() if key != "slots"}, indent=2), flush=True)
    if args.mock:
        write_runs(manifest=manifest, attempts_sha256=attempts_sha, repo_of=repo_of, mock=True, out_root=out_root)
    elif label == "main" and not report["halt_reason"]:
        write_runs(manifest=manifest, attempts_sha256=attempts_sha, repo_of=repo_of, mock=False, out_root=out_root)
    if report["halt_reason"]:
        raise SystemExit("stopped: " + report["halt_reason"])


if __name__ == "__main__":
    main()
