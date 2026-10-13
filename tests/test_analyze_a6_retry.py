import base64
import json
from pathlib import Path

import pytest

from scripts import analyze_a5_main
from scripts.analyze_a6_retry import (
    SEED,
    _stats,
    bootstrap_ci,
    conclusion,
    detected,
    load_attempts,
    load_runs,
    main,
    prepare,
    render_report,
    second_stage_triggered,
    sign_flip_p,
    slot_issues,
)
from scripts.make_a6_synthetic import simulate, write_scenario

AGENT = Path(__file__).resolve().parents[1]
PLAN = AGENT.parent / "coding-harness" / "docs" / "sprint" / "A6-R-PLAN.zh-CN.md"
PREREG = AGENT / "docs" / "sprint" / "A6-R-PREREG.zh-CN.md"


def _b64(text):
    return base64.b64encode(text.encode()).decode()


def _row(task, arm, first, k, solved, status=None, **extra):
    row = {
        "task_id": task,
        "repo": "demo/demo",
        "arm": arm,
        "first": first,
        "k": k,
        "run_dir": f"runs/a6-retry/{task}/{arm}/{first}/r{k}",
        "mock": False,
        "status": status or ("pass" if solved else "fail"),
        "solved": solved,
        "model_calls": 40,
        "first_edit_step": 4,
        "cost_cny": "0.5",
        "changed_files": [],
        "prompt_sha256": "p-" + task,
        "retry": {"arm": arm, "first": first, "attempt_sha256": "s" if arm == "r1" else None},
    }
    row.update(extra)
    return row


def _task(task, r0, r1, first="b0r1"):
    rows = [_row(task, "r0", first, k, solved) for k, solved in enumerate(r0, start=1)]
    rows += [_row(task, "r1", first, k, solved) for k, solved in enumerate(r1, start=1)]
    return rows


def test_prereg_keeps_plan_section_one_verbatim():
    if not PLAN.is_file():
        pytest.skip("coding-harness plan not present")
    plan = PLAN.read_bytes().replace(b"\r\n", b"\n").decode("utf-8")
    section = plan[plan.index("## 1. 实验设计") : plan.index("## 2. 分工")].rstrip("\n")
    prereg = PREREG.read_bytes().replace(b"\r\n", b"\n").decode("utf-8")
    assert section in prereg


def test_statistics_follow_the_a5_script():
    values = [0.0, 0.333, -0.333, 0.667, 0.0, 1.0, -0.667]
    assert sign_flip_p(values, seed=20260926) == analyze_a5_main.sign_flip_p(values)
    assert bootstrap_ci(values, seed=20260926) == analyze_a5_main.bootstrap_ci(values)
    assert SEED == 20261013


def test_zero_effect_is_not_detected():
    rows = []
    for index in range(6):
        rows += _task(f"t{index}", [False, True, False], [False, True, False])
    eligible, excluded = prepare(rows)
    stats = _stats(eligible)
    assert excluded == []
    assert stats["mean"] == 0.0
    assert not detected(stats)
    assert conclusion(stats).startswith("未检出大于 40.0 个百分点的效应")
    assert not second_stage_triggered(stats)


def test_large_effect_is_detected_and_does_not_trigger_stage_two():
    rows = []
    for index in range(8):
        rows += _task(f"t{index}", [False, False, False], [True, True, True])
    stats = _stats(prepare(rows)[0])
    assert detected(stats)
    assert conclusion(stats).startswith("检出效应：平均 d_t 为 100.0 个百分点")
    assert not second_stage_triggered(stats)


def test_stage_two_needs_point_estimate_and_interval_with_zero():
    assert second_stage_triggered({"n": 22, "mean": 0.05, "low": -0.02, "high": 0.12})
    assert not second_stage_triggered({"n": 22, "mean": 0.049, "low": -0.02, "high": 0.12})
    assert not second_stage_triggered({"n": 22, "mean": 0.08, "low": 0.01, "high": 0.15})


def test_detection_needs_both_p_and_interval():
    assert not detected({"n": 22, "p": 0.04, "low": -0.01, "high": 0.2})
    assert not detected({"n": 22, "p": 0.06, "low": 0.01, "high": 0.2})
    assert detected({"n": 22, "p": 0.04, "low": 0.01, "high": 0.2})


