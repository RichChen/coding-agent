"""Leave-one-out retrieval on the v4 source tasks. Does not touch pilot targets."""

from __future__ import annotations

import asyncio
from pathlib import Path

from reposkill_agent.memory.card_plugin import MemoryCardPlugin, rank_cards
from reposkill_agent.memory.cards import load_memory_cards

ROOT = Path(__file__).resolve().parents[1]
CARDS = ROOT / "benchmarks" / "a5" / "memory-cards-v4.jsonl"
OUT = ROOT / "docs" / "sprint" / "DEV-LOO-SELECTION.md"
EVIDENCE = Path("D:/crq/src/coding-harness/docs/upgrade/evidence")


def original_root(source_id: str) -> Path | None:
    matches = sorted(EVIDENCE.glob(f"A5-harness-preflight-*/tasks/{source_id}/staging/original"))
    return matches[-1] if matches else None


def main() -> None:
    cards = load_memory_cards(CARDS)
    lines = [
        "# dev 留一法选择（v4 interim）",
        "",
        "每道源题只在其余卡片上检索。目标树是 harness receipt 旁的 `staging/original`。",
        "没有改检索规则。`scikit-learn-10508` 还没有卡片。",
        "",
    ]
    for card in cards:
        others = tuple(item for item in cards if item.source_id != card.source_id)
        root = original_root(card.source_id)
        ranked = rank_cards(others, repo=card.repo, issue=card.issue_summary)
        lines.append(f"## {card.source_id}")
        lines.append("")
        lines.append(f"- tree: `{root}`" if root else "- tree: 缺少 staging/original")
        if ranked:
            lines.append("- rank: " + "；".join(f"{item.source_id.split('__')[-1]} {score:.1f}" for score, item in ranked))
        else:
            lines.append("- rank: 无")
        for variant in ("B1", "B2", "B3"):
            if root is None:
                lines.append(f"- {variant}: 未跑")
                continue
            result = asyncio.run(
                MemoryCardPlugin(
                    variant=variant,
                    cards=others,
                    repo=card.repo,
                    issue=card.issue_summary,
                    target_root=root,
                ).decide({})
            )
            items = result["events"][0]["items"]
            status = result["events"][0]["status"]
            if not items:
                lines.append(f"- {variant}: {status}")
                continue
            rendered = []
            for item in items:
                short = item["source_id"].split("__")[-1]
                rendered.append(f"{short} {item['status']} {item['score']} {item['reason'][:80]}")
            lines.append(f"- {variant}: {status}；" + "；".join(rendered))
        lines.append("")
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
