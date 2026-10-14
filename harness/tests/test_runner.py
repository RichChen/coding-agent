"""Tests for EvalRunner metrics and report generation."""

import json
import tempfile
from pathlib import Path

import pytest

from src.eval.metrics import TaskResult, aggregate_metrics, aggregate_repeated_metrics
from src.eval.report import ReportGenerator, format_est_cost, per_task_pass_matrix
from src.runtime.loop import FailureReason


class TestAggregateMetrics:
    def test_empty_results(self):
        m = aggregate_metrics("test", [])
        assert m.total_tasks == 0
        assert m.success_rate == 0.0

    def test_all_pass(self):
        results = [
            TaskResult(
                task_id="t1", success=True, expected_check=True,
                steps=3, elapsed_ms=1000, tokens=500,
            ),
            TaskResult(
                task_id="t2", success=True, expected_check=True,
                steps=5, elapsed_ms=2000, tokens=800,
            ),
        ]
        m = aggregate_metrics("baseline", results)
        assert m.total_tasks == 2
        assert m.passed == 2
        assert m.success_rate == 100.0
        assert m.avg_steps == 4.0
        assert m.avg_elapsed_ms == 1500.0
        assert m.avg_tokens == 650.0

    def test_cost_estimation(self):
        results = [
            TaskResult(task_id="t1", success=True, expected_check=True, tokens=1000),
            TaskResult(task_id="t2", success=True, expected_check=True, tokens=2000),
        ]
        m = aggregate_metrics("baseline", results, cost_per_1k_tokens=0.5)
        assert m.total_tokens == 3000
        assert m.est_cost == pytest.approx(1.5)

        m_free = aggregate_metrics("baseline", results, cost_per_1k_tokens=0)
        assert m_free.est_cost is None

    def test_mixed_results(self):
        results = [
            TaskResult(
                task_id="t1", success=True, expected_check=True,
                steps=2, elapsed_ms=500, tokens=100,
            ),
            TaskResult(
                task_id="t2", success=False, expected_check=False,
                failure_reason=FailureReason.TIMEOUT,
                steps=10, elapsed_ms=10000, tokens=200,
            ),
        ]
        m = aggregate_metrics("baseline", results)
        assert m.total_tasks == 2
        assert m.passed == 1
        assert m.success_rate == 50.0
        assert m.timeout_count == 1
        assert m.failure_breakdown["timeout"] == 1

    def test_failure_classification(self):
        results = [
            TaskResult(task_id="t1", success=False, failure_reason=FailureReason.TIMEOUT),
            TaskResult(task_id="t2", success=False, failure_reason=FailureReason.TOOL_ERROR),
            TaskResult(task_id="t3", success=False, failure_reason=FailureReason.POLICY_BLOCK, policy_blocks=2),
            TaskResult(task_id="t4", success=False, failure_reason=FailureReason.MODEL_PARSE_ERROR),
            TaskResult(task_id="t5", success=False, failure_reason=FailureReason.STEP_LIMIT),
        ]
        m = aggregate_metrics("test", results)
        assert m.timeout_count == 1
        assert m.tool_error_count == 1
        assert m.policy_block_count == 2  # sum of policy_blocks, not failure_reason count
        assert m.model_error_count == 1
        assert m.step_limit_count == 1

    def test_repeated_metrics(self):
        run1 = aggregate_metrics(
            "baseline",
            [
                TaskResult(task_id="t1", success=True, expected_check=True, steps=2, elapsed_ms=100),
                TaskResult(task_id="t2", success=False, expected_check=False, steps=4, elapsed_ms=300),
            ],
        )
        run2 = aggregate_metrics(
            "baseline",
            [
                TaskResult(task_id="t1", success=True, expected_check=True, steps=3, elapsed_ms=200),
                TaskResult(task_id="t2", success=True, expected_check=True, steps=5, elapsed_ms=400),
            ],
        )

        repeated = aggregate_repeated_metrics("baseline", [run1, run2])

        assert repeated.run_count == 2
        assert repeated.total_tasks == 2
        assert repeated.success_rate.mean == 75.0
        assert round(repeated.success_rate.std, 2) == 35.36
        assert repeated.avg_steps.mean == 3.5


