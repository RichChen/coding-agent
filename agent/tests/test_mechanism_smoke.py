"""Batch 4.5 mechanism smoke: Phase7 skill/memory/category/context/repair."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from reposkill_agent.core.contracts import TaskSpec
from reposkill_agent.eval.graph_runner import TaskGraphRunner
from reposkill_agent.eval.llm_ablation import LLMAblationRunner
from reposkill_agent.eval.task_category import task_category
from reposkill_agent.eval.task_spec import load_tasks
from reposkill_agent.llm.client import MockModelClient
from reposkill_agent.skills import SkillRegistry, SkillRetriever, SkillValidator
from reposkill_agent.skills.models import SkillEvidenceContext

ROOT = Path(__file__).parent.parent
PHASE7_TASKS = ROOT / "benchmarks" / "tasks" / "phase7_medium_24.yaml"


def test_task_category_phase7_tags():
    assert task_category(["multi_file_api", "skill_heavy"]) == "skill_heavy"
    assert task_category(["multi_file_api", "memory_heavy"]) == "memory_heavy"
    assert task_category(["context_heavy", "config"]) == "context_heavy"
    assert task_category(["traceback_repair", "events"]) == "traceback_repair"
    assert task_category(["repo_convention", "inventory"]) == "repo_convention"
    assert task_category(["multi_file_api", "inventory"]) == "multi_file_api"
    assert task_category(["rename"]) == "rename"


def test_phase7_skill_evidence_allows_injection():
    if not PHASE7_TASKS.exists():
        pytest.skip("phase7_medium_24 not available")
    catalog = load_tasks(PHASE7_TASKS, benchmarks_root=ROOT / "benchmarks")
    task = next(t for t in catalog.tasks if t.id == "inv_api_tax_01")
    registry = SkillRegistry(ROOT / "reposkill_agent" / "skills" / "library")
    retrieved = SkillRetriever().retrieve(task, registry.load(), top_k=5)
    assert retrieved
    evidence = SkillEvidenceContext(
        issue=task.issue,
        tags=task.tags,
        expected_files=task.expected_files,
        repo_files=["inventory/pricing.py", "inventory/models.py"],
    )
    selection = SkillValidator().validate(task, retrieved, evidence)
    assert selection.injected_count > 0, selection.rejected


def test_traceback_repair_skill_without_test_output():
    registry = SkillRegistry(ROOT / "reposkill_agent" / "skills" / "library")
    skill = next(s for s in registry.load() if s.id == "inspect_pytest_traceback")
    task = TaskSpec(
        id="evt_traceback_01",
        issue="Pytest traceback indicates v1 payload keys are lost",
        repo_path="repo",
        test_command="pytest -q",
        expected_files=["events/serializer.py"],
        tags=["traceback_repair", "events"],
    )
    selection = SkillValidator().validate(
        task,
        [skill],
        SkillEvidenceContext(
            issue=task.issue,
            tags=task.tags,
            expected_files=task.expected_files,
        ),
    )
    assert selection.injected_count == 1


def test_phase7_medium_ablation_skill_memory_smoke(tmp_path: Path):
    if not PHASE7_TASKS.exists():
        pytest.skip("phase7_medium_24 not available")
    catalog = load_tasks(PHASE7_TASKS, benchmarks_root=ROOT / "benchmarks")
    runner = LLMAblationRunner(
        output_root=tmp_path / "reports",
        model_client=_phase7_mock_client(),
        seed=0,
        seed_memory=True,
    )
    summary = runner.run(
        catalog=catalog,
        limit=6,
        config_names=["L3_llm_skill", "L4_llm_memory", "L5_llm_full"],
    )
    l3 = summary["results"]["L3_llm_skill"]["aggregate"]
    l4 = summary["results"]["L4_llm_memory"]["aggregate"]
    l5 = summary["results"]["L5_llm_full"]["aggregate"]
    assert l3["skill_injected_total"] > 0, l3
    assert l4["memory_injected_total"] > 0, l4
    assert l5["skill_injected_total"] > 0, l5
    assert l5["memory_injected_total"] > 0, l5

    categories = {row["category"] for row in summary["results"]["L3_llm_skill"]["rows"]}
    assert categories - {"other"}, f"expected Phase7 categories, got {categories}"


def test_context_expansion_mechanism_smoke(tmp_path: Path):
    repo = ROOT / "benchmarks" / "repos" / "medium_event_pipeline"
    if not repo.exists():
        pytest.skip("medium_event_pipeline not available")
    task = TaskSpec(
        id="evt_context_pipeline_01",
        issue="End-to-end pipeline cannot process registered handlers from serialized input.",
        repo_path=str(repo),
        test_command="python -m pytest tests/test_context_pipeline.py -q",
        expected_files=["events/pipeline.py", "events/registry.py", "events/serializer.py"],
        tags=["context_heavy", "events", "support"],
    )
    mock = MockModelClient(
        responses=[
            {
                "summary": "need callers and tests",
                "edits": [],
                "confidence": 0.2,
                "needs_more_context": True,
                "requested_context": ["tests", "callers"],
            },
            {
                "summary": "mock patch",
                "edits": [
                    {
                        "path": "events/pipeline.py",
                        "content": "# placeholder patch\n",
                        "reason": "smoke",
                    }
                ],
                "confidence": 0.5,
                "needs_more_context": False,
            },
        ]
    )
    runner = TaskGraphRunner(
        adapter="fake",
        trace_dir=tmp_path / "traces",
        work_dir=tmp_path / "work",
        max_replans=1,
        developer_mode="llm",
        model_client=mock,
        max_llm_calls_per_task=2,
        allow_prefix_scripted_fixes=False,
    )
    result = runner.run(task)
    extra = result.metrics.extra
    assert int(extra.get("context_expansion_count", 0)) > 0
    assert int(extra.get("allowed_path_added_count", 0)) > 0
    assert int(extra.get("needs_more_context_recovered_count", 0)) > 0


def test_json_repair_mechanism_smoke(tmp_path: Path):
    repo = ROOT / "benchmarks" / "repos" / "medium_inventory"
    if not repo.exists():
        pytest.skip("medium_inventory not available")
    workspace = tmp_path / "ws"
    shutil.copytree(repo, workspace)
    task = TaskSpec(
        id="inv_api_tax_01",
        issue="Checkout totals ignore regional tax profiles.",
        repo_path=str(workspace),
        test_command="python -m pytest tests/test_api_tax.py -q",
        expected_files=["inventory/pricing.py"],
        tags=["multi_file_api", "skill_heavy"],
    )
    mock = MockModelClient(
        responses=[
            {
                "error_type": "llm_parse_error",
                "message": "bad json",
                "raw_content_preview": "{not valid",
            },
            {
                "summary": "repair",
                "edits": [
                    {
                        "path": "inventory/pricing.py",
                        "content": "# repaired\n",
                        "reason": "repair",
                    }
                ],
                "confidence": 0.8,
                "needs_more_context": False,
            },
        ]
    )
    runner = TaskGraphRunner(
        adapter="fake",
        trace_dir=tmp_path / "traces",
        work_dir=tmp_path / "work",
        developer_mode="llm",
        model_client=mock,
        max_llm_calls_per_task=2,
        allow_prefix_scripted_fixes=False,
    )
    result = runner.run(task)
    extra = result.metrics.extra
    assert int(extra.get("llm_parse_repair_attempt_total", 0)) > 0
    assert int(extra.get("llm_parse_repair_success_total", 0)) > 0


def _phase7_mock_client() -> MockModelClient:
    """Mock client that patches the first expected file for each task."""
    responses = []
    catalog = load_tasks(PHASE7_TASKS, benchmarks_root=ROOT / "benchmarks")
    for task in catalog.tasks[:12]:
        path = task.expected_files[0] if task.expected_files else "app/main.py"
        responses.append(
            {
                "summary": "phase7 mock",
                "edits": [{"path": path, "content": "# mock\n", "reason": "smoke"}],
                "confidence": 0.5,
                "needs_more_context": False,
            }
        )
    return MockModelClient(responses=responses * 20)
