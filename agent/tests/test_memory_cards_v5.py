import json
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


def test_source_hidden_ids_are_scrubbed_from_commands(tmp_path):
    from reposkill_agent.memory.records import MemoryCard
    from scripts.build_memory_cards import hidden_id_hit_counts, scrub_hidden_ids

    node = "tests/test_hidden.py::TestHidden::test_secret_behavior_case"
    root = tmp_path / "harness"
    private = root / "runs" / "sprint5-main-private" / "demo-1.json"
    private.parent.mkdir(parents=True)
    private.write_text(json.dumps({"FAIL_TO_PASS": [node], "PASS_TO_PASS": []}), encoding="utf-8")
    card = MemoryCard(
        repo="demo/demo",
        created_at="2020-01-02T00:00:00Z",
        version="abc123def456",
        source_id="demo-1",
        issue_summary="A public bug.",
        fix_approach="Changed parse.",
        test_commands=(f"pytest {node}",),
        source_run="r1 " + str(tmp_path / "missing-run"),
    )
    assert hidden_id_hit_counts((card,), [root])[0] == 1
    cleaned = scrub_hidden_ids((card,), [root])
    assert node not in cleaned[0].test_commands[0]
    assert hidden_id_hit_counts(cleaned, [root])[0] == 0


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
def test_generic_builder_matches_v5_bytes():
    from reposkill_agent.memory.cards_v5 import build_cards_from_handoff, cards_jsonl

    cards, _status = build_cards_from_handoff(
        HANDOFF, canonical_path=CANONICAL, path_base=Path(".")
    )
    payload = cards_jsonl(cards)
    assert payload.replace(b"\r\n", b"\n") == CARDS.read_bytes().replace(b"\r\n", b"\n")


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
    import hashlib

    issue = "A public bug report."
    digest = hashlib.sha256(issue.encode("utf-8")).hexdigest()
    public = tmp_path / "runs" / "sprint5-main-public" / "django__django-90002.json"
    public.parent.mkdir(parents=True)
    public.write_text(json.dumps({"issue_text": issue}), encoding="utf-8")
    pool_body = _handoff_run("django__django-90002", pool_run, solved=True)
    pool_body["public_task"] = "runs/sprint5-main-public/django__django-90002.json"
    pool_body["issue_sha256"] = digest
    pool = {"schema": "sprint6.main-b0-runs.v2", "scope": "pool", "runs": [pool_body]}
    dev_path = tmp_path / "dev.json"
    pool_path = tmp_path / "docs" / "sprint" / "pool.json"
    pool_path.parent.mkdir(parents=True)
    dev_path.write_text(json.dumps(dev), encoding="utf-8")
    pool_path.write_text(json.dumps(pool), encoding="utf-8")
    cards, status, handoffs, omitted = build_cards_from_handoffs(
        [dev_path, pool_path], canonical_path=CANONICAL, path_base=Path(".")
    )
    assert status == "final"
    assert omitted == ()
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
    dup_run = _handoff_run("django__django-90001", pool_run, solved=True)
    dup_run["public_task"] = pool_body["public_task"]
    dup_run["issue_sha256"] = digest
    dup.write_text(json.dumps({**pool, "runs": [dup_run]}), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate_source_id"):
        build_cards_from_handoffs([dev_path, dup], canonical_path=CANONICAL, path_base=Path("."))
    from reposkill_agent.memory.cards_v5 import load_handoff_document

    old = tmp_path / "v1.json"
    old.write_text(
        json.dumps({"schema": "sprint6.main-b0-runs.v1", "runs": [pool_body]}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="pool_v1_rejected"):
        load_handoff_document(old)
    broken = tmp_path / "docs" / "sprint" / "bad.json"
    bad_run = dict(pool_body)
    bad_run["issue_sha256"] = "0" * 64
    broken.write_text(
        json.dumps({"schema": "sprint6.main-b0-runs.v2", "runs": [bad_run]}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="issue_sha_mismatch"):
        build_cards_from_handoffs([broken], canonical_path=CANONICAL, path_base=Path("."))


def test_unsolved_cards_skip_infra_and_all_infra_is_omitted(tmp_path):
    from reposkill_agent.memory.cards_v5 import build_cards_from_handoffs, manifest_for

    failed_run = tmp_path / "failed"
    _events(failed_run)
    infra_only = _handoff_run("django__django-90004", failed_run, solved=False, repeat=1)
    infra_only["status"] = "infra_error"
    infra_only["grader_status"] = "infra_error"
    earlier_infra = _handoff_run("django__django-90003", failed_run, solved=False, repeat=1)
    earlier_infra["status"] = "infra_error"
    earlier_infra["grader_status"] = "infra_error"
    later_fail = _handoff_run("django__django-90003", failed_run, solved=False, repeat=2)
    document = {
        "schema": "sprint5.memory-source-runs.v2",
        "scope": "dev",
        "runs": [earlier_infra, later_fail, infra_only],
    }
    path = tmp_path / "handoff.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    cards, _status, handoffs, omitted = build_cards_from_handoffs(
        [path], canonical_path=CANONICAL, path_base=Path(".")
    )
    assert omitted == ("django__django-90004",)
    assert [card.source_id for card in cards] == ["django__django-90003"]
    assert cards[0].verification_status == "failed_attempt"
    assert cards[0].source_run.startswith("r2 ")
    manifest = manifest_for(
        cards,
        b"{}",
        status="final",
        commit="test",
        handoff_sha=handoffs[0]["sha256"],
        handoff_schema=handoffs[0]["schema"],
        handoffs=handoffs,
        omitted_infra_only=list(omitted),
    )
    assert manifest["omitted_infra_only"] == ["django__django-90004"]
