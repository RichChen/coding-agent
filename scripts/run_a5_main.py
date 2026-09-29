"""Run the main-pool comparison. All B0 repeats finish before any B2 repeat starts."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
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
    """Pre-registered: FAULT_ALARM_RUNS formal B0 runs, canary r1 slots excluded, with none solved."""
    if phase != "b0" or not out_root.exists():
        return None
    formal = []
    for path in sorted(out_root.glob("*/b0/r*/summary.json")):
        slot = path.parent.name
        if "." in slot or (slot == "r1" and path.parent.parent.parent.name in canaries):
            continue
        row = json.loads(path.read_text(encoding="utf-8"))
        if row.get("status") != "infra_error":
            formal.append(row)
    if len(formal) >= FAULT_ALARM_RUNS and not any(row.get("solved") for row in formal):
        return "fault alarm: " + str(len(formal)) + " formal B0 runs, none solved; audit the harness"
    return None


def halt_reason(out_root: Path, phase: str, canaries=frozenset()) -> str | None:
    """Stop conditions checked before every new run. In-flight runs still finish."""
    alarm = fault_alarm(out_root, phase, canaries)
    if alarm:
        return alarm
    rows = phase_summaries(out_root, phase)
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


async def run_phase(tasks, phase: str, *, cards: Path | None, mock: bool, repeats: int, out_root: Path | None = None, canaries=None):
    out_root = out_root or out_root_for(mock)
    if canaries is None:
        canaries = frozenset(canary_ids(accepted_tasks(load_targets())).values())
    profile = PROFILE
    variant = "B0" if phase == "b0" else "B2"
    pending = []
    refused = []
    kept_infra = []
    for task in tasks:
        for repeat in range(1, repeats + 1):
            output = out_root / task["id"] / phase / ("r" + str(repeat))
            summary_path = output / "summary.json"
            if summary_path.is_file():
                summary = json.loads(summary_path.read_text(encoding="utf-8"))
                problem = resumable(summary, phase=phase, mock=mock)
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
            pending.append((task, output))
    if refused:
        raise SystemExit("existing summaries do not belong to this phase; not overwriting:\n" + "\n".join(refused))
    state = {"halt": halt_reason(out_root, phase, canaries)}
    semaphore = asyncio.Semaphore(PARALLEL)

    async def one(task, output):
        async with semaphore:
            while True:
                if state["halt"]:
                    return None
                output.mkdir(parents=True, exist_ok=True)
                try:
                    summary = await run_task(
                        materialize_runner_task(task), profile, output, mock=mock, variant=variant, cards_path=cards,
                    )
                except (Exception, SystemExit) as exc:
                    state["halt"] = state["halt"] or ("run crashed: " + task["id"] + " " + type(exc).__name__ + ": " + str(exc)[:300])
                    return None
                state["halt"] = state["halt"] or halt_reason(out_root, phase, canaries)
                if summary.get("status") != "infra_error":
                    return summary
                if state["halt"] or not retire_infra(output):
                    kept_infra.append(_display_path(output))
                    return summary

    results = await asyncio.gather(*(one(task, output) for task, output in pending))
    report = {
        "phase": phase,
        "mock": mock,
        "parallel": PARALLEL,
        "halt_reason": state["halt"],
        "started": sum(1 for item in results if item is not None),
        "not_started": sum(1 for item in results if item is None),
        "infra_kept": sorted(set(kept_infra)),
        "infra_retired": sorted(_display_path(path) for path in out_root.glob("*/" + phase + "/r*.infra*")),
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
    parser.add_argument("--handoff", action="store_true", help="rewrite the B0 handoff from existing r1-r3 summaries, no runs")
    args = parser.parse_args()
    if args.handoff:
        write_b0_handoff(mock=args.mock)
        return
    if not args.preflight and not args.phase:
        raise SystemExit("--phase is required unless --preflight is given")
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
    report = asyncio.run(run_phase(tasks, args.phase, cards=cards, mock=args.mock, repeats=args.repeats, out_root=out_root))
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
