import base64
import json

from scripts.run_swe_task import HOLDOUT, apply_delta, delta_lost, select_tasks, solved, summarize_events


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


def test_apply_delta_accepts_both_content_shapes():
    raw = base64.b64encode(b"print(1)\n").decode("ascii")
    base = {"a.py": b"old"}
    wrapped = apply_delta(base, {"changed": {"a.py": {"content": raw}}, "deleted": []})
    direct = apply_delta(base, {"changed": {"a.py": raw}, "deleted": []})
    assert wrapped["a.py"] == b"print(1)\n"
    assert direct["a.py"] == b"print(1)\n"
