"""Category-aware augmentation policy for L5 full-stack runs."""

from __future__ import annotations

from dataclasses import dataclass

from reposkill_agent.core.contracts import TaskSpec
from reposkill_agent.eval.task_category import task_category
from reposkill_agent.memory.matching import seed_pair_task_id
from reposkill_agent.memory.models import MemorySelection
from reposkill_agent.skills.models import SkillSelection


@dataclass(frozen=True)
class AugmentationPolicy:
    """Router decision for skill/memory injection on a patch attempt."""

    name: str
    allow_skills: bool
    max_skills: int
    allow_memory: bool
    max_memory_hints: int
    memory_repo_profile_only: bool
    exclude_episodic_failures: bool
    procedural_only: bool = False
    exclude_repo_profile: bool = False


def _memory_primary_policy(
    *,
    name: str = "memory_primary",
    max_memory_hints: int = 3,
    exclude_repo_profile: bool = False,
) -> AugmentationPolicy:
    return AugmentationPolicy(
        name=name,
        allow_skills=False,
        max_skills=0,
        allow_memory=True,
        max_memory_hints=max_memory_hints,
        memory_repo_profile_only=False,
        exclude_episodic_failures=True,
        procedural_only=False,
        exclude_repo_profile=exclude_repo_profile,
    )


def _context_minimal_policy(*, name: str = "context_primary") -> AugmentationPolicy:
    return AugmentationPolicy(
        name=name,
        allow_skills=False,
        max_skills=0,
        allow_memory=False,
        max_memory_hints=0,
        memory_repo_profile_only=False,
        exclude_episodic_failures=True,
        exclude_repo_profile=True,
    )


# Backward-compatible alias used in earlier batches.
InjectionBudget = AugmentationPolicy


def resolve_augmentation_policy(
    task: TaskSpec,
    *,
    full_stack: bool,
    context_recovery_patch: bool = False,
) -> AugmentationPolicy | None:
    """Route augmentation by task category; return None when not in L5 full-stack mode."""
    if not full_stack:
        return None
    category = task_category(task.tags)
    if context_recovery_patch:
        if category == "memory_heavy":
            return AugmentationPolicy(
                name="memory_context_recovery",
                allow_skills=False,
                max_skills=0,
                allow_memory=True,
                max_memory_hints=2,
                memory_repo_profile_only=False,
                exclude_episodic_failures=True,
                procedural_only=False,
            )
        return AugmentationPolicy(
            name="context_recovery_minimal",
            allow_skills=False,
            max_skills=0,
            allow_memory=False,
            max_memory_hints=0,
            memory_repo_profile_only=False,
            exclude_episodic_failures=True,
        )
    category = task_category(task.tags)
    if category == "skill_heavy":
        return AugmentationPolicy(
            name="skill_primary",
            allow_skills=True,
            max_skills=1,
            allow_memory=False,
            max_memory_hints=0,
            memory_repo_profile_only=False,
            exclude_episodic_failures=True,
            exclude_repo_profile=True,
        )
    if category == "memory_heavy":
        return _memory_primary_policy()
    if category == "context_heavy":
        return _context_minimal_policy()
    if category == "multi_file_api":
        # L4-like: memory-only avoids skill/memory combo weaker than memory ablation.
        return _memory_primary_policy(
            name="api_memory_primary",
            max_memory_hints=2,
            exclude_repo_profile=True,
        )
    if category == "repo_convention":
        return _memory_primary_policy(
            name="convention_memory_primary",
            max_memory_hints=2,
            exclude_repo_profile=True,
        )
    if category == "traceback_repair":
        return _context_minimal_policy(name="traceback_minimal")
    return _memory_primary_policy(
        name="legacy_memory_primary",
        max_memory_hints=2,
        exclude_repo_profile=True,
    )


def full_stack_injection_budget(task: TaskSpec) -> AugmentationPolicy:
    """Backward-compatible entry point."""
    policy = resolve_augmentation_policy(task, full_stack=True)
    assert policy is not None
    return policy


