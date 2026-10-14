"""Tests for timeout and retry behavior."""

import asyncio

import pytest

from src.policy.budget import Budget, BudgetExhausted
from src.runtime.retry import RetryConfig, RetryPolicy


class TestRetryPolicy:
    def test_classify_timeout(self):
        assert RetryPolicy._classify(TimeoutError("timed out")) == "timeout"
        assert RetryPolicy._classify(Exception("request timed out")) == "timeout"

    def test_classify_model_error(self):
        assert RetryPolicy._classify(Exception("model error")) == "model_error"
        assert RetryPolicy._classify(Exception("api parse error")) == "model_error"

    def test_classify_unknown(self):
        assert RetryPolicy._classify(ValueError("something")) == "unknown"

    def test_should_retry(self):
        config = RetryConfig(retry_on=["timeout", "model_error"])
        policy = RetryPolicy(config)
        assert policy.should_retry(Exception("timed out"))
        assert policy.should_retry(Exception("model error"))
        assert not policy.should_retry(ValueError("bad input"))

    @pytest.mark.asyncio
    async def test_retry_with_success(self):
        calls = []

        async def flaky():
            calls.append(1)
            if len(calls) < 3:
                raise Exception("timed out")
            return "ok"

        config = RetryConfig(max_retries=3, backoff_base_seconds=0.01)
        policy = RetryPolicy(config)
        result = await policy.execute(flaky)
        assert result == "ok"
        assert len(calls) == 3

    @pytest.mark.asyncio
    async def test_retry_exhausted(self):
        async def always_fails():
            raise Exception("timed out")

        config = RetryConfig(max_retries=1, backoff_base_seconds=0.01)
        policy = RetryPolicy(config)
        with pytest.raises(Exception, match="timed out"):
            await policy.execute(always_fails)

    @pytest.mark.asyncio
    async def test_no_retry_on_non_retryable(self):
        calls = []

        async def value_error():
            calls.append(1)
            raise ValueError("bad input")

        config = RetryConfig(max_retries=3, retry_on=["timeout"])
        policy = RetryPolicy(config)
        with pytest.raises(ValueError):
            await policy.execute(value_error)
        assert len(calls) == 1  # No retries


class TestStepTimeout:
    def test_step_timeout_raises(self):
        budget = Budget(max_steps=10, step_timeout_seconds=0.0)
        budget.start()
        budget.start_step()
        budget._last_step_start -= 10.0  # Simulate step taking too long
        with pytest.raises(BudgetExhausted, match="Step timeout"):
            budget.check_step_timeout()
