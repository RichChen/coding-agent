"""Tests for bootstrap confidence intervals."""

from src.eval.bootstrap import (
    bootstrap_mean_ci,
    bootstrap_paired_success_rate_delta_ci,
    bootstrap_proportion_ci,
)


class TestBootstrap:
    def test_proportion_ci_contains_observed_rate(self):
        ci = bootstrap_proportion_ci(8, 10, seed=42)
        assert ci is not None
        assert ci.low <= 80.0 <= ci.high

    def test_mean_ci_for_repeated_runs(self):
        ci = bootstrap_mean_ci([90.0, 100.0, 87.5], seed=42)
        assert ci is not None
        assert ci.low <= 92.5 <= ci.high

    def test_paired_delta_ci(self):
        passed_a = [True, True, False, True]
        passed_b = [True, False, False, True]
        ci = bootstrap_paired_success_rate_delta_ci(passed_a, passed_b, seed=42)
        assert ci is not None
        assert ci.low <= 0.0 <= ci.high
