"""Run the main-pool comparison. All B0 repeats finish before any B2 repeat starts."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import random
import re
import statistics
import sys
from decimal import Decimal
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.handoff_sha import handoff_sha256  # noqa: E402
from scripts.preflight_a5_repo_baseline import patch_paths  # noqa: E402
from scripts.run_swe_task import parse_id_list, prerun_check, public_issue, run_task, tool_smoke  # noqa: E402
from scripts.select_main_targets import ISSUES, PUBLIC_ROOT, issue_sha256  # noqa: E402
from scripts.sprint5_prepare_main import FAMILY, nodeid_selection  # noqa: E402

TOTAL_CAP = Decimal("230")
PHASE_CAP = {"b0": Decimal("120"), "b2": TOTAL_CAP}
PARALLEL = 3
MAX_INFRA_RERUNS = 2
INFRA_STOP_RATIO = Decimal("0.10")
INFRA_STOP_MIN = 3
PROFILE = ROOT / "configs/sprint/b0-v2.yaml"
FAULT_ALARM_RUNS = 30
HANDOFF_REPEATS = (1, 2, 3)
DRIFT_REPEAT = 4
DRIFT_SEED = 20260929


def out_root_for(mock: bool) -> Path:
    return ROOT / "runs" / ("a5-main-mock" if mock else "a5-main")


def handoff_path_for(mock: bool) -> Path:
    return ROOT / "docs" / "sprint" / ("main-b0-runs.mock.json" if mock else "main-b0-runs.json")


def resumable(summary: dict, *, phase: str, mock: bool) -> str | None:
    """Return why an existing summary cannot count for this phase, or None."""
    if "mock" not in summary or "profile" not in summary:
        return "summary has no mock/profile field"
    if bool(summary["mock"]) != mock:
        return "summary is a mock run" if summary["mock"] else "summary is a real run"
    if summary["profile"] != PROFILE.stem:
        return "profile is " + str(summary["profile"])
    if summary.get("variant") != phase.upper():
        return "variant is " + str(summary.get("variant"))
    return None


def load_targets():
    return yaml.safe_load((ROOT / "configs/sprint/main-targets.yaml").read_text(encoding="utf-8"))["tasks"]


def accepted_tasks(tasks):
    folder = ROOT / "docs" / "sprint" / "main-calibration"
    kept = []
    for task in tasks:
        path = folder / (task["id"] + ".json")
        if not path.is_file():
            continue
        row = json.loads(path.read_text(encoding="utf-8"))
        if row.get("accepted"):
            kept.append(task)
    return kept


def spent(root: Path) -> Decimal:
    total = Decimal("0")
    if not root.exists():
        return total
    for path in root.rglob("summary.json"):
        row = json.loads(path.read_text(encoding="utf-8"))
        total += Decimal(str(row.get("cost_cny") or "0"))
    return total


def infra_attempts(output: Path) -> int:
    return sum(1 for path in output.parent.glob(output.name + ".infra*") if path.is_dir())


def retire_infra(output: Path) -> bool:
    """Move an infra_error run to r<k>.infra<n> so the slot can run again. False once the reruns are used up."""
    used = infra_attempts(output)
    if used >= MAX_INFRA_RERUNS:
        return False
    output.rename(output.with_name(output.name + ".infra" + str(used + 1)))
    return True


def phase_summaries(out_root: Path, phase: str) -> list[dict]:
    """Every attempt of a phase, including retired infra_error runs."""
    rows = []
    if not out_root.exists():
        return rows
    for path in sorted(out_root.glob("*/" + phase + "/r*/summary.json")):
        rows.append(json.loads(path.read_text(encoding="utf-8")))
    return rows


def canary_ids(tasks) -> dict:
    """Map repo to the lower-median task by created_at; its B0 r1 is the canary."""
    groups = {}
    for task in tasks:
        groups.setdefault(task["repo"], []).append(task)
    chosen = {}
    for repo, rows in sorted(groups.items()):
        rows = sorted(rows, key=lambda row: str(row["created_at"]))
        chosen[repo] = rows[(len(rows) - 1) // 2]["id"]
    return chosen


def fault_alarm(out_root: Path, phase: str, canaries) -> str | None:
    """Pre-registered: FAULT_ALARM_RUNS formal runs of the phase with none solved.

    B0 excludes the canary r1 slots. B2 counts only b2 slots, so the b0/r4 drift slots never count.
    """
    if phase not in ("b0", "b2") or not out_root.exists():
        return None
    formal = []
    for path in sorted(out_root.glob("*/" + phase + "/r*/summary.json")):
        slot = path.parent.name
        if "." in slot or (phase == "b0" and slot == "r1" and path.parent.parent.parent.name in canaries):
            continue
        row = json.loads(path.read_text(encoding="utf-8"))
        if row.get("status") != "infra_error":
            formal.append(row)
    if len(formal) >= FAULT_ALARM_RUNS and not any(row.get("solved") for row in formal):
        return ("fault alarm: " + str(len(formal)) + " formal " + phase.upper() + " runs, none solved; audit the harness")
    return None


def actual_injection(run_dir: Path) -> list[str] | None:
    """Card ids the host actually put into the model view, from context.prepared events. None without events."""
    events = run_dir / "events.jsonl"
    if not events.is_file():
        return None
    ids = set()
    with events.open(encoding="utf-8") as handle:
        for line in handle:
            if '"context.prepared"' not in line:
                continue
            event = json.loads(line)
            if event.get("event_type") != "context.prepared":
                continue
            plugin = ((event.get("payload") or {}).get("stats") or {}).get("plugin") or {}
            ids.update(item["id"] for item in plugin.get("actually_injected") or [] if item.get("reason") == "memory_card")
    return sorted(ids)


def injection_mismatch(out_root: Path, predicted: dict, verified: set) -> str | None:
    """D7: every finished B2 run must inject exactly the predicted card set. verified caches runs already checked."""
    for path in sorted(out_root.glob("*/b2/r*/summary.json")):
        run_dir = path.parent
        if "." in run_dir.name or run_dir in verified:
            continue
        row = json.loads(path.read_text(encoding="utf-8"))
        if row.get("status") == "infra_error":
            continue
        task_id = run_dir.parent.parent.name
        actual = actual_injection(run_dir)
        if actual is None:
            return "injection cannot be checked, no events.jsonl: " + task_id + " " + run_dir.name
        expected = sorted(predicted.get(task_id, ["<task not in the predicted table>"]))
        if actual != expected:
            return "injection differs from the prediction: " + task_id + " " + run_dir.name + " actual " + json.dumps(actual) + " predicted " + json.dumps(expected)
        verified.add(run_dir)
    return None


def halt_reason(out_root: Path, phase: str, canaries=frozenset(), extra_phases=(), predicted=None, verified=None) -> str | None:
    """Stop conditions checked before every new run. In-flight runs still finish.

    extra_phases get the same per-run checks (the b0/r4 drift slots during B2); the spend cap is the phase's.
    predicted maps task id to the card ids B2 must inject.
    """
    alarm = fault_alarm(out_root, phase, canaries)
    if alarm:
        return alarm
    for checked in (phase, *extra_phases):
        reason = run_checks(phase_summaries(out_root, checked))
        if reason:
            return reason
    if predicted is not None:
        reason = injection_mismatch(out_root, predicted, set() if verified is None else verified)
        if reason:
            return reason
    names = set()
    for row in phase_summaries(out_root, "b0") + (phase_summaries(out_root, "b2") if phase != "b0" else []):
        model = row.get("model") or {}
        if model.get("changed_to"):
            return "model changed during a run: " + str(row.get("task_id"))
        if model.get("name"):
            names.add(model["name"])
    if len(names) > 1:
        return "model name changed between runs: " + ", ".join(sorted(names))
    cost = spent(out_root)
    if cost >= PHASE_CAP[phase]:
        return "spend " + str(cost) + " CNY reached the " + phase + " cap " + str(PHASE_CAP[phase])
    return None


def run_checks(rows: list[dict]) -> str | None:
    infra = sum(1 for row in rows if row.get("status") == "infra_error")
    if infra >= INFRA_STOP_MIN and Decimal(infra) > INFRA_STOP_RATIO * len(rows):
        return "infra_error " + str(infra) + " of " + str(len(rows)) + " completed runs"
    for row in rows:
        if (row.get("harness_tool_errors") or 0) > 0:
            return "harness tool errors: " + str(row.get("task_id")) + " " + str(row["harness_tool_errors"])
        if row.get("answer_isolation_pass") is False or row.get("status") == "answer_isolation_failed":
            return "answer isolation failed: " + str(row.get("task_id")) + " " + str(row.get("stop_reason"))
        if row.get("status") == "infra_error":
            continue
        ids = row.get("grader_ids") or {}
        if ids.get("missing") and not row.get("grader_candidate_error"):
            return "grader reported missing ids: " + str(row.get("task_id"))
        if ids.get("reason") or row.get("grader_status") == "invalid_env":
            return "grader crashed: " + str(row.get("task_id")) + " " + str(ids.get("reason"))
    return None


def slot_queue(tasks, phase: str, repeats: int, *, with_b0_drift: bool = False) -> list[tuple[dict, str, int]]:
    """(task, slot phase, repeat) in run order. With the drift arm, B2 slots and b0/r4 slots share one queue,
    shuffled with DRIFT_SEED after a canonical sort so the order does not depend on the input order."""
    slots = [(task, phase, repeat) for task in tasks for repeat in range(1, repeats + 1)]
    if not with_b0_drift:
        return slots
    if phase != "b2":
        raise SystemExit("the b0 drift arm only runs with phase b2")
    slots += [(task, "b0", DRIFT_REPEAT) for task in tasks]
    slots.sort(key=lambda slot: (slot[0]["id"], slot[1], slot[2]))
    random.Random(DRIFT_SEED).shuffle(slots)
    return slots


async def run_phase(tasks, phase: str, *, cards: Path | None, mock: bool, repeats: int, out_root: Path | None = None,
                    canaries=None, with_b0_drift: bool = False, prerun_checks: dict | None = None, predicted: dict | None = None):
    out_root = out_root or out_root_for(mock)
    verified = set()
    if canaries is None:
        canaries = frozenset(canary_ids(accepted_tasks(load_targets())).values())
    profile = PROFILE
    extra = ("b0",) if with_b0_drift else ()
    pending = []
    refused = []
    kept_infra = []
    for task, slot_phase, repeat in slot_queue(tasks, phase, repeats, with_b0_drift=with_b0_drift):
        output = out_root / task["id"] / slot_phase / ("r" + str(repeat))
        summary_path = output / "summary.json"
        if summary_path.is_file():
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            problem = resumable(summary, phase=slot_phase, mock=mock)
            if problem:
                refused.append(str(summary_path) + ": " + problem)
                continue
            if summary.get("status") != "infra_error":
                continue
            if not retire_infra(output):
                kept_infra.append(_display_path(output))
                continue
        elif output.exists():
            refused.append(str(output) + ": directory has no summary.json (an interrupted run)")
            continue
        pending.append((task, output, slot_phase))
    if refused:
        raise SystemExit("existing summaries do not belong to this phase; not overwriting:\n" + "\n".join(refused))
    state = {"halt": halt_reason(out_root, phase, canaries, extra, predicted, verified)}
    semaphore = asyncio.Semaphore(PARALLEL)

    async def one(task, output, slot_phase):
        variant = "B0" if slot_phase == "b0" else "B2"
        slot_cards = cards if slot_phase == "b2" else None
        async with semaphore:
            while True:
                if state["halt"]:
                    return None
                output.mkdir(parents=True, exist_ok=True)
                try:
                    summary = await run_task(
                        materialize_runner_task(task), profile, output, mock=mock, variant=variant, cards_path=slot_cards,
                    )
                except (Exception, SystemExit) as exc:
                    state["halt"] = state["halt"] or ("run crashed: " + task["id"] + " " + type(exc).__name__ + ": " + str(exc)[:300])
                    return None
                state["halt"] = state["halt"] or halt_reason(out_root, phase, canaries, extra, predicted, verified)
                if summary.get("status") != "infra_error":
                    return summary
                if state["halt"] or not retire_infra(output):
                    kept_infra.append(_display_path(output))
                    return summary

    results = await asyncio.gather(*(one(*item) for item in pending))
    retired = [path for slot_phase in (phase, *extra) for path in out_root.glob("*/" + slot_phase + "/r*.infra*")]
    report = {
        "phase": phase,
        "with_b0_drift": with_b0_drift,
        "prerun_checks": prerun_checks,
        "injection_verified_runs": len(verified),
        "mock": mock,
        "parallel": PARALLEL,
        "halt_reason": state["halt"],
        "started": sum(1 for item in results if item is not None),
        "not_started": sum(1 for item in results if item is None),
        "started_by_slot_phase": {slot_phase: sum(1 for item, (_, _, p) in zip(results, pending) if item is not None and p == slot_phase)
                                  for slot_phase in (phase, *extra)},
        "infra_kept": sorted(set(kept_infra)),
        "infra_retired": sorted(_display_path(path) for path in retired),
        "spent_cny": str(spent(out_root)),
    }
    out_root.mkdir(parents=True, exist_ok=True)
    (out_root / (phase + "-report.json")).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def checked_public(task: dict) -> Path:
    """runs/sprint5-main-public/<id>.json, verified against docs/sprint/main-issues.json."""
    path = PUBLIC_ROOT / (task["id"] + ".json")
    if not path.is_file():
        raise SystemExit("public file missing for " + task["id"] + ": " + _display_path(path))
    public = json.loads(path.read_text(encoding="utf-8"))
    text = public.get("issue_text")
    if not isinstance(text, str) or not text.strip():
        raise SystemExit("public file for " + task["id"] + " has no issue_text")
    expected = (json.loads(ISSUES.read_text(encoding="utf-8"))["tasks"].get(task["id"]) or {}).get("issue_sha256")
    if expected is None:
        raise SystemExit(task["id"] + " is not in docs/sprint/main-issues.json")
    if issue_sha256(text) != expected or public.get("issue_sha256") != expected:
        raise SystemExit("issue sha for " + task["id"] + " differs from docs/sprint/main-issues.json")
    ref = public.get("repo_ref") or {}
    if ref.get("repo_id") != task["repo"] or ref.get("revision") != task["base_commit"]:
        raise SystemExit("repo_ref for " + task["id"] + " differs from the target")
    return path


def materialize_runner_task(task: dict) -> dict:
    """Give a pool task the receipt and public issue run_task already expects.

    Generated files stay under runs/. The public file does not contain patches.
    """
    if task.get("receipt") and task.get("public_task") and task.get("family"):
        return task
    private_path = ROOT / task["private"]
    private = json.loads(private_path.read_text(encoding="utf-8"))
    if not private.get("test_patch") or not private.get("patch"):
        raise SystemExit("private file for " + task["id"] + " has no test_patch or patch")
    public_path = checked_public(task)
    clean = json.loads((ROOT / "docs" / "sprint" / "clean-images" / (task["id"] + ".json")).read_text(encoding="utf-8"))
    calibration_path = ROOT / "docs" / "sprint" / "main-calibration" / (task["id"] + ".json")
    calibration = json.loads(calibration_path.read_text(encoding="utf-8"))
    excluded = calibration.get("p2p_excluded") or []
    f2p, p2p, report = nodeid_selection(task, private, patch_paths(private["test_patch"]))
    recorded = calibration.get("nodeids") or {}
    for side in ("f2p", "p2p"):
        if report[side] != recorded.get(side):
            raise SystemExit(
                "grader ids for " + task["id"] + " differ from calibration on " + side
                + ": " + json.dumps(report[side]) + " vs " + json.dumps(recorded.get(side))
            )
    folder = ROOT / "runs" / "sprint5-main-runner" / task["id"]
    folder.mkdir(parents=True, exist_ok=True)
    archive = ROOT / "runs" / "sprint5-main-images" / task["id"] / "source.tar.gz"
    receipt = {
        "baseline_image_digest": clean["clean_image_digest"],
        "base_revision": task["base_commit"],
        "source_attempt_ref": archive.as_posix(),
        "private_source_binding": {
            "path": private_path.as_posix(),
            "test_patch_paths": patch_paths(private["test_patch"]),
            "gold_patch_paths": patch_paths(private["patch"]),
        },
    }
    receipt_path = folder / "receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    staging = ROOT / "runs" / "sprint5-main-images" / task["id"] / "staging"
    prepared = dict(task)
    prepared["family"] = FAMILY[task["repo"]]
    prepared["receipt"] = receipt_path.relative_to(ROOT).as_posix()
    prepared["public_task"] = public_path.as_posix()
    prepared["original"] = (staging / "original").relative_to(ROOT).as_posix()
    prepared["baseline"] = (staging / "baseline").relative_to(ROOT).as_posix()
    prepared["grader_timeout_seconds"] = 600
    prepared["p2p_excluded"] = excluded
    prepared["grader_nodeids"] = {"f2p": f2p, "p2p": p2p}
    return prepared


def calibration_ids(task_id: str) -> dict:
    path = ROOT / "docs" / "sprint" / "main-calibration" / (task_id + ".json")
    nodeids = json.loads(path.read_text(encoding="utf-8")).get("nodeids") or {}
    return {side: (nodeids.get(side) or {}).get("used") for side in ("f2p", "p2p")}


def image_python(clean: dict | None):
    """Major.minor of the clean image's base, e.g. python:3.6.15-slim-buster -> 3.6."""
    match = re.match(r"python:(\d+)\.(\d+)", (clean or {}).get("base_image") or "")
    return f"{match.group(1)}.{match.group(2)}" if match else None


