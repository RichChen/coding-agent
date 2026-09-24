"""Tests for memory matching and hint quality."""

from __future__ import annotations

from reposkill_agent.core.contracts import TaskSpec
from reposkill_agent.eval.injection_policy import (
    memory_warmup_tasks_for_eval,
    seed_pair_tasks_for_eval,
)
from reposkill_agent.memory.matching import (
    extract_test_signals,
    procedural_applies,
    repo_convention_for_path,
    seed_pair_task_id,
)


def test_seed_pair_task_id_maps_holdout_to_seed():
    assert seed_pair_task_id("inv_api_tax_holdout_01") == "inv_api_tax_01"
    assert seed_pair_task_id("inv_rename_holdout_01") == "inv_rename_01"


def test_repo_convention_for_medium_inventory():
    text = repo_convention_for_path("benchmarks/repos/medium_inventory")
    assert "Result" in text


def test_extract_test_signals_result_convention():
    output = "AttributeError: 'int' object has no attribute 'ok'"
    signals = extract_test_signals(output)
    assert any("Result" in signal for signal in signals)


def test_procedural_applies_by_domain_tag():
    task = TaskSpec(
        id="holdout",
        issue="x",
        repo_path="repos/medium_inventory",
        test_command="pytest",
        tags=["memory_heavy", "inventory", "repeated"],
    )
    assert procedural_applies(["inventory", "support"], task)
    assert not procedural_applies(["config"], task)


def test_memory_warmup_includes_support_and_seed_pairs():
    eval_tasks = [
        TaskSpec(
            id="inv_api_tax_holdout_01",
            issue="x",
            repo_path="repos/medium_inventory",
            test_command="pytest",
            tags=["memory_heavy", "inventory", "repeated"],
        )
    ]
    catalog = eval_tasks + [
        TaskSpec(
            id="inv_api_tax_01",
            issue="seed",
            repo_path="repos/medium_inventory",
            test_command="pytest",
            tags=["skill_heavy", "inventory"],
        ),
        TaskSpec(
            id="inv_regression_cart_01",
            issue="support",
            repo_path="repos/medium_inventory",
            test_command="pytest",
            tags=["support", "inventory"],
        ),
    ]
    seeds = seed_pair_tasks_for_eval(eval_tasks, catalog)
    warmup = memory_warmup_tasks_for_eval(eval_tasks, catalog)
    assert any(t.id == "inv_api_tax_01" for t in seeds)
    assert any(t.id == "inv_regression_cart_01" for t in warmup)
    assert warmup[0].id == "inv_regression_cart_01"
