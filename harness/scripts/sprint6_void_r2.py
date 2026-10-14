#!/usr/bin/env python3
"""6C-FIX H7: move every B0 run made before freeze revision 3 out of runs/a5-main/. Move only, never delete."""
from __future__ import annotations

import json
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_a5_main import recorded_user_prompt  # noqa: E402

SOURCE = ROOT / "runs" / "a5-main"
DEST = ROOT / "runs" / "a5-main-void" / "r2-no-issue"
RULE = "修订 3 之前的全部 B0 运行，不论结果"


def placeholder_prompt(run: Path):
    """True if the recorded user prompt ends in the 'Public issue for <id>' placeholder; None without events."""
    events = run / "events.jsonl"
    if not events.is_file():
        return None
    try:
        prompt = recorded_user_prompt(events)
    except SystemExit:
        return None
    return prompt.rsplit("Public issue:\n", 1)[-1].startswith("Public issue for ")


def run_rows(root: Path) -> list[dict]:
    rows = []
    for summary_path in sorted(root.glob("*/b0/r*/summary.json")):
        run = summary_path.parent
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        rows.append({
            "run": summary["task_id"] + "/b0/" + run.name,
            "placeholder_prompt": placeholder_prompt(run),
            "solved": bool(summary.get("solved")),
            "status": summary.get("status"),
            "cost_cny": str(summary.get("cost_cny") or "0"),
        })
    return rows


def readme(rows: list[dict]) -> str:
    total = sum((Decimal(row["cost_cny"]) for row in rows), Decimal("0"))
    lines = [
        "# 作废的 B0 运行（r2-no-issue）",
        "",
        "## 原因",
        "",
        "修订 2 下的 B0 运行里，pool 题的 user prompt 没有 issue 文本，只有 `Public issue for <id>` 占位。",
        "`select_main_targets.py` 只把 instance_id、FAIL_TO_PASS、PASS_TO_PASS、patch、test_patch 存进私有文件，",
        "没有保存 problem_statement；`materialize_runner_task` 读不到时静默回退成占位文本。",
        "agent 在不知道要修什么的情况下运行，这些结果不能代表 B0 的能力。修订 3 已经补齐 issue 文本，",
        "并把这类回退改成报错（见 docs/sprint/A5-MAIN-FREEZE.md 修订 3）。",
        "",
        "## 规则",
        "",
        "**" + RULE + "**。这些运行只移动到这里，不删除，也不计入 A5-main 的花费上限和结果。",
        f"这一轮的花费 {total} CNY 记为作废成本。",
        "",
        "## 运行列表",
        "",
        "| 运行 | prompt 是占位 issue | solved | status | 花费 (CNY) |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(f"| {row['run']} | {row['placeholder_prompt']} | {row['solved']} | {row['status']} | {row['cost_cny']} |")
    lines += [
        "",
        f"共 {len(rows)} 次运行（含 infra 槽位）；解出 {sum(1 for row in rows if row['solved'])} 次；"
        f"prompt 是占位 issue 的 {sum(1 for row in rows if row['placeholder_prompt'])} 次；花费合计 {total} CNY。",
        "",
        "同时移入的还有这一轮的 `b0-report.json`。",
        "",
    ]
    return "\n".join(lines)


def main():
    if DEST.exists():
        raise SystemExit("destination already exists: " + str(DEST))
    rows = run_rows(SOURCE)
    DEST.mkdir(parents=True)
    for item in sorted(SOURCE.iterdir()):
        item.rename(DEST / item.name)
    total = sum((Decimal(row["cost_cny"]) for row in rows), Decimal("0"))
    (DEST / "README.md").write_text(readme(rows), encoding="utf-8")
    (DEST / "void-runs.json").write_text(json.dumps({"rule": RULE, "void_cost_cny": str(total), "runs": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    left = list(SOURCE.iterdir())
    print(json.dumps({"moved_runs": len(rows), "void_cost_cny": str(total), "left_in_source": len(left), "destination": str(DEST.relative_to(ROOT))}))


if __name__ == "__main__":
    main()