class TestReportGeneration:
    def test_generate_markdown_and_csv(self):
        results = [
            TaskResult(
                task_id="add_hello", success=True, expected_check=True,
                steps=3, elapsed_ms=1500, tokens=600, final_answer="Done",
            ),
        ]
        metrics = aggregate_metrics("baseline", results)

        reporter = ReportGenerator(output_dir=tempfile.mkdtemp())
        md_path, csv_path = reporter.generate([metrics], dataset_name="test")

        md_content = Path(md_path).read_text(encoding="utf-8")
        assert "# Eval Report" in md_content
        assert "baseline" in md_content
        assert "add_hello" in md_content
        assert "100.0%" in md_content

        csv_content = Path(csv_path).read_text(encoding="utf-8")
        assert "add_hello" in csv_content
        assert "True" in csv_content

    def test_generate_repeated_markdown_and_csv(self):
        run1 = aggregate_metrics(
            "baseline",
            [TaskResult(task_id="t1", success=True, expected_check=True, steps=2)],
        )
        run2 = aggregate_metrics(
            "baseline",
            [TaskResult(task_id="t1", success=False, expected_check=False, steps=4)],
        )
        repeated = aggregate_repeated_metrics("baseline", [run1, run2])

        run_b1 = aggregate_metrics(
            "context_compact",
            [TaskResult(task_id="t1", success=True, expected_check=True, steps=3)],
        )
        repeated_b = aggregate_repeated_metrics("context_compact", [run_b1])

        reporter = ReportGenerator(output_dir=tempfile.mkdtemp())
        md_path, csv_path = reporter.generate([repeated, repeated_b], dataset_name="test")

        md_content = Path(md_path).read_text(encoding="utf-8")
        assert "Repeated Run Summary" in md_content
        assert "mean/std" in md_content
        assert "Bootstrap 95% CI" in md_content
        assert "baseline" in md_content

        csv_content = Path(csv_path).read_text(encoding="utf-8")
        assert "run_index" in csv_content
        assert "baseline,1,t1" in csv_content
        assert "baseline,2,t1" in csv_content


class TestFileExistsJudge:
    def test_file_exists_positive(self, tmp_path):
        from src.eval.runner import EvalRunner

        (tmp_path / "test.txt").write_text("hello world")
        result = EvalRunner._check_file_exists(tmp_path, {"path": "test.txt"})
        assert result is True

    def test_file_not_exists(self, tmp_path):
        from src.eval.runner import EvalRunner

        result = EvalRunner._check_file_exists(tmp_path, {"path": "missing.txt"})
        assert result is False

    def test_file_exists_with_min_size(self, tmp_path):
        from src.eval.runner import EvalRunner

        (tmp_path / "small.txt").write_text("hi")
        (tmp_path / "big.txt").write_text("large enough content here")

        assert EvalRunner._check_file_exists(tmp_path, {"path": "small.txt", "min_size_bytes": 100}) is False
        assert EvalRunner._check_file_exists(tmp_path, {"path": "big.txt", "min_size_bytes": 10}) is True


