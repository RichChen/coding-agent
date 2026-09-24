"""Tests for L5 category-aware augmentation policy."""

from __future__ import annotations

from pathlib import Path

from reposkill_agent.core.contracts import TaskSpec
from reposkill_agent.eval.injection_policy import (
    apply_skill_policy,
    cap_skill_selection,
    resolve_augmentation_policy,
    warmup_tasks_for_eval,
)
from reposkill_agent.memory import EpisodicStore, MemoryRetriever, ProceduralStore, RepoProfileStore
from reposkill_agent.memory.episodic import EpisodicMemory
from reposkill_agent.memory.procedural import ProceduralMemory
from reposkill_agent.memory.repo_profile import RepoProfileMemory
from reposkill_agent.skills.models import SkillSelection, SkillSpec


def test_augmentation_policy_routes_by_category():
    skill_task = TaskSpec(
        id="t",
        issue="x",
        repo_path="r",
        test_command="pytest",
        tags=["skill_heavy"],
    )
    policy = resolve_augmentation_policy(skill_task, full_stack=True)
    assert policy is not None
    assert policy.name == "skill_primary"
    assert policy.allow_skills is True
    assert policy.allow_memory is False
    assert policy.max_memory_hints == 0

    memory_task = TaskSpec(
        id="t",
        issue="x",
        repo_path="r",
        test_command="pytest",
        tags=["memory_heavy"],
    )
    policy = resolve_augmentation_policy(memory_task, full_stack=True)
    assert policy.name == "memory_primary"
    assert policy.allow_skills is False
    assert policy.max_memory_hints == 3

    context_task = TaskSpec(
        id="t",
        issue="x",
        repo_path="r",
        test_command="pytest",
        tags=["context_heavy"],
    )
    context_policy = resolve_augmentation_policy(context_task, full_stack=True)
    assert context_policy.name == "context_primary"
    assert context_policy.allow_skills is False
    assert context_policy.allow_memory is False
    assert context_policy.max_memory_hints == 0

    recovery = resolve_augmentation_policy(
        context_task,
        full_stack=True,
        context_recovery_patch=True,
    )
    assert recovery.name == "context_recovery_minimal"
    assert recovery.allow_skills is False
    assert recovery.allow_memory is False


def test_multi_file_api_uses_memory_only_not_mix():
    task = TaskSpec(
        id="evt_serialization_01",
        issue="x",
        repo_path="repos/medium_event_pipeline",
        test_command="pytest",
        tags=["multi_file_api", "events"],
    )
    policy = resolve_augmentation_policy(task, full_stack=True)
    assert policy.name == "api_memory_primary"
    assert policy.allow_skills is False
    assert policy.allow_memory is True
    assert policy.exclude_repo_profile is True


def test_repo_convention_uses_memory_only_not_mix():
    task = TaskSpec(
        id="evt_retry_policy_01",
        issue="x",
        repo_path="repos/medium_event_pipeline",
        test_command="pytest",
        tags=["repo_convention", "events"],
    )
    policy = resolve_augmentation_policy(task, full_stack=True)
    assert policy.name == "convention_memory_primary"
    assert policy.allow_skills is False
    assert policy.max_skills == 0


def test_apply_skill_policy_suppresses_context_primary():
    skills = [
        SkillSpec(id=f"s{i}", name=f"S{i}", version="0.1", purpose="p")
        for i in range(2)
    ]
    selection = SkillSelection(
        selected=skills,
        retrieved_count=2,
        validated_count=2,
        candidate_count=2,
        injected_count=2,
        gated_count=0,
    )
    policy = resolve_augmentation_policy(
        TaskSpec(id="t", issue="x", repo_path="r", test_command="pytest", tags=["context_heavy"]),
        full_stack=True,
    )
    capped, suppressed = apply_skill_policy(selection, policy)
    assert capped.injected_count == 0
    assert suppressed == 2


def test_cap_skill_selection_trims_injected():
    skills = [
        SkillSpec(id=f"s{i}", name=f"S{i}", version="0.1", purpose="p")
        for i in range(3)
    ]
    base = SkillSelection(
        selected=skills,
        retrieved_count=3,
        validated_count=3,
        candidate_count=3,
        injected_count=3,
        gated_count=0,
    )
    capped = cap_skill_selection(base, 1)
    assert capped.injected_count == 1
    assert capped.gated_count == 2


def test_memory_full_stack_excludes_episodic_failures(tmp_path: Path):
    memory_dir = tmp_path / "memory"
    episodic = EpisodicStore(memory_dir)
    procedural = ProceduralStore(memory_dir)
    profile_store = RepoProfileStore(memory_dir)
    profile_store.upsert(
        RepoProfileMemory(
            repo_fingerprint="fp1",
            test_commands=["pytest -q"],
            top_level_entries=["app"],
            common_files=["app/x.py"],
        )
    )
    procedural.append(
        ProceduralMemory(
            id="p1",
            source_task_ids=["prev"],
            pattern="api migration",
            reusable_workflow=["patch"],
            applies_when=["api"],
            verifier="tests_pass",
            confidence=0.9,
        )
    )
    episodic.append(
        EpisodicMemory(
            task_id="failed",
            repo_fingerprint="fp1",
            issue_summary="failed",
            plan_summary="plan",
            actions=[],
            final_diff_summary="",
            tests=[],
            outcome="failure",
            failure_type="test_failure",
        )
    )
    retriever = MemoryRetriever(episodic, procedural, profile_store)
    task = TaskSpec(
        id="current",
        issue="api",
        repo_path="/repo",
        test_command="pytest",
        tags=["skill_heavy"],
    )
    open_selection = retriever.select(task, "fp1", max_hints=3)
    gated_selection = retriever.select(
        task,
        "fp1",
        max_hints=1,
        repo_profile_only=True,
        exclude_episodic_failures=True,
        procedural_only=True,
    )
    assert open_selection.injected_count >= 2
    assert gated_selection.injected_count == 1
    assert gated_selection.injected[0]["type"] == "repo_profile"


def test_warmup_tasks_for_eval_picks_support_in_same_repo():
    eval_tasks = [
        TaskSpec(
            id="inv_api_tax_01",
            issue="x",
            repo_path="repos/medium_inventory",
            test_command="pytest",
            tags=["memory_heavy"],
        )
    ]
    catalog = eval_tasks + [
        TaskSpec(
            id="inv_regression_cart_01",
            issue="support",
            repo_path="repos/medium_inventory",
            test_command="pytest",
            tags=["support"],
        ),
        TaskSpec(
            id="other",
            issue="x",
            repo_path="repos/other",
            test_command="pytest",
            tags=["support"],
        ),
    ]
    warmup = warmup_tasks_for_eval(eval_tasks, catalog)
    assert len(warmup) == 1
    assert warmup[0].id == "inv_regression_cart_01"