def prompt_check(task: dict, prepared: dict) -> dict:
    """Render the user prompt and check it carries the verbatim issue and nothing private."""
    prompt = public_issue(prepared)
    issue = json.loads(Path(prepared["public_task"]).read_text(encoding="utf-8"))["issue_text"]
    expected = json.loads(ISSUES.read_text(encoding="utf-8"))["tasks"][task["id"]]["issue_sha256"]
    private = json.loads((ROOT / task["private"]).read_text(encoding="utf-8"))
    verbatim = prompt.endswith("Public issue:\n" + issue)
    template = prompt[: len(prompt) - len(issue)] if verbatim else prompt
    fields = [name for name in ("patch", "test_patch", "FAIL_TO_PASS", "PASS_TO_PASS") if private.get(name) and private[name] in prompt]
    ids = parse_id_list(private["FAIL_TO_PASS"]) + parse_id_list(private["PASS_TO_PASS"])
    ids += list(prepared["grader_nodeids"]["f2p"]) + list(prepared["grader_nodeids"]["p2p"])
    leaked = sorted({node for node in ids if node and node in template})
    row = {
        "issue_chars": len(issue),
        "issue_sha256": issue_sha256(issue),
        "prompt_chars": len(prompt),
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "issue_verbatim": verbatim,
        "issue_sha_matches": issue_sha256(issue) == expected,
        "private_fields_in_prompt": fields,
        "private_ids_in_template": leaked[:10],
        "ids_in_public_issue": sorted({node for node in ids if node and node in issue})[:10],
    }
    problems = [name for name, bad in (
        ("empty prompt", not prompt or not issue),
        ("issue not verbatim", not verbatim),
        ("issue sha differs from main-issues.json", not row["issue_sha_matches"]),
        ("private field in prompt", bool(fields)),
        ("private id in prompt template", bool(leaked)),
    ) if bad]
    row["failure"] = "; ".join(problems) or None
    return row


