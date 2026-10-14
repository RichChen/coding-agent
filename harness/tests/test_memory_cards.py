"""Leave-one-out memory cards. No model calls."""
import asyncio
from pathlib import Path

from src.policy.reposkill import load_adapter, source_digest
from scripts.run_swe_task import leave_one_out

AGENT = Path(r"D:\crq\src\coding-agent")
CARDS = AGENT / "benchmarks/a5/memory-cards-v5.jsonl"
TASK = "django__django-10914"


def _cards():
    load_adapter(AGENT, source_digest(AGENT))
    from reposkill_agent.memory.card_plugin import MemoryCardPlugin
    from reposkill_agent.memory.cards import load_memory_cards
    return MemoryCardPlugin, load_memory_cards(CARDS)


def test_leave_one_out_drops_the_current_task():
    _, cards = _cards()
    assert any(card.source_id == TASK for card in cards)
    kept, dropped = leave_one_out(cards, TASK)
    assert dropped == [TASK]
    assert all(card.source_id != TASK for card in kept)


def test_b0_injects_nothing():
    plugin_cls, cards = _cards()
    kept, _ = leave_one_out(cards, TASK)
    plugin = plugin_cls(variant="B0", cards=kept, repo="django/django", issue="issue", target_root=AGENT)
    decision = asyncio.run(plugin.decide({}))
    assert decision["candidates"] == []


def test_b2_prompt_omits_own_card_and_respects_budget():
    plugin_cls, cards = _cards()
    kept, _ = leave_one_out(cards, TASK)
    plugin = plugin_cls(
        variant="B2", cards=kept, repo="django/django", issue="queryset",
        target_root=AGENT, max_bytes=4096,
    )
    decision = asyncio.run(plugin.decide({}))
    ids = [item["id"] for item in decision["candidates"]]
    assert TASK not in ids
    blob = []
    for item in decision["candidates"]:
        assert len(item["text"].encode("utf-8")) <= 4096
        rendered = f"[Untrusted policy candidate; source={item['source']}]\n{item['text']}"
        assert item["text"] in rendered
        blob.append(rendered)
    assert sum(len(part.encode("utf-8")) for part in blob) <= 4096
