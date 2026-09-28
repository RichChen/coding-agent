import json
from pathlib import Path

import pytest

from reposkill_agent.memory.cards import RENDER_LIMIT, render_card
from reposkill_agent.memory.cards_v3 import NONE_RUN, build_memory_cards_v3
from reposkill_agent.memory.legacy_env import is_legacy_env_artifact

SNAPSHOT = Path(
    "D:/crq/src/coding-harness/docs/upgrade/evidence/"
    "A5-real240-77-harness-preflight/memory-snapshot.jsonl"
)
VERIFICATION = Path("D:/crq/src/coding-harness/docs/sprint/memory-source-verification.json")
TARGETS = Path("configs/a5/pilot20-harness-consumption-manifest.json")
PRIVATE = Path("benchmarks/a5/pilot20-source-v1/private/test.parquet")


def test_v3_fields_and_render_budget(tmp_path):
    source = tmp_path / "src"
    run = source / "run"
    (run / "session" / "artifacts").mkdir(parents=True)
    (run / "events.jsonl").write_text(
        "\n".join(
            json.dumps(event)
            for event in (
                {"event_type": "tool.intent", "payload": {"name": "read_file", "arguments": {"path": "pkg/a.py", "offset": 3, "limit": 4}}},
                {"event_type": "tool.intent", "payload": {"name": "run_command", "arguments": {"command": "python -m pytest tests/test_a.py -q"}}},
                {"event_type": "tool.intent", "payload": {"name": "run_command", "arguments": {"command": "pip install six && find / -name six"}}},
                {"event_type": "tool.intent", "payload": {"name": "search_replace", "arguments": {"path": "pkg/a.py", "search": "def parse(text):\n    return text", "replace": "def parse(text):\n    return text or ''"}}},
                {"event_type": "state.saved", "payload": {"messages": [{"role": "assistant", "content": "The bug is caused by parse returning None on empty input. Tests live under tests/."}]}},
            )
        )
        + "\n",
        encoding="utf-8",
    )
    (source / "public-trajectory.json").write_text(
        json.dumps({"issue_summary": "Empty input crashes parse.", "public_evidence": [], "actions": [], "public_verification": "", "failure_notes": []}),
        encoding="utf-8",
    )
    (source / "candidate-delta.json").write_text(
        json.dumps({"changed": {"pkg/a.py": {"content": "def parse(text):\n    return text or ''\n"}}}),
        encoding="utf-8",
    )
    snapshot = tmp_path / "snap.jsonl"
    snapshot.write_text(
        json.dumps({"source_id": "example__example-1", "source_dir": str(source), "created_at": "2020-01-01T00:00:00+00:00", "bindings": {"repo": "example/example", "base_revision": "abc123def456"}})
        + "\n",
        encoding="utf-8",
    )
    card = build_memory_cards_v3(snapshot, tmp_path / "missing.json")[0]
    assert card.relevant_files[0].startswith("pkg/a.py")
    assert card.test_commands[0].startswith("python -m pytest")
    assert all(not is_legacy_env_artifact(command) for command in card.test_commands)
    assert "parse" in card.fix_approach
    assert "none recorded" not in render_card(card)
    assert len(render_card(card).encode("utf-8")) <= RENDER_LIMIT
    assert card.verification_status == "unverified"
    assert card.distillation == "rule"


def test_missing_test_command_is_explicit(tmp_path):
    source = tmp_path / "src"
    (source / "run" / "session" / "artifacts").mkdir(parents=True)
    (source / "run" / "events.jsonl").write_text(
        json.dumps({"event_type": "tool.intent", "payload": {"name": "run_command", "arguments": {"command": "git status"}}}) + "\n",
        encoding="utf-8",
    )
    (source / "public-trajectory.json").write_text(
        json.dumps({"issue_summary": "A bug.", "public_evidence": [], "actions": [], "public_verification": "", "failure_notes": []}),
        encoding="utf-8",
    )
    snapshot = tmp_path / "snap.jsonl"
    snapshot.write_text(
        json.dumps({"source_id": "example__example-2", "source_dir": str(source), "created_at": "2020-01-01T00:00:00+00:00", "bindings": {"repo": "example/example", "base_revision": "abc123def456"}})
        + "\n",
        encoding="utf-8",
    )
    card = build_memory_cards_v3(snapshot, tmp_path / "missing.json")[0]
    assert card.test_commands == (NONE_RUN,)


@pytest.mark.skipif(not SNAPSHOT.is_file(), reason="harness snapshot not on this machine")
def test_v3_missing_created_at_is_an_error(tmp_path):
    source = tmp_path / "src"
    source.mkdir()
    (source / "run" / "session" / "artifacts").mkdir(parents=True)
    (source / "run" / "events.jsonl").write_text("", encoding="utf-8")
    (source / "public-trajectory.json").write_text(
        json.dumps({"issue_summary": "A bug.", "public_evidence": [], "actions": [], "public_verification": "", "failure_notes": []}),
        encoding="utf-8",
    )
    snapshot = tmp_path / "snap.jsonl"
    snapshot.write_text(
        json.dumps({"source_id": "example__example-3", "source_dir": str(source), "bindings": {"repo": "example/example", "base_revision": "abc123def456"}})
        + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="created_at_missing"):
        build_memory_cards_v3(snapshot, tmp_path / "missing.json")


def test_real_v3_cards_stay_inside_budget_and_exclude_targets(tmp_path):
    pool = {
        item["canonical_id"]: item
        for item in json.loads(Path("configs/a5/canonical-handoff.json").read_text(encoding="utf-8"))["memory_build_source_pool"]
    }
    lines = []
    for line in SNAPSHOT.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        created_at = (pool[row["source_id"]].get("provenance") or {}).get("historical_pr_created_at")
        assert created_at, row["source_id"]
        row["created_at"] = created_at
        lines.append(json.dumps(row))
    snapshot = tmp_path / "snap.jsonl"
    snapshot.write_text("\n".join(lines) + "\n", encoding="utf-8")
    cards = build_memory_cards_v3(snapshot, VERIFICATION)
    assert len(cards) == 11
    with_tests = 0
    for card in cards:
        text = render_card(card)
        assert len(text.encode("utf-8")) <= RENDER_LIMIT
        assert "none recorded" not in text
        assert text.startswith("[historical attempt")
        if card.test_commands != (NONE_RUN,):
            with_tests += 1
    assert with_tests >= 2
    targets = json.loads(TARGETS.read_text(encoding="utf-8"))["targets"]
    blob = "\n".join(render_card(card) for card in cards)
    assert {card.source_id for card in cards}.isdisjoint(targets)
    for target in targets:
        assert target not in blob
    if not PRIVATE.is_file():
        return
    import pyarrow.parquet as pq

    table = pq.read_table(PRIVATE, columns=["instance_id", "patch", "test_patch", "FAIL_TO_PASS"])
    rows = {row["instance_id"]: row for row in table.to_pylist()}
    for target in targets:
        row = rows[target]
        for column in ("patch", "test_patch", "FAIL_TO_PASS"):
            for line in str(row[column]).splitlines():
                if not line.startswith("+") or line.startswith("+++"):
                    continue
                snippet = line[1:].strip()
                if len(snippet) >= 80:
                    assert snippet not in blob, target
                    break