def recorded_user_prompt(events: Path) -> str:
    for line in events.read_text(encoding="utf-8").splitlines():
        event = json.loads(line) if line.strip() else {}
        if event.get("event_type") == "state.saved":
            for message in event["payload"]["messages"]:
                if message.get("role") == "user":
                    return message["content"]
    raise SystemExit("no user prompt recorded in " + _display_path(events))


def dev_prompt_check() -> dict:
    """The dev prompts render byte-identical to the ones the sprint-4 B0 runs sent."""
    rows = []
    dev = yaml.safe_load((ROOT / "configs/sprint/dev-tasks.yaml").read_text(encoding="utf-8"))["tasks"]
    for task in dev:
        row = {"task_id": task["id"]}
        try:
            rendered = public_issue(task).encode("utf-8")
            recorded = recorded_user_prompt(ROOT / "runs" / "sprint4-b0-v2" / task["id"] / "r1" / "events.jsonl").encode("utf-8")
            row.update(
                identical=rendered == recorded,
                rendered_sha256=hashlib.sha256(rendered).hexdigest(),
                recorded_sha256=hashlib.sha256(recorded).hexdigest(),
            )
        except (Exception, SystemExit) as exc:
            row.update(identical=False, error=type(exc).__name__ + ": " + str(exc)[:300])
        rows.append(row)
    return {"identical": sum(1 for row in rows if row["identical"]), "total": len(rows), "tasks": rows}


