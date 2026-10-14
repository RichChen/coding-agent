"""Tests for skill registry/retrieval/validation and graph integration."""

from pathlib import Path

from reposkill_agent.core.contracts import TaskSpec
from reposkill_agent.eval.graph_runner import TaskGraphRunner
from reposkill_agent.eval.injection_policy import resolve_augmentation_policy
from reposkill_agent.skills import SkillRegistry, SkillRetriever, SkillValidator
from reposkill_agent.skills.models import SkillSpec


def test_skill_registry_loads_markdown_files():
    registry = SkillRegistry(Path("reposkill_agent/skills/library"))
    loaded = registry.load()
    assert len(loaded) >= 5
    assert any(skill.id == "fix_import_module_error" for skill in loaded)


def test_skill_retrieval_and_validation_for_import_task():
    task = TaskSpec(
        id="t1",
        issue="Tests fail with ModuleNotFoundError import issue",
        repo_path="repo",
        test_command="pytest -q",
        expected_files=["app/calculator.py"],
        tags=["import", "bugfix"],
    )
    registry = SkillRegistry(Path("reposkill_agent/skills/library"))
    skills = registry.load()
    retrieved = SkillRetriever().retrieve(task, skills, top_k=3)
    selection = SkillValidator().validate(task, retrieved)
    assert selection.retrieved_count >= 1
    assert selection.validated_count >= 1


def test_graph_runner_with_skills_records_metrics(tmp_path: Path):
    repo_root = Path("benchmarks/repos/fix_import_error").resolve()
    task = TaskSpec(
        id="fix_import_error",
        issue="Fix module import error",
        repo_path=str(repo_root),
        test_command="python -m pytest tests/ -q",
        expected_files=["app/calculator.py"],
        tags=["import", "bugfix"],
    )
    runner = TaskGraphRunner(
        adapter="fake",
        trace_dir=tmp_path / "traces",
        work_dir=tmp_path / "work",
        use_skills=True,
    )
    result = runner.run(task)
    assert result.metrics.success
    assert int(result.metrics.extra["skill_retrieved_count"]) >= 1
    assert int(result.metrics.extra["skill_validated_count"]) >= 1


def test_inventory_task_rejects_event_domain_skill():
    task = TaskSpec(
        id="inv_api_tax_01",
        issue="Checkout totals ignore regional tax profiles",
        repo_path="repos/medium_inventory",
        test_command="pytest -q",
        expected_files=["inventory/pricing.py", "inventory/models.py"],
        tags=["multi_file_api", "skill_heavy", "inventory"],
    )
    event_skill = SkillSpec(
        id="event_serializer_compat",
        name="Event serializer",
        version="0.1",
        purpose="serialization",
        domains=["events"],
        required_evidence=["multi_file_api", "expected_files"],
        applies_when=["multi_file_api", "events"],
    )
    inventory_skill = SkillSpec(
        id="inventory_tax_api",
        name="Inventory tax",
        version="0.1",
        purpose="tax",
        domains=["inventory"],
        required_evidence=["multi_file_api", "inventory", "expected_files"],
        applies_when=["tax", "inventory"],
    )
    registry = SkillRegistry(Path("reposkill_agent/skills/library"))
    skills = registry.load()
    retrieved = SkillRetriever().retrieve(task, skills, top_k=5)
    assert not any(s.id == "event_serializer_compat" for s in retrieved)
    selection = SkillValidator().validate(task, [event_skill, inventory_skill])
    assert selection.injected_count == 1
    assert selection.selected[0].id == "inventory_tax_api"
    rejected = {item["skill_id"]: item["reason"] for item in selection.rejected}
    assert rejected["event_serializer_compat"].startswith("domain_mismatch")


def test_skill_primary_policy_blocks_memory():
    policy = resolve_augmentation_policy(
        TaskSpec(
            id="t",
            issue="x",
            repo_path="r",
            test_command="pytest",
            tags=["skill_heavy"],
        ),
        full_stack=True,
    )
    assert policy.name == "skill_primary"
    assert policy.allow_memory is False
    assert policy.max_memory_hints == 0


def test_context_primary_unaffected_by_skill_primary():
    skill_policy = resolve_augmentation_policy(
        TaskSpec(id="t", issue="x", repo_path="r", test_command="pytest", tags=["skill_heavy"]),
        full_stack=True,
    )
    context_policy = resolve_augmentation_policy(
        TaskSpec(id="t", issue="x", repo_path="r", test_command="pytest", tags=["context_heavy"]),
        full_stack=True,
    )
    assert skill_policy.name == "skill_primary"
    assert context_policy.name == "context_primary"
    assert context_policy.allow_skills is False
    assert context_policy.allow_memory is False
