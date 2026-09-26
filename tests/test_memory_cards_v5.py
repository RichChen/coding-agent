import json
import sys
from pathlib import Path

import pytest

from reposkill_agent.memory.cards import render_card
from reposkill_agent.memory.cards_v5 import HandoffFieldMissing, runs_with_identity

CANONICAL = Path("configs/a5/canonical-handoff.json")
HANDOFF = Path("D:/crq/src/coding-harness/docs/sprint/memory-source-runs.json")
CARDS = Path("benchmarks/a5/memory-cards-v5.jsonl")


def test_v2_handoff_missing_created_at_fails():
    data = {
        "schema": "sprint5.memory-source-runs.v2",
        "runs": [{"source_id": "django__django-10914", "repo": "django/django"}],
    }
    with pytest.raises(HandoffFieldMissing, match="created_at_missing"):
        runs_with_identity(data, {})


def test_v2_handoff_missing_repo_fails():
    data = {
        "schema": "sprint5.memory-source-runs.v2",
        "runs": [{"source_id": "django__django-10914", "created_at": "2019-01-30T21:13:20+08:00"}],
    }
    with pytest.raises(HandoffFieldMissing, match="repo_missing"):
        runs_with_identity(data, {})


def test_naive_created_at_is_rejected():
    from reposkill_agent.memory.records import MemoryCard

    with pytest.raises(ValueError):
        MemoryCard(
            repo="demo/demo",
            created_at="2020-01-01T00:00:00",
            version="abc123def456",
            source_id="demo-1",
            issue_summary="A bug.",
            fix_approach="Changed parse.",
        )


@pytest.mark.skipif(not CARDS.is_file(), reason="v5 cards are built in the sprint step")
def test_generic_builder_matches_v5_bytes(tmp_path):
    import subprocess

    out = tmp_path / "cards.jsonl"
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/build_memory_cards.py",
            "--handoff",
            str(HANDOFF),
            "--out",
            str(out),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert out.read_bytes().replace(b"\r\n", b"\n") == CARDS.read_bytes().replace(b"\r\n", b"\n")


def test_v5_cards_have_repo_and_created_at_and_do_not_render_created_at():
    from reposkill_agent.memory.cards import load_memory_cards

    cards = load_memory_cards(CARDS)
    assert len(cards) == 14
    for card in cards:
        assert "/" in card.repo
        assert "T" in card.created_at
        assert card.created_at not in render_card(card)
    text = json.loads(CANONICAL.read_text(encoding="utf-8"))
    assert HANDOFF.is_file()
    assert "target_tasks" in text
