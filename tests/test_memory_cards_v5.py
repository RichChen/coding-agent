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
    manifest_path = Path("benchmarks/a5/memory-cards-v5.manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["status"] == "final"
    assert manifest["build_inputs"]["handoff_schema"] == "sprint5.memory-source-runs.v2"
    assert manifest["build_inputs"]["memory_source_runs_sha256"]
    assert manifest["build_inputs"]["interim_handoff_sha256"] is None


def _events(run_dir: Path) -> None:
    run_dir.mkdir(parents=True)
    line = json.dumps({"event_type": "state.saved", "payload": {"messages": []}})
    (run_dir / "events.jsonl").write_text(line + "\n", encoding="utf-8")


def _handoff_run(source_id: str, run_dir: Path, *, solved: bool, repeat: int = 1) -> dict:
    return {
        "source_id": source_id,
        "repo": "django/django",
        "created_at": "2020-01-02T00:00:00Z",
        "repeat": repeat,
        "solved": solved,
        "status": "pass" if solved else "fail",
        "grader_status": "pass" if solved else "fail",
        "summary": str(run_dir / "summary.json"),
        "run_dir": str(run_dir),
        "layout": "sprint",
        "answer_isolation_pass": True,
        "issue_text": "A public bug report.",
        "base_commit": "abc123def456",
    }


def test_two_handoffs_build_and_mock_or_duplicate_ids_are_rejected(tmp_path):
    from reposkill_agent.memory.cards_v5 import build_cards_from_handoffs, published_sha256

    dev_run = tmp_path / "dev-run"
    pool_run = tmp_path / "pool-run"
    _events(dev_run)
    _events(pool_run)
    dev = {
        "schema": "sprint5.memory-source-runs.v2",
        "scope": "dev",
        "runs": [_handoff_run("django__django-90001", dev_run, solved=True)],
    }
    pool_body = _handoff_run("django__django-90002", pool_run, solved=True)
    pool_body.pop("run_dir")
    pool = {"schema": "sprint6.main-b0-runs.v1", "scope": "pool", "runs": [pool_body]}
    dev_path = tmp_path / "dev.json"
    pool_path = tmp_path / "pool.json"
    dev_path.write_text(json.dumps(dev), encoding="utf-8")
    pool_path.write_text(json.dumps(pool), encoding="utf-8")
    cards, status, handoffs = build_cards_from_handoffs(
        [dev_path, pool_path], canonical_path=CANONICAL, path_base=Path(".")
    )
    assert status == "final"
    assert [card.source_id for card in cards] == ["django__django-90001", "django__django-90002"]
    assert [item["sha256"] for item in handoffs] == [
        published_sha256(dev_path),
        published_sha256(pool_path),
    ]
    mock = tmp_path / "mock.json"
    mock.write_text(json.dumps({**pool, "scope": "step7-mock"}), encoding="utf-8")
    with pytest.raises(ValueError, match="mock_handoff_rejected"):
        build_cards_from_handoffs([dev_path, mock], canonical_path=CANONICAL, path_base=Path("."))
    dup = tmp_path / "dup.json"
    dup.write_text(
        json.dumps({**pool, "runs": [_handoff_run("django__django-90001", pool_run, solved=True)]}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate_source_id"):
        build_cards_from_handoffs([dev_path, dup], canonical_path=CANONICAL, path_base=Path("."))
