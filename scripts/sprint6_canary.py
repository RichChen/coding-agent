#!/usr/bin/env python3
"""6B-FIX canaries: one B0 r1 per image Python version, on the lower-median task by created_at.

select  prints the chosen task ids.
check   checks their r1 summaries and writes runs/a5-main-logs/canary-check.json.
"""
from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_a5_main import (PROFILE, accepted_tasks, calibration_ids, image_python,  # noqa: E402
                                 load_targets, out_root_for)


def clean_record(task_id: str) -> dict:
    return json.loads((ROOT / "docs" / "sprint" / "clean-images" / (task_id + ".json")).read_text(encoding="utf-8"))


def select(tasks) -> dict:
    """Map Python version to the lower-median task by created_at. Versions without tasks are absent."""
    groups = {}
    for task in tasks:
        groups.setdefault(image_python(clean_record(task["id"])), []).append(task)
    chosen = {}
    for version, rows in sorted(groups.items()):
        rows = sorted(rows, key=lambda row: str(row["created_at"]))
        chosen[version] = rows[(len(rows) - 1) // 2]["id"]
    return chosen


def check_summary(task_id: str, summary: dict, ledger: dict | None, excluded: int) -> list[str]:
    problems = []
    if summary.get("mock") is not False:
        problems.append("mock is not false")
    if summary.get("profile") != PROFILE.stem:
        problems.append("profile is " + str(summary.get("profile")))
    if summary.get("answer_isolation_pass") is not True:
        problems.append("answer_isolation_pass is not true")
    recorded = calibration_ids(task_id)
    expected = {"f2p": recorded["f2p"], "p2p": None if recorded["p2p"] is None else recorded["p2p"] - excluded}
    ids = summary.get("grader_ids") or {}
    if {"f2p": ids.get("f2p"), "p2p": ids.get("p2p")} != expected:
        problems.append("grader ids " + json.dumps(ids) + " differ from calibration " + json.dumps(expected))
    if ids.get("missing"):
        problems.append("grader reported missing ids")
    if ids.get("reason"):
        problems.append("grader reason: " + str(ids["reason"])[:200])
    if summary.get("status") == "infra_error":
        problems.append("infra_error: " + str(summary.get("infra_reason")))
    if summary.get("harness_tool_errors") != 0:
        problems.append("harness_tool_errors is " + str(summary.get("harness_tool_errors")))
    cost = Decimal(str(summary.get("cost_cny") or "0"))
    if ledger is None or ledger.get("currency") != "CNY":
        problems.append("no CNY ledger")
    elif Decimal(str(ledger.get("cost_committed") or "0")) != cost or cost <= 0:
        problems.append("summary cost " + str(cost) + " is not the ledger cost " + str(ledger.get("cost_committed")))
    return problems


def check(chosen: dict, out_root: Path) -> dict:
    rows = []
    for version, task_id in chosen.items():
        folder = out_root / task_id / "b0" / "r1"
        summary_path = folder / "summary.json"
        if not summary_path.is_file():
            rows.append({"python": version, "task_id": task_id, "pass": False, "problems": ["no r1 summary"]})
            continue
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        ledger_path = folder / "cny-ledger.json"
        ledger = json.loads(ledger_path.read_text(encoding="utf-8")) if ledger_path.is_file() else None
        calibration = json.loads((ROOT / "docs" / "sprint" / "main-calibration" / (task_id + ".json")).read_text(encoding="utf-8"))
        problems = check_summary(task_id, summary, ledger, len(calibration.get("p2p_excluded") or []))
        rows.append({
            "python": version,
            "task_id": task_id,
            "solved": summary.get("solved"),
            "status": summary.get("status"),
            "model_calls": summary.get("model_calls"),
            "cost_cny": summary.get("cost_cny"),
            "harness_tool_errors": summary.get("harness_tool_errors"),
            "docker_retries": len(summary.get("docker_retries") or []),
            "pass": not problems,
            "problems": problems,
        })
    return {"passed": sum(1 for row in rows if row["pass"]), "total": len(rows), "canaries": rows}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["select", "check"])
    args = parser.parse_args()
    chosen = select(accepted_tasks(load_targets()))
    if args.command == "select":
        print(json.dumps(chosen, indent=2))
        return
    report = check(chosen, out_root_for(False))
    destination = ROOT / "runs" / "a5-main-logs" / "canary-check.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if report["passed"] != report["total"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
