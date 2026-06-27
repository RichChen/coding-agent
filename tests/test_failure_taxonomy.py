"""Tests for failure taxonomy generator."""

import csv
from io import StringIO
from pathlib import Path

from scripts.gen_failure_taxonomy import build_taxonomy, load_failure_rows


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames = [
        "config",
        "run_index",
        "task_id",
        "success",
        "expected_check",
        "steps",
        "elapsed_ms",
        "tokens",
        "tool_failures",
        "policy_blocks",
        "failure_reason",
        "expected_failures",
        "trace_file",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


class TestFailureTaxonomy:
    def test_builds_reason_and_assert_counts(self, tmp_path):
        csv_path = tmp_path / "sample.csv"
        _write_csv(
            csv_path,
            [
                {
                    "config": "baseline",
                    "run_index": "1",
                    "task_id": "t_step",
                    "success": "False",
                    "expected_check": "False",
                    "steps": "40",
                    "elapsed_ms": "1000",
                    "tokens": "100",
                    "tool_failures": "2",
                    "policy_blocks": "0",
                    "failure_reason": "step_limit",
                    "expected_failures": "command_success failed: python -m pytest -q",
                    "trace_file": "traces/t.jsonl",
                },
                {
                    "config": "plan_act",
                    "run_index": "1",
                    "task_id": "t_judge",
                    "success": "True",
                    "expected_check": "False",
                    "steps": "12",
                    "elapsed_ms": "900",
                    "tokens": "80",
                    "tool_failures": "1",
                    "policy_blocks": "0",
                    "failure_reason": "none",
                    "expected_failures": "file_contains: missing keyword 'foo' in app.py",
                    "trace_file": "traces/t2.jsonl",
                },
                {
                    "config": "plan_act",
                    "run_index": "1",
                    "task_id": "t_pass",
                    "success": "True",
                    "expected_check": "True",
                    "steps": "5",
                    "elapsed_ms": "500",
                    "tokens": "50",
                    "tool_failures": "0",
                    "policy_blocks": "0",
                    "failure_reason": "none",
                    "expected_failures": "",
                    "trace_file": "traces/t3.jsonl",
                },
            ],
        )

        rows = load_failure_rows([csv_path])
        md = build_taxonomy(rows, [csv_path])

        assert len(rows) == 2
        assert "## By failure_reason" in md
        assert "| step_limit | 1 |" in md
        assert "| none | 1 |" in md
        assert "## By assert type" in md
        assert "| command_success | 1 |" in md
        assert "| file_contains | 1 |" in md
        assert "t_step" in md
        assert "t_judge" in md
        assert "t_pass" not in md
