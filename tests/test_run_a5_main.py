import asyncio
import json
from decimal import Decimal

import pytest

from scripts import run_a5_main
from scripts.run_a5_main import halt_reason, handoff_path_for, out_root_for, resumable, run_phase, write_b0_handoff

TASK = {"id": "django__django-16527", "repo": "django/django", "created_at": "2023-02-05T22:05:00Z"}
REAL = {"mock": False, "profile": "b0-v2", "model": {"name": "deepseek-flash", "base_url_host": "api.deepseek.com"}}


def _summary(root, phase, slot="r1", **fields):
    path = root / TASK["id"] / phase / slot / "summary.json"
    path.parent.mkdir(parents=True)
    row = {"task_id": TASK["id"], "variant": phase.upper(), "solved": False, "status": "fail", "cost_cny": "0"}
    row.update(fields)
    path.write_text(json.dumps(row), encoding="utf-8")
    return path


def _fake_runner(monkeypatch, statuses):
    calls = []

    async def fake(task, profile, output, **kwargs):
        status = statuses[len(calls)]
        calls.append(output.name)
        row = {"task_id": task["id"], "variant": kwargs["variant"], "status": status, "solved": status == "pass", "cost_cny": "0.1", **REAL}
        (output / "summary.json").write_text(json.dumps(row), encoding="utf-8")
        return row

    monkeypatch.setattr(run_a5_main, "run_task", fake)
    monkeypatch.setattr(run_a5_main, "materialize_runner_task", lambda task: task)
    return calls


def _no_runs(monkeypatch):
    async def must_not_run(*args, **kwargs):
        raise AssertionError("a run started")

    monkeypatch.setattr(run_a5_main, "run_task", must_not_run)
    monkeypatch.setattr(run_a5_main, "materialize_runner_task", lambda task: task)


def test_mock_and_real_runs_use_separate_roots():
    assert out_root_for(True).name == "a5-main-mock"
    assert out_root_for(False).name == "a5-main"
    assert handoff_path_for(True).name == "main-b0-runs.mock.json"
    assert handoff_path_for(False).name == "main-b0-runs.json"


def test_b0_and_b2_share_one_parallel_setting():
    assert run_a5_main.PARALLEL == 3


def test_budget_caps_revision_2():
    from decimal import Decimal
    assert run_a5_main.PHASE_CAP == {"b0": Decimal("110"), "b2": Decimal("220")}
    assert run_a5_main.TOTAL_CAP == Decimal("220")


def test_spend_counts_only_the_formal_root(tmp_path):
    formal = tmp_path / "a5-main"
    void = tmp_path / "a5-main-void" / "r1-tool-py36"
    for root, cost in ((formal, "1.5"), (void, "13.682")):
        path = root / "t" / "b0" / "r1" / "summary.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"cost_cny": cost}), encoding="utf-8")
    assert str(run_a5_main.spent(formal)) == "1.5"


def test_resume_requires_matching_mock_profile_and_variant():
    good = {"mock": False, "profile": "b0-v2", "variant": "B0"}
    assert resumable(good, phase="b0", mock=False) is None
    assert resumable({"variant": "B0"}, phase="b0", mock=False)
    assert resumable({**good, "mock": True}, phase="b0", mock=False)
    assert resumable({**good, "profile": "b0-v1"}, phase="b0", mock=False)
    assert resumable(good, phase="b2", mock=False)


def test_real_phase_refuses_a_mock_summary(tmp_path, monkeypatch):
    path = _summary(tmp_path, "b0", mock=True, profile="b0-v2")
    before = path.read_bytes()
    _no_runs(monkeypatch)
    with pytest.raises(SystemExit, match="mock run"):
        asyncio.run(run_phase([TASK], "b0", cards=None, mock=False, repeats=1, out_root=tmp_path))
    assert path.read_bytes() == before


def test_real_phase_refuses_a_summary_without_mock_field(tmp_path, monkeypatch):
    _summary(tmp_path, "b0")
    _no_runs(monkeypatch)
    with pytest.raises(SystemExit, match="no mock/profile"):
        asyncio.run(run_phase([TASK], "b0", cards=None, mock=False, repeats=1, out_root=tmp_path))


def test_interrupted_run_directory_is_refused(tmp_path, monkeypatch):
    (tmp_path / TASK["id"] / "b0" / "r1" / "workspace").mkdir(parents=True)
    _no_runs(monkeypatch)
    with pytest.raises(SystemExit, match="no summary.json"):
        asyncio.run(run_phase([TASK], "b0", cards=None, mock=False, repeats=1, out_root=tmp_path))