def preflight(tasks, destination: Path | None = None) -> dict:
    """Every check a run makes before its first model call, on every task. No model calls."""
    rows = []
    for task in tasks:
        row = {"task_id": task["id"]}
        try:
            prepared = materialize_runner_task(task)
            spec, image, clean, failure = prerun_check(prepared, mock=False)
            f2p = [node for node in spec.expected_nodeids if node not in spec.baseline_passed]
            counts = {"f2p": len(f2p), "p2p": len(spec.baseline_passed)}
            recorded = calibration_ids(task["id"])
            excluded = list(prepared.get("p2p_excluded") or [])
            stray = [node for node in excluded if node not in prepared["grader_nodeids"]["p2p"]]
            expected = {"f2p": recorded["f2p"], "p2p": None if recorded["p2p"] is None else recorded["p2p"] - len(excluded)}
            if failure is None and stray:
                failure = "p2p_excluded ids not in the selected p2p: " + json.dumps(stray[:3])
            if failure is None and counts != expected:
                failure = "grader ids " + json.dumps(counts) + " differ from calibration " + json.dumps(expected)
            row["prompt"] = prompt_check(task, prepared)
            if failure is None and row["prompt"]["failure"]:
                failure = "prompt check failed: " + row["prompt"]["failure"]
            row.update(
                image=image,
                python=image_python(clean),
                answer_isolation_pass=bool(clean and clean.get("answer_isolation_pass")),
                grader_ids=counts,
                calibration_ids=recorded,
                p2p_excluded=len(excluded),
                public_task=_display_path(Path(prepared["public_task"])),
                failure=failure,
            )
            if failure is None:
                smoke = asyncio.run(tool_smoke(image, PROFILE))
                row["tool_smoke"] = smoke
                if not smoke["passed"]:
                    bad = [c["tool"] + ":" + str(c["exception"] or c["error_kind"]) for c in smoke["calls"] if not c["ok"]]
                    row["failure"] = "tool smoke failed: " + (smoke["error"] or ", ".join(bad) or "incomplete")
        except (Exception, SystemExit) as exc:
            row["failure"] = type(exc).__name__ + ": " + str(exc)[:300]
        row["pass"] = row.get("failure") is None
        rows.append(row)
        print(task["id"], "pass" if row["pass"] else row["failure"], flush=True)
    by_python = {}
    for row in rows:
        bucket = by_python.setdefault(row.get("python") or "unknown", {"passed": 0, "total": 0, "tool_smoke_passed": 0})
        bucket["total"] += 1
        bucket["passed"] += int(row["pass"])
        bucket["tool_smoke_passed"] += int(bool((row.get("tool_smoke") or {}).get("passed")))
    chars = [row["prompt"]["issue_chars"] for row in rows if row.get("prompt")]
    report = {
        "passed": sum(1 for row in rows if row["pass"]),
        "total": len(rows),
        "tool_smoke_passed": sum(1 for row in rows if (row.get("tool_smoke") or {}).get("passed")),
        "prompt_passed": sum(1 for row in rows if row.get("prompt") and row["prompt"]["failure"] is None),
        "issue_chars": {"min": min(chars), "median": statistics.median(chars), "max": max(chars)} if chars else None,
        "by_python": dict(sorted(by_python.items())),
        "dev_prompts": dev_prompt_check(),
        "tasks": rows,
    }
    destination = destination or ROOT / "runs" / "a5-main-logs" / "preflight.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def write_b0_handoff(*, mock: bool = False, out_root: Path | None = None, destination: Path | None = None, tasks=None):
    out_root = out_root or out_root_for(mock)
    issues = json.loads(ISSUES.read_text(encoding="utf-8"))["tasks"]
    runs = []
    for task in tasks if tasks is not None else accepted_tasks(load_targets()):
        for repeat in HANDOFF_REPEATS:
            run_dir = out_root / task["id"] / "b0" / ("r" + str(repeat))
            summary_path = run_dir / "summary.json"
            if not summary_path.is_file():
                continue
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            problem = resumable(summary, phase="b0", mock=mock)
            if problem:
                raise SystemExit("refusing to hand off " + str(summary_path) + ": " + problem)
            grader_path = run_dir / "grader-result.json"
            if not grader_path.is_file():
                raise SystemExit("refusing to hand off " + str(run_dir) + ": no grader-result.json")
            if not (PUBLIC_ROOT / (task["id"] + ".json")).is_file():
                raise SystemExit("refusing to hand off " + task["id"] + ": no public task file")
            expected = (issues.get(task["id"]) or {}).get("issue_sha256")
            if expected is None or summary.get("issue_sha256") != expected:
                raise SystemExit("refusing to hand off " + str(summary_path) + ": issue_sha256 is not main-issues.json")
            runs.append({
                "source_id": task["id"],
                "repo": task["repo"],
                "created_at": task["created_at"],
                "repeat": repeat,
                "solved": summary.get("solved"),
                "status": summary.get("status"),
                "cost_cny": summary.get("cost_cny"),
                "summary": _display_path(summary_path),
                "answer_isolation_pass": summary.get("answer_isolation_pass"),
                "base_commit": task["base_commit"],
                "grader_status": json.loads(grader_path.read_text(encoding="utf-8")).get("status"),
                "run_dir": _display_path(run_dir),
                "public_task": _display_path(PUBLIC_ROOT / (task["id"] + ".json")),
                "issue_sha256": summary["issue_sha256"],
            })
    destination = destination or handoff_path_for(mock)
    payload = {
        "schema": "sprint6.main-b0-runs.v2",
        "profile_tag": "b0-v2",
        "runs": runs,
    }
    if mock:
        payload["scope"] = "mock"
        payload["note"] = "Zero-model mock runs. This is not the R6 handoff."
    destination.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(handoff_sha256(destination), flush=True)
    return destination


