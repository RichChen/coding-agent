from scripts.analyze_a5_main import detection_floor_points, prepare, render_report

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