class TestEnhancedJudges:
    def test_file_not_contains(self, tmp_path):
        from src.eval.runner import EvalRunner

        (tmp_path / "poem.txt").write_text("Roses are red\nViolets are blue")

        assert EvalRunner._check_file_not_contains(
            tmp_path,
            {"path": "poem.txt", "keywords": ["debug line"]},
        ) is True
        assert EvalRunner._check_file_not_contains(
            tmp_path,
            {"path": "poem.txt", "keywords": ["Roses"]},
        ) is False

    def test_command_success(self, tmp_path):
        from src.eval.runner import EvalRunner

        assert EvalRunner._check_command_success(
            tmp_path,
            {"command": "python -c \"print('ok')\"", "keywords": ["ok"]},
        ) is True
        assert EvalRunner._check_command_success(
            tmp_path,
            {"command": "python -c \"import sys; sys.exit(2)\""},
        ) is False

    def test_command_output_requires_exit_zero_by_default(self, tmp_path):
        from src.eval.runner import EvalRunner

        assert EvalRunner._check_command_output(
            tmp_path,
            {"command": "python -c \"print('visible'); import sys; sys.exit(1)\""},
        ) is False
        assert EvalRunner._check_command_output(
            tmp_path,
            {
                "command": "python -c \"print('visible'); import sys; sys.exit(1)\"",
                "require_exit_zero": False,
                "keywords": ["visible"],
            },
        ) is True

    def test_yaml_contains(self, tmp_path):
        from src.eval.runner import EvalRunner

        (tmp_path / "config.yaml").write_text("service:\n  name: demo\n  port: 8080\n")

        assert EvalRunner._check_yaml_contains(
            tmp_path,
            {"path": "config.yaml", "keywords": ["port: 8080", "name: demo"]},
        ) is True
        assert EvalRunner._check_yaml_contains(
            tmp_path,
            {"path": "config.yaml", "keywords": ["debug: true"]},
        ) is False

    def test_multi_assert(self, tmp_path):
        from src.eval.runner import EvalRunner
        from src.runtime.loop import AgentRunResult

        (tmp_path / "poem.txt").write_text("Roses are red\nViolets are blue")
        result = AgentRunResult(task_id="t1", success=True, final_answer="Done")

        expected = {
            "type": "multi_assert",
            "assertions": [
                {"type": "file_contains", "path": "poem.txt", "keywords": ["Roses"]},
                {"type": "file_not_contains", "path": "poem.txt", "keywords": ["debug"]},
                {"type": "keywords_in_answer", "keywords": ["done"]},
            ],
        }

        assert EvalRunner._check_expected(tmp_path, result, expected) is True

    def test_multi_assert_partial_failure_returns_failures(self, tmp_path):
        from src.eval.runner import EvalRunner
        from src.runtime.loop import AgentRunResult

        (tmp_path / "poem.txt").write_text("Roses are red\nViolets are blue")
        result = AgentRunResult(task_id="t1", success=True, final_answer="Done")

        expected = {
            "type": "multi_assert",
            "assertions": [
                {"type": "file_contains", "path": "poem.txt", "keywords": ["Roses"]},
                {"type": "file_not_contains", "path": "poem.txt", "keywords": ["Roses"]},
            ],
        }

        ok, failures = EvalRunner._explain_expected(tmp_path, result, expected)
        assert ok is False
        assert len(failures) == 1
        assert "file_not_contains" in failures[0]

    def test_json_equals(self, tmp_path):
        from src.eval.runner import EvalRunner

        (tmp_path / "config.json").write_text('{"version": "1.0", "debug": true}')

        assert EvalRunner._check_json_equals(
            tmp_path,
            {"path": "config.json", "value": {"version": "1.0", "debug": True}},
        ) is True
        assert EvalRunner._check_json_equals(
            tmp_path,
            {"path": "config.json", "value": {"version": "1.0", "debug": False}},
        ) is False

    def test_regex_match(self, tmp_path):
        from src.eval.runner import EvalRunner

        (tmp_path / "script.sh").write_text('echo "She said \\"Hello\\""')

        assert EvalRunner._check_regex_match(
            tmp_path,
            {"path": "script.sh", "pattern": r'echo\s+"She said \\"Hello\\""'},
        ) is True
        assert EvalRunner._check_regex_match(
            tmp_path,
            {"path": "script.sh", "pattern": r"debug"},
        ) is False

    def test_copy_fixture_dir(self, tmp_path):
        from src.eval.runner import EvalRunner

        fixture = tmp_path / "fixture"
        fixture.mkdir()
        (fixture / "app.py").write_text("print('hello')")
        (fixture / "pkg").mkdir()
        (fixture / "pkg" / "__init__.py").write_text("")

        workspace = tmp_path / "workspace"
        workspace.mkdir()
        EvalRunner._copy_fixture_dir(workspace, fixture)

        assert (workspace / "app.py").read_text() == "print('hello')"
        assert (workspace / "pkg" / "__init__.py").exists()


class TestRestoreProtectedPaths:
    def test_restore_protected_paths_overwrites_tampered_test(self, tmp_path):
        from src.eval.runner import EvalRunner

        fixture = tmp_path / "fixture"
        workspace = tmp_path / "workspace"
        rel = "pkg/tests/test_x.py"
        fixture_file = fixture / rel
        workspace_file = workspace / rel
        fixture_file.parent.mkdir(parents=True)
        workspace_file.parent.mkdir(parents=True)
        fixture_file.write_text("assert_real_behavior\n", encoding="utf-8")
        workspace_file.write_text("def test_x():\n    assert True\n", encoding="utf-8")

        task = {"protected_paths": [rel]}
        EvalRunner._restore_protected_paths(workspace, fixture, task)

        assert workspace_file.read_text(encoding="utf-8") == "assert_real_behavior\n"

    def test_restore_protected_paths_noop_when_empty(self, tmp_path):
        from src.eval.runner import EvalRunner

        workspace = tmp_path / "workspace"
        workspace.mkdir()
        tampered = workspace / "pkg/tests/test_x.py"
        tampered.parent.mkdir(parents=True)
        tampered.write_text("def test_x():\n    assert True\n", encoding="utf-8")

        EvalRunner._restore_protected_paths(workspace, tmp_path / "fixture", {})
        EvalRunner._restore_protected_paths(workspace, tmp_path / "fixture", {"protected_paths": []})

        assert tampered.read_text(encoding="utf-8") == "def test_x():\n    assert True\n"