DEV_HANDOFF = ROOT / "docs" / "sprint" / "memory-source-runs.json"


def check_cards_manifest(cards: Path, handoffs=None) -> dict:
    """D5: refuse B2 unless the card manifest is final, names both current handoffs, and matches the card file."""
    manifest_path = cards.with_name(cards.name.removesuffix(".jsonl") + ".manifest.json")
    if not cards.is_file() or not manifest_path.is_file():
        raise SystemExit("card file or manifest missing: " + str(cards) + ", " + str(manifest_path))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    problems = []
    if manifest.get("status") != "final":
        problems.append("status is " + str(manifest.get("status")))
    listed = {(row.get("schema"), row.get("sha256")) for row in (manifest.get("build_inputs") or {}).get("handoffs") or []}
    expected = {}
    for path in handoffs or (DEV_HANDOFF, handoff_path_for(False)):
        schema = json.loads(path.read_text(encoding="utf-8")).get("schema")
        expected[path.name] = {"schema": schema, "sha256": handoff_sha256(path)}
        if (schema, expected[path.name]["sha256"]) not in listed:
            problems.append("handoff " + path.name + " (" + str(schema) + ", " + expected[path.name]["sha256"] + ") not in build_inputs.handoffs")
    cards_sha = hashlib.sha256(cards.read_bytes()).hexdigest()
    if manifest.get("cards_sha256") != cards_sha:
        problems.append("cards_sha256 " + str(manifest.get("cards_sha256")) + " but the file hashes to " + cards_sha)
    if problems:
        raise SystemExit("card manifest check failed, not running B2:\n" + "\n".join(problems))
    return {"cards": _display_path(cards), "cards_sha256": cards_sha, "manifest": _display_path(manifest_path), "handoffs": expected}