def test_finished_and_failed_runs_are_not_repeated(tmp_path, monkeypatch):
    _summary(tmp_path, "b0", **REAL)
    _no_runs(monkeypatch)
    report = asyncio.run(run_phase([TASK], "b0", cards=None, mock=False, repeats=1, out_root=tmp_path))
    assert report["started"] == 0 and report["halt_reason"] is None


def test_infra_error_slot_is_moved_aside_and_rerun_at_most_twice(tmp_path, monkeypatch):
    monkeypatch.setattr(run_a5_main, "INFRA_STOP_RATIO", Decimal("1"))
    _summary(tmp_path, "b0", status="infra_error", **REAL)
    calls = _fake_runner(monkeypatch, ["infra_error", "infra_error"])
    report = asyncio.run(run_phase([TASK], "b0", cards=None, mock=False, repeats=1, out_root=tmp_path))
    slots = sorted(path.name for path in (tmp_path / TASK["id"] / "b0").iterdir())
    assert slots == ["r1", "r1.infra1", "r1.infra2"]
    assert calls == ["r1", "r1"]
    assert report["infra_kept"] == [(tmp_path / TASK["id"] / "b0" / "r1").as_posix()]
    again = asyncio.run(run_phase([TASK], "b0", cards=None, mock=False, repeats=1, out_root=tmp_path))
    assert again["started"] == 0 and len(again["infra_kept"]) == 1


def test_infra_error_rerun_that_passes_stops_rerunning(tmp_path, monkeypatch):
    monkeypatch.setattr(run_a5_main, "INFRA_STOP_RATIO", Decimal("1"))
    calls = _fake_runner(monkeypatch, ["infra_error", "pass"])
    report = asyncio.run(run_phase([TASK], "b0", cards=None, mock=False, repeats=1, out_root=tmp_path))
    assert calls == ["r1", "r1"]
    assert report["infra_kept"] == []
    assert json.loads((tmp_path / TASK["id"] / "b0" / "r1" / "summary.json").read_text())["status"] == "pass"


def test_handoff_reads_only_the_numbered_slot(tmp_path):
    _summary(tmp_path, "b0", slot="r1.infra1", status="infra_error", **REAL)
    _summary(tmp_path, "b0", status="pass", solved=True, **REAL)
    destination = tmp_path / "main-b0-runs.json"
    write_b0_handoff(mock=False, out_root=tmp_path, destination=destination, tasks=[TASK])
    runs = json.loads(destination.read_text(encoding="utf-8"))["runs"]
    assert [(run["repeat"], run["status"]) for run in runs] == [(1, "pass")]


def _slots(root, statuses):
    for index, status in enumerate(statuses):
        path = root / ("task-" + str(index)) / "b0" / "r1" / "summary.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"task_id": "task-" + str(index), "status": status, "cost_cny": "0", **REAL}), encoding="utf-8")


def test_any_harness_tool_error_halts(tmp_path):
    _slots(tmp_path, ["fail", "pass"])
    assert halt_reason(tmp_path, "b0") is None
    path = tmp_path / "task-1" / "b0" / "r1" / "summary.json"
    row = json.loads(path.read_text(encoding="utf-8"))
    path.write_text(json.dumps({**row, "harness_tool_errors": 1}), encoding="utf-8")
    assert halt_reason(tmp_path, "b0") == "harness tool errors: task-1 1"


def test_harness_tool_errors_halt_even_on_an_infra_row(tmp_path):
    _slots(tmp_path, ["fail"])
    path = tmp_path / "task-0" / "b0" / "r1" / "summary.json"
    row = json.loads(path.read_text(encoding="utf-8"))
    path.write_text(json.dumps({**row, "status": "infra_error", "harness_tool_errors": 2}), encoding="utf-8")
    assert halt_reason(tmp_path, "b0").startswith("harness tool errors")


def test_two_infra_errors_never_halt(tmp_path):
    _slots(tmp_path, ["infra_error", "infra_error"])
    assert halt_reason(tmp_path, "b0") is None


def test_three_infra_errors_halt_only_above_ten_percent(tmp_path):
    _slots(tmp_path, ["infra_error"] * 3)
    assert "infra_error 3 of 3" in halt_reason(tmp_path, "b0")
    at_ten = tmp_path / "at-ten"
    _slots(at_ten, ["infra_error"] * 3 + ["fail"] * 27)
    assert halt_reason(at_ten, "b0") is None
    above = tmp_path / "above"
    _slots(above, ["infra_error"] * 3 + ["fail"] * 26)
    assert "infra_error 3 of 29" in halt_reason(above, "b0")


