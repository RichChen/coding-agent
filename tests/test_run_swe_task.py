from scripts.run_swe_task import HOLDOUT, delta_lost, select_tasks, solved, summarize_events


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
    assert stats["stop_reason"].startswith("unknown:")
    assert delta_lost(stats, None) is True
    assert delta_lost(stats, {"changed": {"changelog/x.rst": {}}}) is False
