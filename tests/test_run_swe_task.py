import base64
import json

import pytest

from scripts.run_swe_task import (
    HOLDOUT,
    apply_delta,
    dated_cards,
    delta_lost,
    resolve_image,
    select_tasks,
    solved,
    summarize_events,
    target_created_at,
    temporal_filter,
)


def test_holdout_is_refused():
    manifest = {"tasks": [{"id": "pytest-dev__pytest-7220"}]}
    try:
        select_tasks(manifest, [])
    except SystemExit as exc:
        assert "hold-out" in str(exc)
    else:
        raise AssertionError("hold-out task was accepted")


def test_solved_requires_full_pass_and_no_regression():
    assert solved({"status": "pass", "failed": 0, "regression_assigned": 2, "regression_passed": 2, "cases": [{"satisfied": True}]})
    assert not solved({"status": "partial", "failed": 1, "regression_assigned": 1, "regression_passed": 1, "cases": [{"satisfied": False}]})
    assert "pytest-dev__pytest-7220" in HOLDOUT


def test_summary_counts_tool_intent_and_edit_round():
    events = [
        {"event_type": "model.started", "payload": {}},
        {"event_type": "tool.intent", "payload": {"name": "search_code"}},
        {"event_type": "model.started", "payload": {}},
        {"event_type": "tool.intent", "payload": {"name": "search_replace"}},
        {"event_type": "run.finished", "payload": {"failure_reason": "none", "success": True, "termination_kind": None}},
    ]
    stats = summarize_events(events, {}, None)
    assert stats["tool_calls"] == 2
    assert stats["first_edit_step"] == 2
    assert stats["stop_reason"] == "completed"
    assert delta_lost(stats, None) is True
    assert delta_lost(stats, {"changed": {"changelog/x.rst": {}}}) is False


def test_stop_reason_reads_result_then_artifact(tmp_path):
    payload = {"termination_kind": "step_deadline", "failure_reason": "step_deadline", "success": False}
    digest = "ab" * 32
    (tmp_path / digest).write_text(json.dumps(payload), encoding="utf-8")
    events = [{"event_type": "run.finished", "payload": {"artifact_ref": digest}}]
    assert summarize_events(events, {}, None, tmp_path)["stop_reason"] == "step_deadline"
    assert summarize_events(events, {"termination_kind": "budget_exhausted"}, None, tmp_path)["stop_reason"] == "budget_exhausted"


class Card:
    def __init__(self, source_id, repo="django/django", created_at=None):
        self.source_id = source_id
        self.repo = repo
        self.created_at = created_at


def test_later_cards_are_filtered():
    cards = [
        Card("early", created_at="2018-01-01T00:00:00Z"),
        Card("later", created_at="2020-01-01T00:00:00Z"),
        Card("other", repo="sympy/sympy", created_at="2017-01-01T00:00:00Z"),
        Card("self", created_at="2019-01-01T00:00:00Z"),
    ]
    kept, dropped = temporal_filter(cards, task_id="self", repo="django/django", created_at="2019-01-01T00:00:00Z", dates={})
    assert [card.source_id for card in kept] == ["early"]
    assert "later" in dropped


def test_pool_cards_outside_the_dev_handoff_are_filtered_by_their_own_date():
    dev = {"dev-early": {"repo": "django/django", "created_at": "2018-01-01T00:00:00Z"}}
    cards = [
        Card("dev-early", created_at="2018-01-01T00:00:00Z"),
        Card("pool-early", created_at="2018-06-01T00:00:00Z"),
        Card("pool-later", created_at="2019-06-01T00:00:00Z"),
    ]
    kept, dropped = temporal_filter(cards, task_id="target", repo="django/django", created_at="2019-01-01T00:00:00Z", dates=dev)
    assert [card.source_id for card in kept] == ["dev-early", "pool-early"]
    assert dropped == ["pool-later"]


