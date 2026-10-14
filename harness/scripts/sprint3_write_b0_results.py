"""Write the B0 v1 results table and the memory-source handoff. No model calls."""
import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
groups = defaultdict(list)
for summary_path in sorted((ROOT / "runs/sprint3-b0").glob("*/*/summary.json")):
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    grader = json.loads((summary_path.parent / "grader-result.json").read_text(encoding="utf-8"))
    groups[summary["task_id"]].append({
        "repeat": int(summary_path.parent.name[1:]),
        "solved": bool(summary["solved"]),
        "cost": Decimal(str(summary["cost_cny"])),
        "calls": summary["model_calls"],
        "first": summary["first_edit_step"],
        "stop": summary["stop_reason"],
        "grader": grader.get("status"),
        "f2p_passed": grader.get("f2p_passed") or 0,
        "f2p_total": grader.get("f2p_total") or 0,
        "p2p_passed": grader.get("p2p_passed") or 0,
        "p2p_total": grader.get("p2p_total") or 0,
        "run_dir": summary_path.parent.resolve().as_posix(),
    })

lines = [
    "# B0 v1 三次重复",
    "",
    "profile 是 `b0-v1`。14 题各跑 3 次，花费 16.173 CNY。没有运行改过测试文件。",
    "",
    "| 题 | 解出 | 平均花费 | 平均调用 | 首次编辑 | 停止原因 | 一致 |",
    "| --- | --- | --- | --- | --- | --- | --- |",
]
solved_runs = consistent_3 = consistent_0 = mixed = 0
handoff = []
for task in sorted(groups):
    rows = sorted(groups[task], key=lambda item: item["repeat"])
    wins = sum(1 for item in rows if item["solved"])
    solved_runs += wins
    if wins == 3:
        consistent_3 += 1
        agreement = "3/3"
    elif wins == 0:
        consistent_0 += 1
        agreement = "0/3"
    else:
        mixed += 1
        agreement = "混合"
    cost = sum(item["cost"] for item in rows) / 3
    calls = sum(item["calls"] for item in rows) / 3
    edits = " / ".join(str(item["first"]) if item["first"] is not None else "-" for item in rows)
    stops = ", ".join(item["stop"] for item in rows)
    short = task.split("__")[-1]
    lines.append(f"| {short} | {wins}/3 | {cost:.3f} | {calls:.1f} | {edits} | {stops} | {agreement} |")
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
        })

lines.extend([
    "",
    f"总体解出 {solved_runs}/42。3/3 的题 {consistent_3} 道，0/3 的题 {consistent_0} 道，混合 {mixed} 道。",
    "",
    "抽查两道解出的运行：django-10914 r1 改的是 `django/conf/global_settings.py` 和 `docs/ref/settings.txt`，没有改测试。sklearn-10297 r1 只改了 `sklearn/linear_model/ridge.py`。42 次运行的 `test_files_touched` 都是空的。",
    "",
])
(ROOT / "docs/sprint/B0-V1-RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
document = {
    "schema": "sprint3.memory-source-runs.v1",
    "profile_tag": "b0-v1",
    "harness_commit": "d40d8dad790b1455e3da8df25e61e2439ff68d85",
    "label_origin": "source_task_swebench_tests",
    "runs": handoff,
}
(ROOT / "docs/sprint/memory-source-runs.json").write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
print(solved_runs, consistent_3, consistent_0, mixed, len(handoff))
