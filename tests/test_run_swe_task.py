import base64
import json

from scripts.run_swe_task import HOLDOUT, apply_delta, delta_lost, resolve_image, select_tasks, solved, summarize_events, temporal_filter


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


def test_later_cards_are_filtered():
    class Card:
        def __init__(self, source_id):
            self.source_id = source_id
    dates = {
        "early": {"repo": "django/django", "created_at": "2018-01-01T00:00:00Z"},
        "later": {"repo": "django/django", "created_at": "2020-01-01T00:00:00Z"},
        "other": {"repo": "sympy/sympy", "created_at": "2017-01-01T00:00:00Z"},
        "self": {"repo": "django/django", "created_at": "2019-01-01T00:00:00Z"},
    }
    cards = [Card("early"), Card("later"), Card("other"), Card("self")]
    kept, dropped = temporal_filter(cards, task_id="self", repo="django/django", created_at="2019-01-01T00:00:00Z", dates=dates)
    assert [card.source_id for card in kept] == ["early"]
    assert "later" in dropped


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
