"""Offline time-ordered selection for the 14 dev cards. Does not change retrieval."""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path

from reposkill_agent.memory.card_plugin import MemoryCardPlugin, rank_cards
from reposkill_agent.memory.cards import load_memory_cards

ROOT = Path(__file__).resolve().parents[1]
CARDS = ROOT / "benchmarks" / "a5" / "memory-cards-v5.jsonl"
OUT = ROOT / "docs" / "sprint" / "DEV-TIME-SELECTION.md"
EVIDENCE = Path("D:/crq/src/coding-harness/docs/upgrade/evidence")


def original_root(source_id: str) -> Path | None:
    matches = sorted(EVIDENCE.glob(f"A5-harness-preflight-*/tasks/{source_id}/staging/original"))
    return matches[-1] if matches else None


def _when(value: str) -> datetime:
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    return datetime.fromisoformat(text)


def main() -> None:
    cards = load_memory_cards(CARDS)
    lines = [
        "# dev 按时间留一法（v5 interim）",
        "",
        "可注入的卡必须同仓库、created_at 更早、不是本题，并且是 validated_fix。",
        "检索仍是原来的 BM25，min_score 仍是 1.0。没有改规则。",
        "",
    ]
    for card in cards:
        earlier = tuple(
            item
            for item in cards
            if item.source_id != card.source_id
            and item.repo == card.repo
            and item.verification_status == "validated_fix"
            and _when(item.created_at) < _when(card.created_at)
        )
        root = original_root(card.source_id)
        lines.append(f"## {card.source_id}")
        lines.append("")
        lines.append(f"- created_at: {card.created_at}")
        if not earlier:
            lines.append("- 可注入：无")
            lines.append("")
            continue
        ranked = rank_cards(earlier, repo=card.repo, issue=card.issue_summary)
        if ranked:
            lines.append("- 分数：" + "；".join(f"{item.source_id.split('__')[-1]} {score:.1f}" for score, item in ranked))
        else:
            lines.append("- 分数：都低于 min_score")
        if root is None:
            lines.append("- 实际注入：缺少 staging/original")
        else:
            result = asyncio.run(
                MemoryCardPlugin(
                    variant="B2",
                    cards=earlier,
                    repo=card.repo,
                    issue=card.issue_summary,
                    target_root=root,
                ).decide({})
            )
            chosen = [item["id"].split("__")[-1] for item in result["candidates"]]
            lines.append("- 实际注入：" + ("、".join(chosen) if chosen else result["events"][0]["status"]))
        lines.append("")
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
