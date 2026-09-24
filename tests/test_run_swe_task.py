from scripts.run_swe_task import HOLDOUT, select_tasks, solved


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
