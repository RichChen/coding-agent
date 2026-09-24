"""Domain matching for skill retrieval and validation."""

from __future__ import annotations

from reposkill_agent.core.contracts import TaskSpec
from reposkill_agent.skills.models import SkillSpec

TASK_DOMAIN_TAGS = frozenset({"inventory", "config", "events", "auth"})
MECHANISM_TAGS = frozenset(
    {
        "skill_heavy",
        "memory_heavy",
        "context_heavy",
        "multi_file_api",
        "traceback_repair",
        "repo_convention",
        "repeated",
        "support",
    }
)
GENERIC_EVIDENCE_TOKENS = frozenset(
    {
        "api",
        "multi_file_api",
        "expected_files",
        "expected files",
        "tags",
        "repo_files",
        "repo files",
        "skill_heavy",
        "context_heavy",
        "memory_heavy",
    }
)


def task_domains(task: TaskSpec) -> set[str]:
    return {tag for tag in task.tags if tag in TASK_DOMAIN_TAGS}


def skill_domains(skill: SkillSpec) -> set[str]:
    if skill.domains:
        return set(skill.domains)
    inferred = {token for token in skill.applies_when if token in TASK_DOMAIN_TAGS}
    return inferred


def domain_compatible(skill: SkillSpec, task: TaskSpec) -> bool:
    """True when skill domain scope matches the task repo domain."""
    task_d = task_domains(task)
    skill_d = skill_domains(skill)
    if not skill_d:
        return True
    if not task_d:
        return True
    return bool(task_d & skill_d)


def only_generic_evidence(skill: SkillSpec) -> bool:
    reqs = {
        token.lower().replace(" ", "_")
        for token in skill.evidence_requirements()
    }
    generic = {token.replace(" ", "_") for token in GENERIC_EVIDENCE_TOKENS}
    return bool(reqs) and reqs <= generic