class TestPlanActConfig:
    def test_plan_act_config_builds_planner(self, tmp_path):
        from src.harness.factory import build_agent, load_config

        config = load_config("configs/plan_act.yaml")
        agent = build_agent(config, tmp_path)

        assert agent.runtime_mode == "plan_act"
        assert agent.planner is not None


class TestTagGrouping:
    def test_success_rate_by_tag(self):
        from src.eval.report import success_rate_by_tag

        results = [
            TaskResult(task_id="t1", success=True, expected_check=True, tags=["repo", "easy"]),
            TaskResult(task_id="t2", success=True, expected_check=False, tags=["repo"]),
            TaskResult(task_id="t3", success=False, expected_check=False, tags=["easy"]),
        ]
        by_tag = success_rate_by_tag(results)
        assert by_tag["repo"]["passed"] == 1
        assert by_tag["repo"]["total"] == 2
        assert by_tag["easy"]["rate"] == 50.0


class TestAstJudges:
    def test_python_ast_valid_passes(self, tmp_path):
        from src.eval.runner import EvalRunner

        (tmp_path / "good.py").write_text("def ok():\n    return 1\n")
        ok, failures = EvalRunner._explain_python_ast_valid(tmp_path, {"path": "good.py"})
        assert ok is True
        assert failures == []

    def test_python_ast_valid_fails_on_syntax_error(self, tmp_path):
        from src.eval.runner import EvalRunner

        (tmp_path / "bad.py").write_text("def broken(:\n")
        ok, failures = EvalRunner._explain_python_ast_valid(tmp_path, {"path": "bad.py"})
        assert ok is False
        assert failures[0].startswith("python_ast_valid:")

    def test_python_defines(self, tmp_path):
        from src.eval.runner import EvalRunner

        (tmp_path / "mod.py").write_text("def helper():\n    return 1\n")
        ok, failures = EvalRunner._explain_python_defines(
            tmp_path,
            {"path": "mod.py", "names": ["helper"]},
        )
        assert ok is True
        assert failures == []
        ok, failures = EvalRunner._explain_python_defines(
            tmp_path,
            {"path": "mod.py", "names": ["missing"]},
        )
        assert ok is False


class TestUnstableTasks:
    def test_marks_partial_pass_as_unstable(self):
        from src.eval.report import unstable_tasks

        run1 = aggregate_metrics(
            "baseline",
            [
                TaskResult(task_id="t1", success=True, expected_check=True),
                TaskResult(task_id="t2", success=False, expected_check=False),
            ],
        )
        run2 = aggregate_metrics(
            "baseline",
            [
                TaskResult(task_id="t1", success=False, expected_check=False),
                TaskResult(task_id="t2", success=True, expected_check=True),
            ],
        )
        repeated = aggregate_repeated_metrics("baseline", [run1, run2])
        unstable = unstable_tasks(repeated)
        assert ("t1", 1, 2) in unstable
        assert ("t2", 1, 2) in unstable

    def test_unstable_tasks_table_includes_config_column(self):
        run_a1 = aggregate_metrics(
            "baseline",
            [TaskResult(task_id="t1", success=True, expected_check=True)],
        )
        run_a2 = aggregate_metrics(
            "baseline",
            [TaskResult(task_id="t1", success=False, expected_check=False)],
        )
        run_b1 = aggregate_metrics(
            "plan_act",
            [TaskResult(task_id="t1", success=True, expected_check=True)],
        )
        run_b2 = aggregate_metrics(
            "plan_act",
            [TaskResult(task_id="t1", success=False, expected_check=False)],
        )
        repeated_a = aggregate_repeated_metrics("baseline", [run_a1, run_a2])
        repeated_b = aggregate_repeated_metrics("plan_act", [run_b1, run_b2])

        reporter = ReportGenerator(output_dir=tempfile.mkdtemp())
        md_path, _ = reporter.generate(
            [repeated_a, repeated_b],
            dataset_name="test",
            run_metadata={"runs": 2},
        )
        md_content = Path(md_path).read_text(encoding="utf-8")
        assert "## Unstable Tasks" in md_content
        assert "| Config | Task ID | Passes | Runs |" in md_content
        assert "| baseline | t1 | 1 | 2 |" in md_content
        assert "| plan_act | t1 | 1 | 2 |" in md_content

    def test_model_matrix_section_when_models_differ(self):
        run_a1 = aggregate_metrics(
            "baseline",
            [TaskResult(task_id="t1", success=True, expected_check=True, tokens=100)],
        )
        run_a2 = aggregate_metrics(
            "baseline",
            [TaskResult(task_id="t1", success=True, expected_check=True, tokens=120)],
        )
        run_b1 = aggregate_metrics(
            "baseline_modelB",
            [TaskResult(task_id="t1", success=False, expected_check=False, tokens=90)],
        )
        run_b2 = aggregate_metrics(
            "baseline_modelB",
            [TaskResult(task_id="t1", success=True, expected_check=True, tokens=110)],
        )
        repeated_a = aggregate_repeated_metrics("baseline", [run_a1, run_a2])
        repeated_b = aggregate_repeated_metrics("baseline_modelB", [run_b1, run_b2])

        reporter = ReportGenerator(output_dir=tempfile.mkdtemp())
        md_path, _ = reporter.generate(
            [repeated_a, repeated_b],
            dataset_name="test",
            run_metadata={
                "runs": 2,
                "configs": {
                    "baseline": {"model": "model-a", "config_hash": "aaa"},
                    "baseline_modelB": {"model": "model-b", "config_hash": "bbb"},
                },
            },
        )
        md_content = Path(md_path).read_text(encoding="utf-8")
        assert "## Model Matrix" in md_content
        assert "model-a" in md_content
        assert "model-b" in md_content


