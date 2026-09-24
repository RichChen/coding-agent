"""Tests for skill/memory domain registry consistency and auth gating."""

from __future__ import annotations

from reposkill_agent.core.contracts import TaskSpec
from reposkill_agent.memory.matching import DOMAIN_TAGS
from reposkill_agent.skills.domain import TASK_DOMAIN_TAGS, domain_compatible, task_domains
from reposkill_agent.skills.models import SkillSpec
from reposkill_agent.skills.validator import SkillValidator


def test_skill_and_memory_domain_tags_match():
    assert TASK_DOMAIN_TAGS == DOMAIN_TAGS
    assert "auth" in TASK_DOMAIN_TAGS


def test_auth_task_domains():
    task = TaskSpec(
        id="auth_role_check_01",
        issue="Role API returns booleans",
        repo_path="repos/medium_auth_rules",
        test_command="pytest -q",
        expected_files=["auth_rules/api.py"],
        tags=["repo_convention", "skill_heavy", "auth"],
    )
    assert task_domains(task) == {"auth"}


def test_auth_rejects_inventory_only_skill():
    task = TaskSpec(
        id="auth_role_check_01",
        issue="Role API returns booleans",
        repo_path="repos/medium_auth_rules",
        test_command="pytest -q",
        expected_files=["auth_rules/api.py"],
        tags=["repo_convention", "skill_heavy", "auth"],
    )
    inventory_skill = SkillSpec(
        id="inventory_tax_api",
        name="Inventory tax",
        version="0.1",
        purpose="tax",
        domains=["inventory"],
        required_evidence=["multi_file_api", "expected_files"],
        applies_when=["tax", "inventory"],
    )
    assert not domain_compatible(inventory_skill, task)
    selection = SkillValidator().validate(task, [inventory_skill])
    assert selection.injected_count == 0
    assert selection.rejected[0]["reason"].startswith("domain_mismatch")


def test_auth_accepts_undomained_repo_convention_skill():
    task = TaskSpec(
        id="auth_role_check_01",
        issue="Role API returns booleans",
        repo_path="repos/medium_auth_rules",
        test_command="pytest -q",
        expected_files=["auth_rules/api.py"],
        tags=["repo_convention", "skill_heavy", "auth"],
    )
    generic_skill = SkillSpec(
        id="repo_result_convention",
        name="Repo Result convention",
        version="0.2",
        purpose="Result returns",
        required_evidence=["repo_convention", "expected_files"],
        applies_when=["repo_convention", "result"],
    )
    assert domain_compatible(generic_skill, task)
    selection = SkillValidator().validate(task, [generic_skill])
    assert selection.injected_count == 1
