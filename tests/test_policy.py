"""Tests for CommandPolicy and Budget."""

import pytest

from src.policy.rules import CommandPolicy
from src.policy.budget import Budget, BudgetExhausted


class TestCommandPolicy:
    def test_allow_all_mode(self):
        policy = CommandPolicy(allow_all=True)
        assert policy.check("ls -la").allowed
        assert policy.check("python script.py").allowed

    def test_block_dangerous_in_allow_all(self):
        policy = CommandPolicy(allow_all=True, blocked_patterns=["rm -rf /"])
        assert not policy.check("rm -rf /").allowed
        assert policy.check("ls").allowed

    def test_whitelist_mode(self):
        policy = CommandPolicy(
            allow_all=False,
            allowed_prefixes=["ls", "cat", "python"],
        )
        assert policy.check("ls -la").allowed
        assert policy.check("cat file.txt").allowed
        assert policy.check("python main.py").allowed

    def test_whitelist_blocks_unknown(self):
        policy = CommandPolicy(
            allow_all=False,
            allowed_prefixes=["ls", "cat"],
        )
        decision = policy.check("rm file.txt")
        assert not decision.allowed
        assert "does not match" in decision.reason

    def test_empty_command_blocked(self):
        policy = CommandPolicy()
        assert not policy.check("").allowed
        assert not policy.check("  ").allowed

    def test_blocked_pattern_case_insensitive(self):
        policy = CommandPolicy(blocked_patterns=["sudo"])
        assert not policy.check("SUDO rm -rf /").allowed

    def test_command_with_args_matches_prefix(self):
        policy = CommandPolicy(allow_all=False, allowed_prefixes=["git"])
        assert policy.check("git status").allowed
        assert policy.check("git diff HEAD~1").allowed

    def test_check_argv_matches_basename(self):
        policy = CommandPolicy(allow_all=False, allowed_prefixes=["python"])
        assert policy.check_argv(["python", "-c", "print(1)"]).allowed
        assert not policy.check_argv(["curl", "https://example.com"]).allowed


class TestBudget:
    def test_steps_count(self):
        budget = Budget(max_steps=5)
        budget.start()
        for _ in range(5):
            budget.start_step()
        assert budget.step_count == 5

    def test_step_limit_exceeded(self):
        budget = Budget(max_steps=2)
        budget.start()
        budget.start_step()
        budget.start_step()
        with pytest.raises(BudgetExhausted, match="Step limit"):
            budget.start_step()

    def test_total_timeout(self):
        budget = Budget(max_steps=100, total_timeout_seconds=0.0)
        budget.start()
        budget._start_time -= 1.0  # Simulate elapsed time
        with pytest.raises(BudgetExhausted, match="timeout"):
            budget.start_step()

    def test_summary(self):
        budget = Budget(max_steps=10)
        budget.start()
        budget.start_step()
        s = budget.summary()
        assert s["steps"] == 1
        assert s["max_steps"] == 10
        assert "elapsed_s" in s
