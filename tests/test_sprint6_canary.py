from scripts import sprint6_canary


def _good(monkeypatch):
    monkeypatch.setattr(sprint6_canary, "calibration_ids", lambda task_id: {"f2p": 2, "p2p": 10})
    summary = {"mock": False, "profile": "b0-v2", "answer_isolation_pass": True, "status": "fail",
               "grader_ids": {"f2p": 2, "p2p": 9, "missing": 0, "reason": None},
               "harness_tool_errors": 0, "cost_cny": "0.120", "docker_retries": []}
    ledger = {"currency": "CNY", "cost_committed": "0.120"}
    return summary, ledger


def test_a_clean_canary_passes(monkeypatch):
    summary, ledger = _good(monkeypatch)
    assert sprint6_canary.check_summary("t", summary, ledger, excluded=1) == []


def test_harness_tool_errors_fail_the_canary(monkeypatch):
    summary, ledger = _good(monkeypatch)
    summary["harness_tool_errors"] = 1
    assert sprint6_canary.check_summary("t", summary, ledger, excluded=1) == ["harness_tool_errors is 1"]
    del summary["harness_tool_errors"]
    assert sprint6_canary.check_summary("t", summary, ledger, excluded=1) == ["harness_tool_errors is None"]


def test_docker_infra_error_fails_the_canary(monkeypatch):
    summary, ledger = _good(monkeypatch)
    summary.update(status="infra_error", infra_reason="candidate snapshot failed: DockerUnavailable")
    assert sprint6_canary.check_summary("t", summary, ledger, excluded=1) == [
        "infra_error: candidate snapshot failed: DockerUnavailable"]


def test_ids_and_ledger_are_checked(monkeypatch):
    summary, ledger = _good(monkeypatch)
    assert sprint6_canary.check_summary("t", summary, ledger, excluded=0)[0].startswith("grader ids")
    assert sprint6_canary.check_summary("t", summary, None, excluded=1) == ["no CNY ledger"]
    assert "ledger cost" in sprint6_canary.check_summary("t", summary, {"currency": "CNY", "cost_committed": "0.1"}, excluded=1)[0]


def test_select_takes_the_lower_median_per_python(monkeypatch):
    versions = {"a": "python:3.6.15-slim-buster", "b": "python:3.6.15-slim-buster", "c": "python:3.6.15-slim-buster",
                "d": "python:3.6.15-slim-buster", "e": "python:3.11-slim-bookworm"}
    monkeypatch.setattr(sprint6_canary, "clean_record", lambda task_id: {"base_image": versions[task_id]})
    tasks = [{"id": key, "created_at": "2020-01-0" + str(i)} for i, key in enumerate("dcbae", start=1)]
    assert sprint6_canary.select(tasks) == {"3.11": "e", "3.6": "c"}