PREDICTED = ROOT / "docs" / "sprint" / "b2-predicted-injection.json"


def load_predicted(cards_sha256: str, path: Path = PREDICTED, repo: Path = ROOT) -> tuple[dict, dict]:
    """D6/D7: the predicted injection table must be committed, unchanged, and built from the same card file."""
    import subprocess

    if not path.is_file():
        raise SystemExit("predicted injection table missing: " + str(path))
    relative = path.relative_to(repo).as_posix()
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", relative], cwd=repo, capture_output=True, text=True)
    dirty = subprocess.run(["git", "status", "--porcelain", "--", relative], cwd=repo, capture_output=True, text=True)
    if tracked.returncode != 0 or dirty.stdout.strip():
        raise SystemExit("predicted injection table is not committed as is: " + relative)
    table = json.loads(path.read_text(encoding="utf-8"))
    if table.get("cards_sha256") != cards_sha256:
        raise SystemExit("predicted injection table was built from cards " + str(table.get("cards_sha256")) + ", not " + cards_sha256)
    by_task = {row["id"]: [item["id"] for item in row["injected"]] for row in table["runs"]}
    commit = subprocess.run(["git", "log", "-1", "--format=%H", "--", relative], cwd=repo, capture_output=True, text=True).stdout.strip()
    return by_task, {"path": relative, "sha256": handoff_sha256(path), "commit": commit, "tasks": len(by_task)}