def test_infra_errors_are_dropped_and_thin_tasks_excluded():
    rows = _task("kept", [True, False, False], [True, True, False])
    rows[0]["status"] = "infra_error"
    rows += _task("thin", [False, False, False], [True, True, True])
    rows[-6]["status"] = "infra_error"
    rows[-5]["status"] = "infra_error"
    eligible, excluded = prepare(rows)
    assert [task["task_id"] for task in eligible] == ["kept"]
    assert eligible[0]["r0_n"] == 2 and eligible[0]["r0_k"] == 0
    assert eligible[0]["d"] == pytest.approx(2 / 3)
    assert excluded == ["thin R0有效1 R1有效3"]


def test_rates_pool_all_first_attempts_of_a_task():
    rows = _task("t", [True, False, False], [True, True, True], first="b0r1")
    rows += _task("t", [False, False, False], [False, False, False], first="b0r2")
    eligible, _ = prepare(rows)
    assert (eligible[0]["r0_k"], eligible[0]["r0_n"]) == (1, 6)
    assert eligible[0]["d"] == pytest.approx(3 / 6 - 1 / 6)


def test_loader_rejects_mock_and_wrong_schema(tmp_path):
    path = tmp_path / "runs.json"
    for payload, error in (
        ({"schema": "a6.retry-runs.v1", "scope": "mock", "runs": []}, "mock_input"),
        ({"schema": "a6.retry-runs.v0", "scope": "a6-retry", "runs": []}, "unexpected_runs_schema"),
        (
            {
                "schema": "a6.retry-runs.v1",
                "scope": "a6-retry",
                "runs": [_row("t", "r0", "b0r1", 1, False, mock=True)],
            },
            "mock_input",
        ),
        (
            {
                "schema": "a6.retry-runs.v1",
                "scope": "a6-retry",
                "runs": [_row("t", "r2", "b0r1", 1, False)],
            },
            "unexpected_arm",
        ),
    ):
        path.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(ValueError, match=error):
            load_runs(path)
    attempts = tmp_path / "attempts.json"
    attempts.write_text(
        json.dumps({"attempts": [{"task": "t", "first": "b0r4", "sha256": "x"}]}), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="bad_attempt_entry"):
        load_attempts(attempts)


def test_slot_issues_list_missing_duplicate_and_mismatched_slots():
    attempts = [{"task": "t", "first": "b0r1", "sha256": "s"}]
    rows = _task("t", [False, False, False], [False, False, False])
    assert all(not items for items in slot_issues(rows, attempts).values())
    rows[0]["run_dir"] = "runs/elsewhere"
    rows[3]["retry"]["attempt_sha256"] = "other"
    rows.append(dict(rows[1]))
    rows.append(_row("u", "r0", "b0r1", 1, False))
    del rows[2]
    issues = slot_issues(rows, attempts)
    assert issues["缺的槽位"] == ["t/r0/b0r1/r3"]
    assert issues["重复的槽位"] == ["t/r0/b0r1/r2"]
    assert issues["清单外的槽位"] == ["u/r0/b0r1/r1"]
    assert issues["run_dir 与槽位不符"] == ["t/r0/b0r1/1 -> runs/elsewhere"]
    assert issues["R1 的 attempt_sha256 与清单不符"] == ["t/b0r1/r1"]