def test_dates_compare_as_instants_across_offsets():
    # The target is 23:10Z on Dec 31. A plain string compare gets both cards wrong.
    cards = [
        Card("earlier", created_at="2019-01-01T08:00:00+09:30"),
        Card("later", created_at="2018-12-31T23:30:00Z"),
    ]
    kept, dropped = temporal_filter(cards, task_id="target", repo="django/django", created_at="2019-01-01T07:10:00+08:00", dates={})
    assert [card.source_id for card in kept] == ["earlier"]
    assert dropped == ["later"]


def test_missing_or_bad_dates_are_errors():
    with pytest.raises(ValueError, match="missing"):
        temporal_filter([Card("undated")], task_id="t", repo="django/django", created_at="2019-01-01T00:00:00Z", dates={})
    with pytest.raises(ValueError, match="parsed"):
        temporal_filter([Card("bad", created_at="yesterday")], task_id="t", repo="django/django", created_at="2019-01-01T00:00:00Z", dates={})
    with pytest.raises(ValueError, match="timezone"):
        temporal_filter([Card("naive", created_at="2018-01-01T00:00:00")], task_id="t", repo="django/django", created_at="2019-01-01T00:00:00Z", dates={})


def test_card_date_must_agree_with_the_handoff():
    dates = {"a": {"repo": "django/django", "created_at": "2018-01-02T00:00:00Z"}}
    with pytest.raises(ValueError, match="disagrees"):
        temporal_filter([Card("a", created_at="2018-01-01T00:00:00Z")], task_id="t", repo="django/django", created_at="2019-01-01T00:00:00Z", dates=dates)
    same = {"a": {"repo": "django/django", "created_at": "2018-01-01T08:00:00+08:00"}}
    kept, _ = temporal_filter([Card("a", created_at="2018-01-01T00:00:00Z")], task_id="t", repo="django/django", created_at="2019-01-01T00:00:00Z", dates=same)
    assert len(kept) == 1


def test_b2_target_date_comes_from_main_targets_or_dev_handoff(tmp_path):
    targets = tmp_path / "main-targets.yaml"
    targets.write_text("tasks:\n- id: pool-task\n  created_at: '2020-01-01T00:00:00Z'\n", encoding="utf-8")
    dev = {"dev-task": {"repo": "django/django", "created_at": "2019-01-01T00:00:00Z"}}
    assert target_created_at("pool-task", dev, targets) == "2020-01-01T00:00:00Z"
    assert target_created_at("dev-task", dev, targets) == "2019-01-01T00:00:00Z"
    with pytest.raises(SystemExit, match="created_at"):
        target_created_at("unknown-task", dev, targets)


def test_undated_card_rows_are_errors(tmp_path, monkeypatch):
    from scripts import run_swe_task

    monkeypatch.setattr(run_swe_task, "handoff_dates", lambda: {"dated": {"repo": "django/django", "created_at": "2018-01-01T00:00:00Z"}})
    cards = tmp_path / "cards.jsonl"
    cards.write_text(json.dumps({"source_id": "dated"}) + "\n" + json.dumps({"source_id": "pool-undated"}) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="pool-undated"):
        dated_cards(cards)


def test_any_profile_requires_a_clean_image():
    task = {"id": "not-a-real-task"}
    receipt = {"baseline_image_digest": "old-image"}
    try:
        resolve_image(task, receipt, legacy_image=False, mock=False)
    except SystemExit as exc:
        assert "clean image required" in str(exc)
    else:
        raise AssertionError("a real run without a clean image was accepted")
    try:
        resolve_image(task, receipt, legacy_image=True, mock=False)
    except SystemExit as exc:
        assert "legacy" in str(exc)
    else:
        raise AssertionError("a legacy image was allowed to call the model")


def test_apply_delta_accepts_both_content_shapes():
    raw = base64.b64encode(b"print(1)\n").decode("ascii")
    base = {"a.py": b"old"}
    wrapped = apply_delta(base, {"changed": {"a.py": {"content": raw}}, "deleted": []})
    direct = apply_delta(base, {"changed": {"a.py": raw}, "deleted": []})
    assert wrapped["a.py"] == b"print(1)\n"
    assert direct["a.py"] == b"print(1)\n"