def _display_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=["b0", "b2"])
    parser.add_argument("--cards", default=None)
    parser.add_argument("--mock", action="store_true")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--task", action="append", default=[])
    parser.add_argument("--preflight", action="store_true", help="run every pre-run check on the pool, no model calls")
    parser.add_argument("--out-root", default=None, help="output root for a mock run")
    parser.add_argument("--with-b0-drift", action="store_true", help="B2 only: also run b0/r4 for every task in one shuffled queue")
    parser.add_argument("--handoff", action="store_true", help="rewrite the B0 handoff from existing r1-r3 summaries, no runs")
    args = parser.parse_args()
    if args.handoff:
        write_b0_handoff(mock=args.mock)
        return
    if not args.preflight and not args.phase:
        raise SystemExit("--phase is required unless --preflight is given")
    if args.with_b0_drift and args.phase != "b2":
        raise SystemExit("--with-b0-drift is only allowed with --phase b2")
    if args.phase == "b2" and not args.cards:
        raise SystemExit("B2 requires --cards")
    if args.out_root and not args.mock:
        raise SystemExit("--out-root is only allowed with --mock")
    tasks = accepted_tasks(load_targets())
    if args.task:
        wanted = set(args.task)
        tasks = [task for task in tasks if task["id"] in wanted]
        missing = wanted - {task["id"] for task in tasks}
        if missing:
            raise SystemExit("not an accepted task: " + ", ".join(sorted(missing)))
    if not tasks:
        raise SystemExit("no accepted main-pool tasks")
    if args.preflight:
        checked = preflight(tasks)
        dev = checked["dev_prompts"]
        print("preflight", checked["passed"], "of", checked["total"], "passed;",
              "dev prompts", dev["identical"], "of", dev["total"], "identical", flush=True)
        if checked["passed"] != checked["total"] or dev["identical"] != dev["total"]:
            raise SystemExit("preflight failed")
        return
    cards = Path(args.cards) if args.cards else None
    if cards is not None and not cards.is_absolute():
        cards = ROOT / cards
    out_root = Path(args.out_root) if args.out_root else None
    if out_root is not None and not out_root.is_absolute():
        out_root = ROOT / out_root
    checks = None
    predicted = None
    if args.phase == "b2":
        checks = {"cards_manifest": check_cards_manifest(cards)}
        predicted, checks["predicted_injection"] = load_predicted(checks["cards_manifest"]["cards_sha256"])
        missing = [task["id"] for task in tasks if task["id"] not in predicted]
        if missing:
            raise SystemExit("tasks missing from the predicted injection table: " + ", ".join(missing))
    report = asyncio.run(run_phase(tasks, args.phase, cards=cards, mock=args.mock, repeats=args.repeats, out_root=out_root,
                                   with_b0_drift=args.with_b0_drift, prerun_checks=checks, predicted=predicted))
    print(json.dumps(report, indent=2), flush=True)
    if report["halt_reason"]:
        raise SystemExit("stopped: " + report["halt_reason"])
    if out_root is not None:
        print("Custom --out-root: no handoff written.", flush=True)
        return
    if args.phase == "b0" and not args.task:
        write_b0_handoff(mock=args.mock)
        print("B0 finished. Stop for card building.", flush=True)


if __name__ == "__main__":
    main()
