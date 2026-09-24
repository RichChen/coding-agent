import json
from pathlib import Path

import pytest

from reposkill_agent.memory.cards import (
    RENDER_LIMIT,
    build_memory_cards,
    load_memory_cards,
    render_card,
    write_memory_cards,
)
from reposkill_agent.memory.records import MemoryCard

SNAPSHOT = Path(
    "D:/crq/src/coding-harness/docs/upgrade/evidence/"
    "A5-real240-77-harness-preflight/memory-snapshot.jsonl"
)
VERIFICATION = Path("D:/crq/src/coding-harness/docs/sprint/memory-source-verification.json")
TARGETS = Path("configs/a5/pilot20-harness-consumption-manifest.json")
PRIVATE = Path("benchmarks/a5/pilot20-source-v1/private/test.parquet")
CARDS = Path("benchmarks/a5/memory-cards-v2.jsonl")

REQUIRED = (
    "repo",
    "version",
    "source_id",
    "issue_summary",
    "relevant_files",
    "test_commands",
    "env_pitfalls",
    "fix_approach",
    "verification_status",
    "dependencies",
)


def _fixture_snapshot(tmp_path: Path) -> Path:
    source = tmp_path / "src"
    source.mkdir()
    (source / "public-trajectory.json").write_text(
        json.dumps(
            {
                "issue_summary": "Fix parse so empty input does not crash. Tests should still pass.",
                "public_evidence": [
                    "python -m pytest tests/test_parser.py -q",
                    "[stderr]\n/bin/sh: 1: git: not found\n[exit_code=127 status=failed]",
                ],
                "actions": [
                    "read_file:pkg/parser.py",
                    "search_replace:pkg/parser.py",
                    "run_command",
                ],
                "public_verification": "smoke:pass",
                "failure_notes": ["ModuleNotFoundError: No module named helper"],
            }
        ),
        encoding="utf-8",
    )
    (source / "candidate-delta.json").write_text(
        json.dumps(
            {
                "changed": {
                    "pkg/parser.py": {
                        "content": "def parse(text):\n    return text\n",
                        "metadata": {"kind": "file"},
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    snapshot = tmp_path / "snap.jsonl"
    snapshot.write_text(
        json.dumps(
            {
                "source_id": "example__example-1",
                "source_dir": str(source),
                "bindings": {
                    "repo": "example/example",
                    "base_revision": "abc123def456",
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return snapshot


def test_rule_card_has_required_fields_and_short_render(tmp_path):
    cards = build_memory_cards(_fixture_snapshot(tmp_path), tmp_path / "missing.json")
    card = cards[0]
    dumped = card.model_dump()
    for name in REQUIRED:
        assert name in dumped
    assert card.verification_status == "unverified"
    assert card.distillation == "rule"
    assert card.relevant_files[0] == "pkg/parser.py"
    assert card.dependencies[0].symbols == ("parse",)
    assert any("pytest" in command for command in card.test_commands)
    assert card.env_pitfalls
    text = render_card(card)
    assert text.startswith("[historical attempt")
    assert "status=unverified" in text
    assert len(text.encode("utf-8")) <= RENDER_LIMIT
    assert "def parse" not in text


def test_round_trip(tmp_path):
    cards = build_memory_cards(_fixture_snapshot(tmp_path), tmp_path / "nope.json")
    path = tmp_path / "memory-cards-v2.jsonl"
    write_memory_cards(cards, path)
    loaded = load_memory_cards(path)
    assert loaded == cards
    assert isinstance(loaded[0], MemoryCard)


@pytest.mark.skipif(not SNAPSHOT.is_file(), reason="harness snapshot not on this machine")
def test_real_cards_exclude_pilot_targets_and_gold():
    cards = build_memory_cards(SNAPSHOT, VERIFICATION)
    assert len(cards) == 11
    blob = "\n".join(render_card(card) + "\n" + card.issue_summary for card in cards)
    targets = json.loads(TARGETS.read_text(encoding="utf-8"))["targets"]
    assert len(targets) == 20
    sources = {card.source_id for card in cards}
    assert sources.isdisjoint(targets)
    for target in targets:
        assert target not in blob
    if not PRIVATE.is_file():
        return
    import pyarrow.parquet as pq

    table = pq.read_table(PRIVATE, columns=["instance_id", "patch", "test_patch", "FAIL_TO_PASS", "PASS_TO_PASS"])
    rows = {row["instance_id"]: row for row in table.to_pylist()}
    for target in targets:
        row = rows[target]
        for column in ("patch", "test_patch", "FAIL_TO_PASS", "PASS_TO_PASS"):
            for line in str(row[column]).splitlines():
                if not line.startswith("+") or line.startswith("+++"):
                    continue
                snippet = line[1:].strip()
                if len(snippet) < 80:
                    continue
                assert snippet not in blob, target