class TestReportMetadata:
    def test_report_includes_metadata_and_significance(self):
        run_a = aggregate_metrics(
            "baseline",
            [TaskResult(task_id="t1", success=True, expected_check=True, tags=["repo"])],
        )
        run_b = aggregate_metrics(
            "baseline",
            [TaskResult(task_id="t1", success=False, expected_check=False, tags=["repo"])],
        )
        repeated_a = aggregate_repeated_metrics("baseline", [run_a, run_b])
        repeated_b = aggregate_repeated_metrics("hardened", [run_a, run_b])

        reporter = ReportGenerator(output_dir=tempfile.mkdtemp())
        md_path, _ = reporter.generate(
            [repeated_a, repeated_b],
            dataset_name="test",
            run_metadata={
                "git_commit": "abc1234",
                "runs": 2,
                "timestamp": "2026-06-25T00:00:00Z",
                "configs": {
                    "baseline": {"model": "mock", "config_hash": "deadbeef"},
                },
            },
        )
        md_content = Path(md_path).read_text(encoding="utf-8")
        assert "## Run Metadata" in md_content
        assert "abc1234" in md_content
        assert "Success Rate by Tag" in md_content
        assert "Unstable Tasks" in md_content
        assert "Significance:" in md_content


class TestCostAndPassMatrix:
    def test_format_est_cost(self):
        assert format_est_cost(None) == "n/a"
        assert format_est_cost(1.2345) == "$1.2345"

    def test_per_task_pass_matrix_three_runs(self):
        runs = []
        for passed_t2 in [False, True, False]:
            runs.append(
                aggregate_metrics(
                    "baseline",
                    [
                        TaskResult(task_id="t1", success=True, expected_check=True),
                        TaskResult(
                            task_id="t2",
                            success=passed_t2,
                            expected_check=passed_t2,
                        ),
                    ],
                )
            )
        repeated = aggregate_repeated_metrics("baseline", runs)
        matrix = per_task_pass_matrix(repeated)

        assert len(matrix) == 2
        t1_row = next(r for r in matrix if r[0] == "t1")
        t2_row = next(r for r in matrix if r[0] == "t2")
        assert t1_row[1] == ["P", "P", "P"]
        assert t1_row[2] == "3/3"
        assert t2_row[1] == ["F", "P", "F"]
        assert t2_row[2] == "1/3"

    def test_report_includes_cost_and_pass_matrix(self):
        run1 = aggregate_metrics(
            "baseline",
            [
                TaskResult(task_id="t1", success=True, expected_check=True, tokens=1000),
                TaskResult(task_id="t2", success=False, expected_check=False, tokens=500),
            ],
            cost_per_1k_tokens=0.5,
        )
        run2 = aggregate_metrics(
            "baseline",
            [
                TaskResult(task_id="t1", success=True, expected_check=True, tokens=1200),
                TaskResult(task_id="t2", success=True, expected_check=True, tokens=600),
            ],
            cost_per_1k_tokens=0.5,
        )
        repeated = aggregate_repeated_metrics("baseline", [run1, run2], cost_per_1k_tokens=0.5)

        reporter = ReportGenerator(output_dir=tempfile.mkdtemp())
        md_path, _ = reporter.generate(
            [repeated],
            dataset_name="test",
            run_metadata={"cost_per_1k_tokens": 0.5, "runs": 2},
        )
        md_content = Path(md_path).read_text(encoding="utf-8")
        assert "## Cost Summary" in md_content
        assert "Est. cost:" in md_content
        assert "## Per-Task Pass Matrix" in md_content
        assert "| t1 | P | P | 2/2 |" in md_content
