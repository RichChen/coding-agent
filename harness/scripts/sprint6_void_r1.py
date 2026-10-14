#!/usr/bin/env python3
"""6B-FIX G6: move every B0 run made before freeze revision 2 out of runs/a5-main/. Move only, never delete."""
from __future__ import annotations

import json
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_a5_main import image_python  # noqa: E402
from src.eval.tool_errors import harness_tool_errors, tool_schemas  # noqa: E402

SOURCE = ROOT / "runs" / "a5-main"
DEST = ROOT / "runs" / "a5-main-void" / "r1-tool-py36"
RULE = "修订 2 之前的全部 B0 运行，不论结果"


def run_rows(root: Path) -> list[dict]:
    schemas = tool_schemas()
    rows = []
    for summary_path in sorted(root.glob("*/b0/r*/summary.json")):
        run = summary_path.parent
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        events_path = run / "events.jsonl"
        events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines() if line.strip()] if events_path.is_file() else []
        clean = json.loads((ROOT / "docs" / "sprint" / "clean-images" / (summary["task_id"] + ".json")).read_text(encoding="utf-8"))
        rows.append({
            "run": summary["task_id"] + "/b0/" + run.name,
            "python": image_python(clean),
            "harness_tool_errors": len(harness_tool_errors(events, schemas)),
            "solved": bool(summary.get("solved")),
            "status": summary.get("status"),
            "cost_cny": str(summary.get("cost_cny") or "0"),
        })
    return rows


def readme(rows: list[dict]) -> str:
    total = sum((Decimal(row["cost_cny"]) for row in rows), Decimal("0"))
    lines = [
        "# 作废的 B0 运行（r1-tool-py36）",
        "",
        "## 原因",
        "",
        "B0 第一次全量运行时，容器里的文件工具（read_file、list_dir、search_replace、edit_file）和 search_code",
        "调用了 `Path.is_relative_to`（Python 3.9 才有）。在 Python 3.6 和 3.8 的镜像里，这些工具每次调用都以",
        "`AttributeError` 失败，agent 实际上只剩 run_command 可用。这些运行不能代表 B0 的真实能力。",
        "另外，这一轮还有两次候选快照的 Docker 控制错误被当成空补丁评分（delta_lost），",
        "一次 grader 在测试开始之前超时被当成 invalid_env。修订 2 已经修复这些问题（见 docs/sprint/A5-MAIN-FREEZE.md 修订 2）。",
        "",
        "## 规则",
        "",
        "**" + RULE + "**。这些运行只移动到这里，不删除，也不计入 A5-main 的花费上限和结果。",
        "",
        "## 运行列表",
        "",
        "| 运行 | 镜像 Python | harness_tool_errors | solved | status | 花费 (CNY) |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(f"| {row['run']} | {row['python']} | {row['harness_tool_errors']} | {row['solved']} | {row['status']} | {row['cost_cny']} |")
    lines += [
        "",
        f"共 {len(rows)} 次运行；harness_tool_errors 合计 {sum(row['harness_tool_errors'] for row in rows)}；"
        f"解出 {sum(1 for row in rows if row['solved'])} 次；花费合计 {total} CNY。",
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
    (DEST / "README.md").write_text(readme(rows), encoding="utf-8")
    (DEST / "void-runs.json").write_text(json.dumps({"rule": RULE, "runs": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    left = list(SOURCE.iterdir())
    print(json.dumps({"moved_runs": len(rows), "left_in_source": len(left), "destination": str(DEST.relative_to(ROOT))}))


if __name__ == "__main__":
    main()