def _tiny_root(tmp_path):
    root = tmp_path / "harness"
    original = root / "runs" / "sprint5-main-images" / "t" / "staging" / "original"
    (original / "pkg").mkdir(parents=True)
    (original / "pkg" / "a.py").write_text("x = 0\n", encoding="utf-8")
    first = {"changed": {"pkg/a.py": _b64("x = 1\n")}, "deleted": []}
    for repeat in (1, 2, 3):
        run = root / "runs" / "a5-main" / "t" / "b0" / f"r{repeat}"
        run.mkdir(parents=True)
        summary = {
            "task_id": "t",
            "solved": repeat == 3,
            "status": "fail",
            "prompt_sha256": "p-t",
            "changed_files": ["pkg/a.py"],
        }
        (run / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
        (run / "candidate-delta.json").write_text(json.dumps(first), encoding="utf-8")
    rows = _task("t", [False, False, False], [True, False, False])
    seconds = {
        ("r0", 1): (first, ["pkg/a.py"]),
        ("r0", 2): ({"changed": {"pkg/a.py": _b64("x = 1\r\n")}}, ["pkg/a.py"]),
        ("r0", 3): ({"changed": {"pkg/b.py": _b64("y\n")}}, ["pkg/b.py"]),
        ("r1", 1): ({"changed": {"pkg/a.py": _b64("x = 2\n")}}, ["pkg/a.py", "tests/test_a.py"]),
        ("r1", 2): ({"changed": {}}, []),
    }
    for row in rows:
        key = (row["arm"], row["k"])
        if key in seconds:
            delta, files = seconds[key]
            run = root / row["run_dir"]
            run.mkdir(parents=True)
            (run / "candidate-delta.json").write_text(json.dumps(delta), encoding="utf-8")
            row["changed_files"] = files
    rows[3]["first_edit_step"] = None
    rows[4]["model_calls"] = 12
    return root, rows


def test_secondary_metrics_count_diff_repeats_and_file_reuse(tmp_path):
    root, rows = _tiny_root(tmp_path)
    payload = {"schema": "a6.retry-runs.v1", "scope": "a6-retry", "runs": rows}
    attempts = [{"task": "t", "first": "b0r1", "sha256": "s"}]
    report = render_report(payload, attempts, root)
    assert "- R0：2/3（0.667）" in report.split("### 1. diff 重复率")[1]
    assert "- R1：0/2（0.000）" in report.split("### 1. diff 重复率")[1]
    assert "R1 缺 candidate-delta.json：runs/a6-retry/t/r1/b0r1/r3" in report
    reuse = report.split("### 2. 文件复用")[1].split("###")[0]
    assert "- R0：2/3（0.667）" in reuse
    assert "- R1：1/3（0.333）" in reuse
    assert "- R1：平均 4.000，中位数 4.0，null 1 次" in report
    assert "用满 40 次 2/3（0.667）" in report
    assert "| t | demo/demo | 中间档 | 1 | 0/3 | 1/3 | 0.333 |" in report
    assert "R0 的 prompt_sha256 与 A5 B0 不同的题：无" in report
    assert "第一次尝试：1 次、1 道题（预期 53/22）" in report


def test_retired_infra_rows_are_ignored(tmp_path):
    root, rows = _tiny_root(tmp_path)
    retired = dict(rows[0], run_dir=rows[0]["run_dir"] + ".infra1", status="infra_error")
    payload = {"schema": "a6.retry-runs.v1", "scope": "a6-retry", "runs": rows + [retired]}
    report = render_report(payload, [{"task": "t", "first": "b0r1", "sha256": "s"}], root)
    assert "列出的退役目录（未计入）：runs/a6-retry/t/r0/b0r1/r1.infra1" in report
    assert "重复的槽位：无" in report


def test_synthetic_end_to_end_through_the_cli(tmp_path, monkeypatch):
    scenario = simulate(0.3, SEED + 30)
    assert len(scenario["attempts"]) == 53
    assert len({item["task"] for item in scenario["attempts"]}) == 22
    assert len(scenario["rows"]) == 318
    runs_path, attempts_path = write_scenario(tmp_path, scenario)
    out = tmp_path / "report.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "analyze",
            "--runs",
            str(runs_path),
            "--attempts",
            str(attempts_path),
            "--harness-root",
            str(tmp_path),
            "--out",
            str(out),
        ],
    )
    assert main() == 0
    report = out.read_text(encoding="utf-8")
    assert report.startswith("# A6-R 分析（合成数据，scope=synthetic）")
    assert "第一次尝试：53 次、22 道题（预期 53/22）" in report
    assert "槽位行数：318（预期 318）" in report
    assert "infra_error：2 次" in report
    assert "，一致" in report
    for name in (
        "缺的槽位",
        "重复的槽位",
        "清单外的槽位",
        "run_dir 与槽位不符",
        "R1 的 attempt_sha256 与清单不符",
    ):
        assert f"{name}：无" in report
    assert "- 0/3：13 题" in report
    assert "- 中间档：9 题" in report
    assert "+10pp 约 54%，+15pp 约 85%，+20pp 约 98%" in report


def test_cli_stops_on_mock_input(tmp_path, monkeypatch, capsys):
    runs = tmp_path / "runs.json"
    runs.write_text(
        json.dumps({"schema": "a6.retry-runs.v1", "mock": True, "runs": []}), encoding="utf-8"
    )
    attempts = tmp_path / "attempts.json"
    attempts.write_text(json.dumps({"attempts": []}), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "analyze",
            "--runs",
            str(runs),
            "--attempts",
            str(attempts),
            "--harness-root",
            str(tmp_path),
            "--out",
            str(tmp_path / "r.md"),
        ],
    )
    assert main() == 2
    assert "STOP mock_input" in capsys.readouterr().out
