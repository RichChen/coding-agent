from scripts import sprint6_canary

ISSUE_SHA = "a" * 64


def _good(monkeypatch):
    monkeypatch.setattr(sprint6_canary, "calibration_ids", lambda task_id: {"f2p": 2, "p2p": 10})
    monkeypatch.setattr(sprint6_canary, "recorded_issue_sha", lambda task_id: ISSUE_SHA)
    summary = {"mock": False, "profile": "b0-v2", "answer_isolation_pass": True, "status": "fail",
               "issue_sha256": ISSUE_SHA, "prompt_sha256": "b" * 64,
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


def test_issue_sha_must_match_main_issues(monkeypatch):
    summary, ledger = _good(monkeypatch)
    summary["issue_sha256"] = "c" * 64
    assert sprint6_canary.check_summary("t", summary, ledger, excluded=1)[0].startswith("issue_sha256")
    del summary["issue_sha256"]
    del summary["prompt_sha256"]
    problems = sprint6_canary.check_summary("t", summary, ledger, excluded=1)
    assert problems[0].startswith("issue_sha256") and problems[1] == "no prompt_sha256"


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


def test_select_takes_the_lower_median_per_repo():
    repos = {"a": "x/x", "b": "x/x", "c": "x/x", "d": "x/x", "e": "y/y"}
    tasks = [{"id": key, "repo": repos[key], "created_at": "2020-01-0" + str(i)} for i, key in enumerate("dcbae", start=1)]
    assert sprint6_canary.select(tasks) == {"x/x": "c", "y/y": "e"}
