#!/usr/bin/env python3
"""CHECKPOINT-6a statistics for the B0 runs under runs/a5-main/. No model calls."""
from __future__ import annotations

import json
import sys
from collections import Counter
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_a5_main import accepted_tasks, canary_ids, load_targets, out_root_for  # noqa: E402


def main():
    root = out_root_for(False)
    tasks = accepted_tasks(load_targets())
    canaries = set(canary_ids(tasks).values())
    formal, infra = [], []
    for path in sorted(root.glob("*/b0/r*/summary.json")):
        row = json.loads(path.read_text(encoding="utf-8"))
        row["_slot"] = path.parent.name
        (infra if "." in row["_slot"] or row.get("status") == "infra_error" else formal).append(row)
    repo_of = {task["id"]: task["repo"] for task in tasks}
    by_repo, by_task = {}, {}
    for row in formal:
        repo = repo_of[row["task_id"]]
        bucket = by_repo.setdefault(repo, [0, 0])
        bucket[0] += int(bool(row.get("solved")))
        bucket[1] += 1
        by_task.setdefault(row["task_id"], []).append(int(bool(row.get("solved"))))
    solved = sum(int(bool(row.get("solved"))) for row in formal)
    cost = sum((Decimal(str(row.get("cost_cny") or "0")) for row in formal + infra), Decimal("0"))
    non_canary = [row for row in formal if not (row["_slot"] == "r1" and row["task_id"] in canaries)]
    report = {
        "formal_runs": len(formal),
        "solved": solved,
        "solve_rate": round(solved / len(formal), 4) if formal else None,
        "by_repo": {repo: {"solved": s, "runs": n, "rate": round(s / n, 4)} for repo, (s, n) in sorted(by_repo.items())},
        "k_of_3": dict(sorted(Counter(str(sum(v)) + "/" + str(len(v)) for v in by_task.values()).items())),
        "tasks_with_fewer_than_3": sorted(task for task, v in by_task.items() if len(v) != 3),
        "status": dict(Counter(row.get("status") for row in formal)),
        "stop_reason": dict(Counter(str(row.get("stop_reason")) for row in formal)),
        "infra": [{"task_id": row["task_id"], "slot": row["_slot"], "infra_reason": row.get("infra_reason")} for row in infra],
        "docker_retries": [dict(task_id=row["task_id"], slot=row["_slot"], **retry) for row in formal + infra for retry in row.get("docker_retries") or []],
        "harness_tool_errors": sum(row.get("harness_tool_errors") or 0 for row in formal + infra),
        "missing_runs": [row["task_id"] + "/" + row["_slot"] for row in formal if (row.get("grader_ids") or {}).get("missing")],
        "grader_candidate_error": [dict(task_id=row["task_id"], slot=row["_slot"], **row["grader_candidate_error"]) for row in formal if row.get("grader_candidate_error")],
        "grader_reason": [row["task_id"] + "/" + row["_slot"] for row in formal if (row.get("grader_ids") or {}).get("reason")],
        "run_error": [dict(task_id=row["task_id"], slot=row["_slot"], run_error=row.get("run_error"), status=row.get("status")) for row in formal if row.get("run_error")],
        "issue_sha_mismatch": [],
        "models": sorted({json.dumps(row.get("model"), sort_keys=True) for row in formal}),
        "cost_cny": str(cost),
        "mean_cost_cny": str((cost / len(formal + infra)).quantize(Decimal("0.001"))) if formal else None,
        "mean_model_calls": round(sum(row.get("model_calls") or 0 for row in formal) / len(formal), 1) if formal else None,
        "changed_runs": sum(1 for row in formal if row.get("changed_files")),
        "non_canary_formal": len(non_canary),
        "non_canary_solved": sum(int(bool(row.get("solved"))) for row in non_canary),
    }
    issues = json.loads((ROOT / "docs/sprint/main-issues.json").read_text(encoding="utf-8"))["tasks"]
    report["issue_sha_mismatch"] = [row["task_id"] + "/" + row["_slot"] for row in formal if row.get("issue_sha256") != issues[row["task_id"]]["issue_sha256"]]
    destination = ROOT / "runs" / "a5-main-logs" / "b0-stats.json"
    destination.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
