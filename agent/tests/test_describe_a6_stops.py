import json

from scripts.describe_a6_stops import render


def _row(task, arm, first, k, stop, status, calls=40):
    return {
        "task_id": task,
        "repo": "demo/demo",
        "arm": arm,
        "first": first,
        "k": k,
        "run_dir": f"runs/a6-retry/{task}/{arm}/{first}/r{k}",
        "mock": False,
        "status": status,
        "solved": status == "pass",
        "model_calls": calls,
        "stop_reason": stop,
    }


def test_counts_by_arm_and_lists_parse_errors(tmp_path):
    rows = [
        _row("t", "r0", "b0r1", 1, "completed", "pass", 12),
        _row("t", "r0", "b0r1", 2, "max_model_calls", "fail"),
        _row("t", "r1", "b0r1", 1, "model_parse_error", "partial", 37),
        _row("t", "r1", "b0r1", 2, "context_overflow", "fail", 20),
    ]
    runs = tmp_path / "runs.json"
    runs.write_text(
        json.dumps({"schema": "a6.retry-runs.v1", "scope": "a6-retry", "runs": rows}),
        encoding="utf-8",
    )
    retired = tmp_path / "retired.json"
    retired.write_text(
        json.dumps([{"slot": "t/r1/b0r1/r1", "retired_to": ["r1.infra1"]}]), encoding="utf-8"
    )
    text = render(runs, retired)
    assert "| model_parse_error | 0 | 1 |" in text
    assert "| context_overflow | 0 | 1 |" in text
    assert "| 合计 | 2 | 2 |" in text
    assert "| t/r1/b0r1/r1 | R1 | 37 | partial |" in text
    assert "| t/r1/b0r1/r2 | R1 | 20 | fail |" in text
    assert "1 个槽位，R0 0 个，R1 1 个" in text