def cap_skill_selection(selection: SkillSelection, max_skills: int) -> SkillSelection:
    """Trim validated skills to the category budget."""
    if len(selection.selected) <= max_skills:
        return selection
    capped = selection.selected[:max_skills]
    return SkillSelection(
        selected=capped,
        retrieved_count=selection.retrieved_count,
        validated_count=selection.validated_count,
        candidate_count=selection.candidate_count,
        injected_count=len(capped),
        gated_count=selection.candidate_count - len(capped),
        rejected=selection.rejected,
    )


def apply_skill_policy(
    selection: SkillSelection,
    policy: AugmentationPolicy | None,
) -> tuple[SkillSelection, int]:
    """Apply router policy to a validated skill selection; return suppressed count."""
    if policy is None:
        return selection, 0
    if not policy.allow_skills or policy.max_skills <= 0:
        suppressed = selection.injected_count
        if suppressed == 0:
            return selection, 0
        return SkillSelection(
            selected=[],
            retrieved_count=selection.retrieved_count,
            validated_count=selection.validated_count,
            candidate_count=selection.candidate_count,
            injected_count=0,
            gated_count=selection.candidate_count,
            rejected=selection.rejected,
        ), suppressed
    capped = cap_skill_selection(selection, policy.max_skills)
    suppressed = max(0, selection.injected_count - capped.injected_count)
    return capped, suppressed


def empty_skill_selection() -> SkillSelection:
    return SkillSelection(
        selected=[],
        retrieved_count=0,
        validated_count=0,
        candidate_count=0,
        injected_count=0,
        gated_count=0,
    )


def apply_memory_policy(
    selection: MemorySelection,
    policy: AugmentationPolicy | None,
) -> tuple[list[dict], int]:
    """Apply router policy to memory hints; return injected hints and suppressed count."""
    if policy is None:
        return list(selection.injected), 0
    if not policy.allow_memory or policy.max_memory_hints <= 0:
        return [], selection.injected_count
    hints = list(selection.injected)[: policy.max_memory_hints]
    suppressed = max(0, selection.injected_count - len(hints))
    return hints, suppressed


def warmup_tasks_for_eval(
    eval_tasks: list[TaskSpec],
    catalog_tasks: list[TaskSpec],
) -> list[TaskSpec]:
    """Support tasks in the same repos as eval tasks, for memory warmup."""
    repos = {task.repo_path for task in eval_tasks}
    warmup: list[TaskSpec] = []
    seen: set[str] = set()
    eval_ids = {task.id for task in eval_tasks}
    for task in catalog_tasks:
        if task.id in eval_ids or task.id in seen:
            continue
        if "support" not in task.tags:
            continue
        if task.repo_path not in repos:
            continue
        warmup.append(task)
        seen.add(task.id)
    return warmup


def seed_pair_tasks_for_eval(
    eval_tasks: list[TaskSpec],
    catalog_tasks: list[TaskSpec],
) -> list[TaskSpec]:
    """Non-holdout seed tasks paired with repeated/holdout eval tasks."""
    by_id = {task.id: task for task in catalog_tasks}
    eval_ids = {task.id for task in eval_tasks}
    seeds: list[TaskSpec] = []
    seen: set[str] = set()
    for eval_task in eval_tasks:
        if "repeated" not in eval_task.tags and "memory_heavy" not in eval_task.tags:
            continue
        seed_id = seed_pair_task_id(eval_task.id)
        if not seed_id or seed_id in eval_ids or seed_id in seen:
            continue
        seed_task = by_id.get(seed_id)
        if seed_task is None:
            continue
        seeds.append(seed_task)
        seen.add(seed_id)
    return seeds


def memory_warmup_tasks_for_eval(
    eval_tasks: list[TaskSpec],
    catalog_tasks: list[TaskSpec],
) -> list[TaskSpec]:
    """Ordered warmup: support tasks first, then seed pairs (deduped)."""
    combined: list[TaskSpec] = []
    seen: set[str] = set()
    warmup = warmup_tasks_for_eval(eval_tasks, catalog_tasks)
    seeds = seed_pair_tasks_for_eval(eval_tasks, catalog_tasks)
    for task in [*warmup, *seeds]:
        if task.id in seen:
            continue
        combined.append(task)
        seen.add(task.id)
    return combined
