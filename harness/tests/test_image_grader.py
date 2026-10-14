from src.eval.image_grader import receipt_diagnostics, score_receipt, touched_kinds


def _receipt(nodes):
    reports = []
    for node, outcome in nodes:
        reports.append({"nodeid": node, "when": "setup", "outcome": "passed"})
        reports.append({"nodeid": node, "when": "call", "outcome": outcome})
        reports.append({"nodeid": node, "when": "teardown", "outcome": "passed"})
    return {"reports": reports}


def test_score_uses_receipt_nodeids_not_a_count():
    scored = score_receipt(_receipt([("a.py::t", "passed"), ("b.py::t", "failed")]), ["a.py::t"], ["b.py::t"])
    assert scored["solved"] is False
    assert scored["f2p_passed"] == 1 and scored["f2p_total"] == 1
    assert scored["p2p_passed"] == 0 and scored["p2p_total"] == 1


def test_score_solved_when_f2p_and_p2p_pass():
    scored = score_receipt(_receipt([("a.py::t", "passed"), ("b.py::t", "passed")]), ["a.py::t"], ["b.py::t"])
    assert scored["solved"] is True


def test_receipt_diagnostics_truncates_errors():
    diag = receipt_diagnostics({
        "collected": ["a", "b"],
        "collection_errors": [{"detail": "x" * 3000}] + [{"detail": str(i)} for i in range(25)],
        "runner_error": "boom",
        "exit_code": 1,
    })
    assert diag["collected_count"] == 2
    assert len(diag["collection_errors"]) == 20
    assert len(diag["collection_errors"][0]) == 2048
    assert diag["runner_error"] == "boom"
    assert diag["exit_code"] == 1


def test_touched_files_are_recorded():
    kinds = touched_kinds(["src/app.py", "tests/test_app.py", "setup.cfg"])
    assert kinds["test_files_touched"] == ["tests/test_app.py"]
    assert kinds["config_files_touched"] == ["setup.cfg"]
