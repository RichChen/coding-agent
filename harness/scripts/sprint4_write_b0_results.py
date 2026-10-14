"""Write the B0 v2 table and the memory-source handoff. No model calls."""
import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT))
groups = defaultdict(list)
isolation_fail = 0
for summary_path in sorted((ROOT / "runs/sprint4-b0-v2").glob("*/*/summary.json")):
    if summary_path.parent.name not in {"r1", "r2", "r3"}:
        continue
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if summary.get("status") == "infra_error":
        continue
    grader = json.loads((summary_path.parent / "grader-result.json").read_text(encoding="utf-8"))
    if summary.get("answer_isolation_pass") is not True:
        isolation_fail += 1
    groups[summary["task_id"]].append({
        "repeat": int(summary_path.parent.name[1:]),
        "solved": bool(summary["solved"]),
        "cost": Decimal(str(summary["cost_cny"])),
        "calls": summary["model_calls"],
        "stop": summary["stop_reason"],
        "grader": grader.get("status"),
        "f2p_passed": grader.get("f2p_passed") or 0,
        "f2p_total": grader.get("f2p_total") or 0,
        "p2p_passed": grader.get("p2p_passed") or 0,
        "p2p_total": grader.get("p2p_total") or 0,
        "tests": (grader.get("touched") or {}).get("test_files_touched") or grader.get("test_files_touched") or [],
        "run_dir": summary_path.parent.resolve().as_posix(),
        "digest": summary.get("clean_image_digest"),
        "isolation": summary.get("answer_isolation_pass"),
    })

v1 = {
    "django__django-10914": "3/3", "django__django-10924": "3/3", "django__django-11039": "3/3",
    "pytest-dev__pytest-5103": "1/3", "pytest-dev__pytest-5227": "3/3",
    "sympy__sympy-11400": "3/3", "sympy__sympy-11870": "0/3", "sympy__sympy-11897": "3/3", "sympy__sympy-12171": "1/3",
    "scikit-learn__scikit-learn-10297": "3/3", "scikit-learn__scikit-learn-10949": "0/3",
    "scikit-learn__scikit-learn-11281": "3/3", "scikit-learn__scikit-learn-10508": "3/3",
    "scikit-learn__scikit-learn-11040": "3/3",
}
lines = [
    "# B0 v2 三次重复",
    "",
    "profile 是 `b0-v2`。镜像是 clean image。v1 是测试可见条件下的历史结果，不并进这个分母。",
    "",
    "| 题 | v2 | v1 | 平均花费 | 停止原因 |",
    "| --- | --- | --- | --- | --- |",
]
solved_runs = 0
handoff = []
spent = Decimal("0")
for task in sorted(groups):
    rows = sorted(groups[task], key=lambda item: item["repeat"])
    wins = sum(1 for item in rows if item["solved"])
    solved_runs += wins
    spent += sum(item["cost"] for item in rows)
    cost = sum(item["cost"] for item in rows) / len(rows)
    stops = ", ".join(item["stop"] for item in rows)
    short = task.split("__")[-1]
    lines.append(f"| {short} | {wins}/3 | {v1.get(task, '-')} | {cost:.3f} | {stops} |")
    for item in rows:
        handoff.append({
            "source_id": task,
            "repeat": item["repeat"],
            "run_dir": item["run_dir"],
            "layout": "sprint",
            "solved": item["solved"],
            "grader_status": item["grader"],
            "f2p_passed": item["f2p_passed"],
            "f2p_total": item["f2p_total"],
            "p2p_passed": item["p2p_passed"],
            "p2p_total": item["p2p_total"],
            "answer_isolation_pass": item["isolation"],
            "clean_image_digest": item["digest"],
            "test_files_touched": item["tests"],
        })
lines.append("")
lines.append(f"解出 {solved_runs}/{len(handoff)}。花费 {spent} CNY。隔离失败 {isolation_fail} 次。")
(ROOT / "docs/sprint/B0-V2-RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
document = {
    "schema": "sprint4.memory-source-runs.v1",
    "profile_tag": "b0-v2",
    "harness_commit": "9f58c36ffc1108b7746d1509385bf7e3a430e7dc",
    "label_origin": "source_task_swebench_tests",
    "condition": "clean_image_test_patch_hidden",
    "runs": handoff,
}
raw = json.dumps(document, indent=2) + "\n"
path = ROOT / "docs/sprint/memory-source-runs.json"
path.write_text(raw, encoding="utf-8")
from scripts.handoff_sha import handoff_sha256
print(solved_runs, len(handoff), spent, isolation_fail)
print(handoff_sha256(path))
