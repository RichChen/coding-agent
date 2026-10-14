"""Check the zero-model mock B0 walk of the whole pool against the empty-patch calibration."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.run_a5_main import accepted_tasks, load_targets  # noqa: E402


def check_task(task_id: str, run: Path, calibration: dict) -> dict:
    row = {"task_id": task_id, "problems": []}
    problems = row["problems"]
    summary_path = run / "summary.json"
    if not summary_path.is_file():
        problems.append("no summary.json")
        return row
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    row["status"] = summary.get("status")
    if summary.get("mock") is not True or summary.get("cost_cny") not in ("0", "0.000"):
        problems.append("not a zero-cost mock run")
    if summary.get("status") in ("answer_isolation_failed", "infra_error"):
        problems.append("status " + str(summary.get("status")))
        return row
    ids = summary.get("grader_ids") or {}
    if ids.get("reason") or summary.get("grader_status") == "invalid_env":
        problems.append("grader crashed: " + str(ids.get("reason")))
        return row
    grader = json.loads((run / "grader-result.json").read_text(encoding="utf-8"))
    cases = grader.get("cases") or []
    missing = sum(1 for case in cases if case.get("outcome") == "missing")
    excluded = list(calibration.get("p2p_excluded") or [])
    empty_f2p = calibration["empty_f2p"]
    empty_p2p = calibration["empty_p2p"]
    row.update(
        f2p=[grader.get("f2p_passed"), grader.get("f2p_total")],
        p2p=[grader.get("p2p_passed"), grader.get("p2p_total")],
        empty_f2p=empty_f2p,
        empty_p2p=empty_p2p,
        p2p_excluded=len(excluded),
        missing=missing,
    )
    if missing:
        problems.append(str(missing) + " missing ids")
    # Calibration accepts a task when the empty patch leaves at least one F2P failing, not all of them.
    if row["f2p"] != list(empty_f2p) or not row["f2p"][0] < row["f2p"][1]:
        problems.append("F2P " + json.dumps(row["f2p"]) + " vs empty_f2p " + json.dumps(empty_f2p))
    if summary.get("solved") is not False:
        problems.append("empty patch counted as solved")
    expected_p2p = [empty_p2p[0], empty_p2p[1] - len(excluded)]
    if row["p2p"] != expected_p2p:
        problems.append("P2P " + json.dumps(row["p2p"]) + " vs expected " + json.dumps(expected_p2p))
    graded = {case.get("nodeid") for case in cases}
    leaked = [node for node in excluded if node in graded]
    if leaked:
        problems.append("p2p_excluded ids reached the grader: " + json.dumps(leaked))
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-root", default="runs/a5-main-mock-e2e")
    parser.add_argument("--destination", default="runs/a5-main-logs/mock-e2e-check.json")
    args = parser.parse_args()
    out_root = ROOT / args.out_root
    rows = []
    for task in accepted_tasks(load_targets()):
        calibration = json.loads((ROOT / "docs" / "sprint" / "main-calibration" / (task["id"] + ".json")).read_text(encoding="utf-8"))
        row = check_task(task["id"], out_root / task["id"] / "b0" / "r1", calibration)
        rows.append(row)
        if row["problems"]:
            print(task["id"], "; ".join(row["problems"]), flush=True)
    report = {"passed": sum(1 for row in rows if not row["problems"]), "total": len(rows), "tasks": rows}
    destination = ROOT / args.destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("mock e2e", report["passed"], "of", report["total"], "consistent", flush=True)
    if report["passed"] != report["total"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
