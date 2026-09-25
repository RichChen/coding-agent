"""Offline B1/B2/B3 selection for the 20 pilot targets. Report only."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from reposkill_agent.memory.card_plugin import MemoryCardPlugin, rank_cards
from reposkill_agent.memory.cards import load_memory_cards

ROOT = Path(__file__).resolve().parents[1]
CARDS = ROOT / "benchmarks" / "a5" / "memory-cards-v4.jsonl"
CANONICAL = ROOT / "configs" / "a5" / "canonical-handoff.json"
TREES = Path("D:/crq/tmp/a5-targets")
OUT = ROOT / "docs" / "sprint" / "PILOT-SELECTION-V4.md"


def tree_root(source_id: str) -> Path | None:
    base = TREES / source_id
    if not base.is_dir():
        return None
    children = [path for path in base.iterdir() if path.is_dir()]
    if len(children) == 1:
        return children[0]
    return base


def issue_text(task: dict) -> str:
    path = ROOT / task["public_task_path"]
    payload = json.loads(path.read_text(encoding="utf-8"))
    return str(payload.get("issue_text") or payload.get("issue_summary") or "")


def main() -> None:
    cards = load_memory_cards(CARDS)
    tasks = json.loads(CANONICAL.read_text(encoding="utf-8"))["target_tasks"]
    lines = [
        "# pilot 离线选择（v4，只报告）",
        "",
        "规则与第 5 步留一法之后相同，没有再改。目标树来自 `D:/crq/tmp/a5-targets` 里的 `source.tar.gz` 解压结果。",
        "v3 对照摘自 CHECKPOINT-2。",
        "",
        "| 目标题 | v4 排序 | v4 B2 注入 | v4 B3 |",
        "|---|---|---|---|",
    ]
    injected_b3 = 0
    for task in tasks:
        source_id = task["canonical_id"]
        root = tree_root(source_id)
        issue = issue_text(task)
        ranked = rank_cards(cards, repo=task["expected_repo"], issue=issue)
        rank_text = "；".join(f"{card.source_id.split('__')[-1]} {score:.1f}" for score, card in ranked) or "无"
        if root is None:
            lines.append(f"| {source_id.split('__')[-1]} | {rank_text} | 缺源码树 | 缺源码树 |")
            continue
        b2 = asyncio.run(
            MemoryCardPlugin(variant="B2", cards=cards, repo=task["expected_repo"], issue=issue, target_root=root).decide({})
        )
        b3 = asyncio.run(
            MemoryCardPlugin(variant="B3", cards=cards, repo=task["expected_repo"], issue=issue, target_root=root).decide({})
        )
        def brief(result) -> str:
            items = result["events"][0]["items"]
            if not items:
                return result["events"][0]["status"]
            return "；".join(
                f"{item['source_id'].split('__')[-1]} {item['status']}" for item in items
            )
        b3_selected = [item for item in b3["events"][0]["items"] if item["status"] == "selected"]
        if b3_selected:
            injected_b3 += 1
        lines.append(f"| {source_id.split('__')[-1]} | {rank_text} | {brief(b2)} | {brief(b3)} |")
    lines.extend(
        [
            "",
            f"B3 至少注入 1 张卡的目标题：{injected_b3} / {len(tasks)}。",
            "",
            "看完这张表没有改检索或渲染规则。",
            "",
        ]
    )
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(OUT, "b3", injected_b3)


if __name__ == "__main__":
    main()