def test_isolation_missing_ids_and_grader_crash_halt(tmp_path):
    _summary(tmp_path, "b0", slot="r1", answer_isolation_pass=False, status="answer_isolation_failed", **REAL)
    assert "isolation" in halt_reason(tmp_path, "b0")
    other = tmp_path / "missing"
    _summary(other, "b0", grader_ids={"missing": 2, "reason": None}, **REAL)
    assert "missing" in halt_reason(other, "b0")
    crashed = tmp_path / "crashed"
    _summary(crashed, "b0", grader_ids={"missing": 0, "reason": "RuntimeError: boom"}, **REAL)
    assert "crashed" in halt_reason(crashed, "b0")


def test_model_name_change_halts(tmp_path):
    _summary(tmp_path, "b0", slot="r1", **REAL)
    _summary(tmp_path, "b0", slot="r2", **{**REAL, "model": {"name": "deepseek-pro", "base_url_host": "api.deepseek.com"}})
    assert "model name changed" in halt_reason(tmp_path, "b0")
    inside = tmp_path / "inside"
    _summary(inside, "b0", **{**REAL, "model": {"name": "a", "changed_to": {"name": "b"}}})
    assert "during a run" in halt_reason(inside, "b0")


def test_b0_soft_cap_halts(tmp_path):
    _summary(tmp_path, "b0", cost_cny="109.99", **REAL)
    assert halt_reason(tmp_path, "b0") is None
    _summary(tmp_path, "b0", slot="r2", cost_cny="0.01", **REAL)
    assert "cap" in halt_reason(tmp_path, "b0")
    assert halt_reason(tmp_path, "b2") is None


def test_halt_stops_new_runs_but_writes_a_report(tmp_path, monkeypatch):
    _summary(tmp_path, "b0", slot="r1", status="infra_error", **REAL)
    monkeypatch.setattr(run_a5_main, "MAX_INFRA_RERUNS", 0)
    monkeypatch.setattr(run_a5_main, "INFRA_STOP_MIN", 1)
    _no_runs(monkeypatch)
    report = asyncio.run(run_phase([TASK], "b0", cards=None, mock=False, repeats=2, out_root=tmp_path))
    assert report["halt_reason"].startswith("infra_error")
    assert report["not_started"] == 1
    assert (tmp_path / "b0-report.json").is_file()


class _Spec:
    expected_nodeids = ("a", "b", "c")
    baseline_passed = ("b", "c")


def _fake_preflight(monkeypatch, *, failure=None, recorded=None, crash=False, excluded=(), selected_p2p=("b", "c"), smoke_ok=True):
    smoked = []

    def prerun(task, *, mock):
        assert mock is False
        if crash:
            raise SystemExit("grader ids differ from calibration")
        return _Spec(), "image@sha256:1", {"answer_isolation_pass": True, "base_image": "python:3.6.15-slim-buster"}, failure

    async def smoke(image, profile):
        smoked.append(image)
        call = {"tool": "read_file", "ok": smoke_ok, "exception": None if smoke_ok else "AttributeError", "error_kind": None}
        return {"passed": smoke_ok, "error": None, "calls": [call]}

    monkeypatch.setattr(run_a5_main, "tool_smoke", smoke)

    def materialize(task):
        nodeids = {"f2p": ["a"], "p2p": list(selected_p2p)}
        return {**task, "public_task": "public.json", "grader_nodeids": nodeids, "p2p_excluded": list(excluded)}

    monkeypatch.setattr(run_a5_main, "materialize_runner_task", materialize)
    monkeypatch.setattr(run_a5_main, "prerun_check", prerun)
    monkeypatch.setattr(run_a5_main, "public_issue", lambda task: "issue")
    monkeypatch.setattr(run_a5_main, "calibration_ids", lambda task_id: recorded or {"f2p": 1, "p2p": 2})
    return smoked


def test_preflight_runs_the_tool_smoke_and_groups_by_python(tmp_path, monkeypatch):
    smoked = _fake_preflight(monkeypatch)
    report = run_a5_main.preflight([TASK], destination=tmp_path / "preflight.json")
    assert smoked == ["image@sha256:1"]
    assert report["tool_smoke_passed"] == 1
    assert report["by_python"] == {"3.6": {"passed": 1, "total": 1, "tool_smoke_passed": 1}}


