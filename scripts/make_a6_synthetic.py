"""Synthetic A6-R inputs for checking scripts/analyze_a6_retry.py. No model calls, no real runs.

Each scenario is a fake harness root with the same layout the analysis reads:
runs/a5-main, runs/sprint5-main-images/<task>/staging/original, runs/a6-retry,
docs/sprint/a6-attempts.json and docs/sprint/a6-retry-runs.json.

Shape follows the A5 B0 failures: 13 tasks at 0/3 with 3 first attempts each, 9 middle tasks
(5 at 1/3 with 2 first attempts, 4 at 2/3 with 1). The fresh retry rate is drawn per task,
uniform on [0, 0.1] for 0/3 and [0.3, 0.7] for the middle tier. R1 adds the true effect to every
run, so the expected mean d_t equals the effect.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import random
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.analyze_a6_retry import (  # noqa: E402
    SEED,
    _stats,
    load_attempts,
    load_runs,
    prepare,
    render_report,
)
from scripts.handoff_sha import handoff_sha256  # noqa: E402

SCENARIOS = (("effect-0", 0.0), ("effect-15", 0.15), ("effect-30", 0.30))
REPOS = ("django/django", "pytest-dev/pytest", "sphinx-doc/sphinx", "sympy/sympy")
ORIGINAL = "def f():\n    return 0\n\n\ndef g():\n    return 0\n"
TEST_FILE = "def test_f():\n    assert True\n"
REPEAT_FIRST = {"r0": 0.4, "r1": 0.15}
NULL_REPLICATES = 200
ESTIMATE_TOLERANCE = 0.10


def _b64(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def _tasks() -> list[dict]:
    tasks = []
    for index in range(22):
        repo = REPOS[index % len(REPOS)]
        task_id = repo.replace("/", "__") + f"-{90000 + index}"
        if index < 13:
            failed = (1, 2, 3)
        elif index < 18:
            failed = (2, 3)
        else:
            failed = (3,)
        tasks.append(
            {
                "task_id": task_id,
                "repo": repo,
                "failed": failed,
                "tier": "0/3" if index < 13 else "mid",
            }
        )
    return tasks


def _first_delta(order: int, repeat: int) -> dict:
    if order % 5 == 0:
        return {"changed": {}, "deleted": []}
    if order % 17 == 3:
        return {"changed": {"tests/test_mod.py": _b64(TEST_FILE + "# tried\n")}, "deleted": []}
    body = ORIGINAL.replace("return 0\n\n", f"return {repeat}\n\n", 1)
    return {"changed": {"pkg/mod.py": _b64(body)}, "deleted": []}


def _second_delta(rng: random.Random, arm: str, first: dict, serial: int) -> dict:
    if rng.random() < REPEAT_FIRST[arm]:
        return json.loads(json.dumps(first))
    if rng.random() < 0.5:
        body = ORIGINAL.replace("return 0\n", f"return {100 + serial}\n", 1)
        return {"changed": {"pkg/mod.py": _b64(body)}, "deleted": []}
    return {"changed": {"pkg/other.py": _b64(f"VALUE = {serial}\n")}, "deleted": []}


def _changed(delta: dict) -> list[str]:
    return sorted(list(delta.get("changed") or {}) + list(delta.get("deleted") or []))


def simulate(effect: float, seed: int) -> dict:
    """In-memory scenario: tasks, A5 B0 summaries and deltas, attempts, and slot rows."""
    rng = random.Random(seed)
    tasks = _tasks()
    a5 = {}
    attempts = []
    order = 0
    for task in tasks:
        task["fresh"] = rng.uniform(0.0, 0.1) if task["tier"] == "0/3" else rng.uniform(0.3, 0.7)
        for repeat in (1, 2, 3):
            failed = repeat in task["failed"]
            delta = (
                _first_delta(order, repeat)
                if failed
                else {
                    "changed": {"pkg/mod.py": _b64(ORIGINAL.replace("return 0", "return 42", 1))},
                    "deleted": [],
                }
            )
            if failed:
                order += 1
                first = f"b0r{repeat}"
                sha = hashlib.sha256(f"{task['task_id']}/{first}".encode()).hexdigest()
                attempts.append({"task": task["task_id"], "first": first, "sha256": sha})
            a5[(task["task_id"], repeat)] = {
                "summary": {
                    "task_id": task["task_id"],
                    "variant": "B0",
                    "mock": False,
                    "solved": not failed,
                    "status": "fail" if failed else "pass",
                    "prompt_sha256": "prompt-" + task["task_id"],
                    "changed_files": _changed(delta),
                },
                "delta": delta,
            }
    by_task = {task["task_id"]: task for task in tasks}
    slots = sorted(
        (item["task"], arm, item["first"], k)
        for item in attempts
        for arm in ("r0", "r1")
        for k in (1, 2, 3)
    )
    rows = []
    deltas = {}
    for serial, (task_id, arm, first, k) in enumerate(slots):
        task = by_task[task_id]
        rate = task["fresh"] + (effect if arm == "r1" else 0.0)
        solved = rng.random() < rate
        first_delta = a5[(task_id, int(first[-1]))]["delta"]
        delta = _second_delta(rng, arm, first_delta, serial)
        calls = rng.randint(12, 40) if arm == "r1" else rng.randint(15, 40)
        run_dir = f"runs/a6-retry/{task_id}/{arm}/{first}/r{k}"
        attempt = next(
            item for item in attempts if item["task"] == task_id and item["first"] == first
        )
        rows.append(
            {
                "task_id": task_id,
                "repo": task["repo"],
                "arm": arm,
                "first": first,
                "k": k,
                "run_dir": run_dir,
                "mock": False,
                "status": "pass" if solved else "fail",
                "solved": solved,
                "model_calls": calls,
                "first_edit_step": None if rng.random() < 0.05 else rng.randint(3, 15),
                "cost_cny": f"{calls * 0.016:.6f}",
                "stop_reason": "max_model_calls" if calls >= 40 else "completed",
                "changed_files": _changed(delta),
                "prompt_sha256": "prompt-" + task_id
                if arm == "r0"
                else f"prompt-{task_id}-{first}",
                "retry": {
                    "arm": arm,
                    "first": first,
                    "attempt_sha256": attempt["sha256"] if arm == "r1" else None,
                },
            }
        )
        deltas[run_dir] = delta
    for row in rng.sample([row for row in rows if len(by_task[row["task_id"]]["failed"]) == 3], 2):
        row["status"] = "infra_error"
        row["solved"] = False
    return {"tasks": tasks, "a5": a5, "attempts": attempts, "rows": rows, "deltas": deltas}


def write_scenario(root: Path, scenario: dict) -> tuple[Path, Path]:
    for task in scenario["tasks"]:
        original = root / "runs" / "sprint5-main-images" / task["task_id"] / "staging" / "original"
        (original / "pkg").mkdir(parents=True, exist_ok=True)
        (original / "tests").mkdir(parents=True, exist_ok=True)
        (original / "pkg" / "mod.py").write_bytes(ORIGINAL.encode())
        (original / "tests" / "test_mod.py").write_bytes(TEST_FILE.encode())
    for (task_id, repeat), item in scenario["a5"].items():
        run = root / "runs" / "a5-main" / task_id / "b0" / f"r{repeat}"
        run.mkdir(parents=True, exist_ok=True)
        (run / "summary.json").write_text(json.dumps(item["summary"], indent=2), encoding="utf-8")
        (run / "candidate-delta.json").write_text(
            json.dumps(item["delta"], indent=2), encoding="utf-8"
        )
    for run_dir, delta in scenario["deltas"].items():
        run = root / run_dir
        run.mkdir(parents=True, exist_ok=True)
        (run / "candidate-delta.json").write_text(json.dumps(delta, indent=2), encoding="utf-8")
    docs = root / "docs" / "sprint"
    docs.mkdir(parents=True, exist_ok=True)
    attempts_path = docs / "a6-attempts.json"
    attempts_path.write_text(
        json.dumps({"schema": "a6.attempts.synthetic", "attempts": scenario["attempts"]}, indent=2)
        + "\n",
        encoding="utf-8",
    )
    runs_path = docs / "a6-retry-runs.json"
    runs_path.write_text(
        json.dumps(
            {
                "schema": "a6.retry-runs.v1",
                "scope": "synthetic",
                "attempts_sha256": handoff_sha256(attempts_path),
                "runs": scenario["rows"],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return runs_path, attempts_path


def null_rejection_rate(replicates: int = NULL_REPLICATES) -> tuple[int, int]:
    rejected = 0
    for index in range(replicates):
        eligible, _ = prepare(simulate(0.0, SEED * 1000 + index)["rows"])
        stats = _stats(eligible)
        if stats["p"] < 0.05:
            rejected += 1
    return rejected, replicates


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path(".tmp/a6-synthetic"))
    parser.add_argument("--null-replicates", type=int, default=NULL_REPLICATES)
    args = parser.parse_args()
    summary = []
    for name, effect in SCENARIOS:
        root = args.out / name
        scenario = simulate(effect, SEED + round(effect * 100))
        runs_path, attempts_path = write_scenario(root, scenario)
        report = render_report(
            load_runs(runs_path),
            load_attempts(attempts_path),
            root,
            runs_sha=handoff_sha256(runs_path),
            attempts_sha=handoff_sha256(attempts_path),
        )
        (root / "report.md").write_text(report, encoding="utf-8")
        eligible, _ = prepare(scenario["rows"])
        stats = _stats(eligible)
        summary.append({"name": name, "effect": effect, **stats})
        print(root / "report.md")
    rejected, total = null_rejection_rate(args.null_replicates)
    (args.out / "summary.json").write_text(
        json.dumps(
            {"scenarios": summary, "null_rejected": rejected, "null_replicates": total}, indent=2
        ),
        encoding="utf-8",
    )
    for item in summary:
        print(
            f"{item['name']}: n={item['n']} mean={item['mean']:.4f} p={item['p']:.4f} "
            f"ci=[{item['low']:.4f}, {item['high']:.4f}] within_{ESTIMATE_TOLERANCE}="
            f"{abs(item['mean'] - item['effect']) <= ESTIMATE_TOLERANCE}"
        )
    print(f"null rejections: {rejected}/{total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
