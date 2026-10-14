"""Tests for eval metrics aggregation and degenerate run detection."""

from src.eval.metrics import (
    EvalMetrics,
    TaskResult,
    aggregate_repeated_metrics,
    is_degenerate_run,
)
from src.eval.report import significance_conclusion


def _run_metrics(
    *,
    success_rate: float,
    avg_steps: float,
    model_errors: int = 0,
    total_tasks: int = 10,
) -> EvalMetrics:
    passed = int(total_tasks * success_rate / 100)
    results = [
        TaskResult(task_id=f"t{i}", success=i < passed, expected_check=i < passed)
        for i in range(total_tasks)
    ]
    return EvalMetrics(
        config_name="test",
        total_tasks=total_tasks,
        passed=passed,
        failed=total_tasks - passed,
        success_rate=success_rate,
        avg_steps=avg_steps,
        model_error_count=model_errors,
        results=results,
    )


class TestDegenerateRun:
    def test_detects_provider_collapse(self):
        run = _run_metrics(success_rate=0.0, avg_steps=1.0)
        assert is_degenerate_run(run) is True

    def test_does_not_flag_hard_all_failed_run(self):
        run = _run_metrics(success_rate=0.0, avg_steps=15.0)
        assert is_degenerate_run(run) is False

    def test_aggregate_excludes_degenerate_runs(self):
        runs = [
            _run_metrics(success_rate=30.0, avg_steps=20.0),
            _run_metrics(success_rate=30.0, avg_steps=18.0),
            _run_metrics(success_rate=0.0, avg_steps=1.0),
            _run_metrics(success_rate=0.0, avg_steps=1.0),
            _run_metrics(success_rate=0.0, avg_steps=1.0),
        ]
        repeated = aggregate_repeated_metrics("plan_act", runs)
        assert repeated.degenerate_run_indices == [3, 4, 5]
        assert repeated.valid_run_count == 2
        assert repeated.success_rate.mean == 30.0
        assert repeated.success_rate_ci is not None

    def test_significance_withheld_when_valid_runs_insufficient(self):
        runs = [
            _run_metrics(success_rate=30.0, avg_steps=20.0),
            _run_metrics(success_rate=0.0, avg_steps=1.0),
            _run_metrics(success_rate=0.0, avg_steps=1.0),
            _run_metrics(success_rate=0.0, avg_steps=1.0),
            _run_metrics(success_rate=0.0, avg_steps=1.0),
        ]
        repeated = aggregate_repeated_metrics("plan_act", runs)
        conclusion = significance_conclusion(
            repeated.success_rate_ci,
            repeated.success_rate_ci,
            valid_run_count_a=5,
            valid_run_count_b=repeated.valid_run_count,
        )
        assert "withheld" in conclusion
        assert "倾向显著" not in conclusion