def test_preflight_fails_a_task_whose_tool_smoke_fails(tmp_path, monkeypatch):
    _fake_preflight(monkeypatch, smoke_ok=False)
    report = run_a5_main.preflight([TASK], destination=tmp_path / "preflight.json")
    assert report["passed"] == 0 and report["tool_smoke_passed"] == 0
    assert report["tasks"][0]["failure"] == "tool smoke failed: read_file:AttributeError"


def test_preflight_skips_the_smoke_when_an_earlier_check_fails(tmp_path, monkeypatch):
    smoked = _fake_preflight(monkeypatch, failure="opt/repo source-only hash mismatch")
    run_a5_main.preflight([TASK], destination=tmp_path / "preflight.json")
    assert smoked == []


def test_preflight_passes_and_writes_a_report(tmp_path, monkeypatch):
    _fake_preflight(monkeypatch)
    report = run_a5_main.preflight([TASK], destination=tmp_path / "preflight.json")
    assert (report["passed"], report["total"]) == (1, 1)
    row = report["tasks"][0]
    assert row["grader_ids"] == {"f2p": 1, "p2p": 2} and row["answer_isolation_pass"] is True
    assert json.loads((tmp_path / "preflight.json").read_text(encoding="utf-8"))["passed"] == 1


def test_preflight_reports_a_source_only_failure(tmp_path, monkeypatch):
    _fake_preflight(monkeypatch, failure="opt/repo source-only hash mismatch")
    report = run_a5_main.preflight([TASK], destination=tmp_path / "preflight.json")
    assert report["passed"] == 0 and "source-only" in report["tasks"][0]["failure"]


def test_preflight_compares_grader_ids_with_calibration(tmp_path, monkeypatch):
    _fake_preflight(monkeypatch, recorded={"f2p": 1, "p2p": 3})
    report = run_a5_main.preflight([TASK], destination=tmp_path / "preflight.json")
    assert report["passed"] == 0 and "differ from calibration" in report["tasks"][0]["failure"]


def test_preflight_subtracts_calibrated_p2p_exclusions(tmp_path, monkeypatch):
    _fake_preflight(monkeypatch, recorded={"f2p": 1, "p2p": 3}, excluded=["d"], selected_p2p=("b", "c", "d"))
    report = run_a5_main.preflight([TASK], destination=tmp_path / "preflight.json")
    assert report["passed"] == 1 and report["tasks"][0]["p2p_excluded"] == 1


def test_preflight_refuses_an_exclusion_outside_the_selection(tmp_path, monkeypatch):
    _fake_preflight(monkeypatch, recorded={"f2p": 1, "p2p": 3}, excluded=["zzz"])
    report = run_a5_main.preflight([TASK], destination=tmp_path / "preflight.json")
    assert report["passed"] == 0 and "not in the selected p2p" in report["tasks"][0]["failure"]


def test_preflight_records_a_crash_and_keeps_going(tmp_path, monkeypatch):
    _fake_preflight(monkeypatch, crash=True)
    report = run_a5_main.preflight([TASK, {**TASK, "id": "other"}], destination=tmp_path / "preflight.json")
    assert (report["passed"], report["total"]) == (0, 2)
    assert report["tasks"][0]["failure"].startswith("SystemExit")


def test_out_root_requires_mock(monkeypatch):
    monkeypatch.setattr("sys.argv", ["run_a5_main.py", "--phase", "b0", "--out-root", "runs/x"])
    with pytest.raises(SystemExit, match="only allowed with --mock"):
        run_a5_main.main()


def test_real_handoff_refuses_a_mock_summary(tmp_path):
    _summary(tmp_path, "b0", mock=True, profile="b0-v2")
    destination = tmp_path / "main-b0-runs.json"
    with pytest.raises(SystemExit, match="mock run"):
        write_b0_handoff(mock=False, out_root=tmp_path, destination=destination, tasks=[TASK])
    assert not destination.exists()


def test_mock_handoff_accepts_mock_summaries(tmp_path):
    _summary(tmp_path, "b0", mock=True, profile="b0-v2")
    destination = tmp_path / "main-b0-runs.mock.json"
    write_b0_handoff(mock=True, out_root=tmp_path, destination=destination, tasks=[TASK])
    payload = json.loads(destination.read_text(encoding="utf-8"))
    assert payload["scope"] == "mock"
    assert [run["source_id"] for run in payload["runs"]] == [TASK["id"]]
