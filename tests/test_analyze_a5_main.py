import json

import pytest

from scripts.analyze_a5_main import (
    _rate,
    detection_floor_points,
    load_a5_main_tree,
    load_main_b0_handoff,
    prepare,
    render_report,
    short_groups,
)


def _row(task, repo, variant, repeat, solved, status="pass", injected=0, cost=0.1, calls=2, edit=3):
    return {
        "task_id": task,
        "repo": repo,
        "variant": variant,
        "repeat": repeat,
        "solved": solved,
        "status": status,
        "cost_cny": cost,
        "model_calls": calls,
        "first_edit_step": edit,
        "memory": {"injected": ["card"] * injected},
    }


def _pair(task, repo, b0, b2, injected=0):
    rows = []
    for repeat, solved in enumerate(b0, start=1):
        rows.append(_row(task, repo, "B0", repeat, solved, cost=0.2, calls=4, edit=5))
    for repeat, solved in enumerate(b2, start=1):
        rows.append(_row(task, repo, "B2", repeat, solved, injected=injected, cost=0.4, calls=6, edit=2))
    return rows


def test_zero_effect_uses_the_null_wording():
    rows = []
    for index in range(4):
        rows.extend(_pair(f"t{index}", "demo/demo", [False, False, False], [False, False, False]))
    report = render_report(rows)
    assert "没有检出大于 49.0 个百分点的效应" in report
    assert "平均 d_t：0.0000" in report
    assert detection_floor_points(4) == 49.0


def test_positive_effect_reports_the_size():
    rows = []
    for index in range(6):
        rows.extend(_pair(f"t{index}", "demo/demo", [False, False, False], [True, True, True], injected=1))
    report = render_report(rows)
    assert "平均 d_t 为 100.0 个百分点" in report
    assert "没有检出大于" not in report.split("## 次要分析")[0]
    assert "demo/demo：6 题，平均 d_t 1.0000" in report
    assert "B0 0.200，B2 0.400" in report


def test_infra_error_is_dropped_and_short_groups_are_listed():
    rows = _pair("kept", "demo/demo", [False, False, True], [True, True, False], injected=1)
    rows.append(
        {
            "task_id": "broken",
            "repo": "demo/demo",
            "variant": "B0",
            "repeat": 1,
            "solved": False,
            "status": "pass",
            "cost_cny": 0.1,
            "model_calls": 1,
            "first_edit_step": 1,
            "memory": {"injected": []},
        }
    )
    rows.append(
        {
            "task_id": "broken",
            "repo": "demo/demo",
            "variant": "B0",
            "repeat": 2,
            "solved": False,
            "status": "infra_error",
            "cost_cny": 9,
            "model_calls": 0,
            "first_edit_step": None,
            "memory": {"injected": []},
        }
    )
    rows.extend(_pair("broken", "demo/demo", [], [True, True, True]))
    eligible, excluded = prepare(rows)
    assert [item["task_id"] for item in eligible] == ["kept"]
    assert any(item.startswith("broken") for item in excluded)
    report = render_report(rows)
    assert "broken" in report
    assert "9" not in report.split("## 花费")[1]


def test_directory_layout_rejects_mock_and_lists_short_groups(tmp_path):
    root = tmp_path / "a5-main" / "django__django-90001"
    for variant, repeats in (("b0", (1, 2)), ("b2", (1, 2, 3))):
        for repeat in repeats:
            run = root / variant / f"r{repeat}"
            run.mkdir(parents=True)
            summary = {
                "task_id": "django__django-90001",
                "solved": False,
                "status": "pass",
                "cost_cny": "0.100",
                "model_calls": 1,
                "first_edit_step": 2,
                "memory": None,
            }
            (run / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    rows = load_a5_main_tree(tmp_path / "a5-main")
    assert len(rows) == 5
    assert rows[0]["variant"] == "B0"
    assert rows[0]["repo"] == "django/django"
    assert short_groups(rows) == ["django__django-90001 B0 2/3"]
    assert "django__django-90001 B0 2/3" in render_report(rows)
    (root / "b2" / "r3" / "summary.json").write_text(json.dumps({"mock": True}), encoding="utf-8")
    with pytest.raises(ValueError, match="mock_input"):
        load_a5_main_tree(tmp_path / "a5-main")


def test_main_b0_handoff_rejects_mock(tmp_path):
    path = tmp_path / "main-b0-runs.json"
    path.write_text(
        json.dumps({"schema": "sprint6.main-b0-runs.v1", "scope": "step7-mock", "runs": []}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="mock_input"):
        load_main_b0_handoff(path)
    path.write_text(
        json.dumps({"schema": "sprint6.main-b0-runs.v1", "scope": "pool", "runs": []}),
        encoding="utf-8",
    )
    assert load_main_b0_handoff(path)["schema"] == "sprint6.main-b0-runs.v1"


def test_two_valid_solves_count_as_a_full_rate():
    rows = _pair("short", "demo/demo", [True, True], [True, True])
    rows.append(_row("short", "demo/demo", "B0", 3, False, status="infra_error"))
    rows.append(_row("short", "demo/demo", "B2", 3, False, status="infra_error"))
    solved, n_valid, rate = _rate([row for row in rows if row["variant"] == "B0"])
    assert (solved, n_valid, rate) == (2, 2, 1.0)
    eligible, excluded = prepare(rows)
    assert excluded == []
    assert eligible[0]["d"] == 0.0
    report = render_report(rows)
    assert "除以有效运行数" in report
    assert "除以 3" not in report
