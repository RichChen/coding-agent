"""Tests for SkillCard v2 and MemoryHint v2 gating."""

from __future__ import annotations

from pathlib import Path

from reposkill_agent.agents.contracts import AgentContext
from reposkill_agent.core.contracts import TaskSpec
from reposkill_agent.core.task_graph import TaskNode
from reposkill_agent.eval.graph_runner import TaskGraphRunner
from reposkill_agent.llm.prompts import (
    build_system_prompt,
    build_user_prompt,
    format_memory_hints,
    format_skill_cards,
)
from reposkill_agent.memory import EpisodicStore, MemoryRetriever, ProceduralStore, RepoProfileStore
from reposkill_agent.memory.episodic import EpisodicMemory
from reposkill_agent.memory.procedural import ProceduralMemory
from reposkill_agent.memory.repo_profile import RepoProfileMemory
from reposkill_agent.skills import SkillRegistry, SkillRetriever, SkillValidator
from reposkill_agent.skills.models import SkillEvidenceContext, SkillSpec


def test_skill_evidence_gating_blocks_missing_evidence():
    skill = SkillSpec(
        id="needs_traceback",
        name="Traceback skill",
        version="0.2.0",
        purpose="needs traceback",
        pattern="fix from traceback",
        required_evidence=["traceback", "test_output"],
        edit_recipe=["read traceback"],
        verifier="tests_pass",
        applies_when=["traceback"],
    )
    task = TaskSpec(
        id="t",
        issue="fix traceback issue",
        repo_path="repo",
        test_command="pytest -q",
        expected_files=["app/x.py"],
        tags=["traceback"],
    )
    selection = SkillValidator().validate(
        task,
        [skill],
        SkillEvidenceContext(issue=task.issue, tags=task.tags, expected_files=task.expected_files),
    )
    assert selection.injected_count == 0
    assert any(r["reason"].startswith("missing_evidence") for r in selection.rejected)


def test_skill_evidence_gating_injects_when_evidence_present():
    task = TaskSpec(
        id="t",
        issue="Tests fail with ModuleNotFoundError import issue",
        repo_path="repo",
        test_command="pytest -q",
        expected_files=["app/calculator.py"],
        tags=["import", "bugfix"],
    )
    registry = SkillRegistry(Path("reposkill_agent/skills/library"))
    retrieved = SkillRetriever().retrieve(task, registry.load(), top_k=5)
    evidence = SkillEvidenceContext(
        issue=task.issue,
        tags=task.tags,
        expected_files=task.expected_files,
        test_output="ModuleNotFoundError: No module named app.calculator",
        repo_files=["app/calculator.py"],
    )
    selection = SkillValidator().validate(task, retrieved, evidence)
    assert selection.injected_count >= 1
    assert selection.injected_count <= 2


def test_negative_transfer_skill_is_gated():
    skill = SkillSpec(
        id="bad_skill",
        name="Bad",
        version="0.2.0",
        purpose="x",
        pattern="x",
        required_evidence=["import"],
        edit_recipe=["x"],
        applies_when=["import"],
        success_count=0,
        failure_count=3,
    )
    task = TaskSpec(
        id="t",
        issue="import error",
        repo_path="repo",
        test_command="pytest",
        tags=["import"],
    )
    selection = SkillValidator().validate(
        task,
        [skill],
        SkillEvidenceContext(issue=task.issue, tags=task.tags),
    )
    assert selection.injected_count == 0
    assert any(r["reason"] == "negative_transfer" for r in selection.rejected)


def test_compact_skill_and_memory_prompt_blocks():
    skill_block = format_skill_cards(
        [
            {
                "id": "s1",
                "pattern": "rename symbol",
                "required_evidence": ["rename"],
                "edit_recipe": ["step1", "step2"],
                "anti_patterns": ["import only"],
                "verifier": "tests_pass",
            }
        ]
    )
    assert "SkillCard:" in skill_block
    assert "procedure:" not in skill_block.lower()
    assert len(skill_block) < 400

    memory_block = format_memory_hints(
        [
            {
                "type": "procedural",
                "source_task_id": "task_a",
                "successful_pattern": "patch then test",
                "likely_files": ["app/x.py"],
                "repo_convention": "Result errors",
                "warning": "",
                "confidence": 0.8,
                "applies_when": ["api"],
            }
        ]
    )
    assert "MemoryHint:" in memory_block
    assert len(memory_block) < 400


def test_memory_hint_v2_caps_and_prioritizes(tmp_path: Path):
    memory_dir = tmp_path / "memory"
    episodic = EpisodicStore(memory_dir)
    procedural = ProceduralStore(memory_dir)
    profile_store = RepoProfileStore(memory_dir)
    profile_store.upsert(
        RepoProfileMemory(
            repo_fingerprint="abc123",
            test_commands=["pytest -q"],
            top_level_entries=["app"],
            common_files=["app/x.py"],
        )
    )
    procedural.append(
        ProceduralMemory(
            id="p1",
            source_task_ids=["prev_task"],
            pattern="api migration",
            reusable_workflow=["locate", "patch", "test"],
            applies_when=["api"],
            verifier="tests_pass",
            confidence=0.85,
        )
    )
    episodic.append(
        EpisodicMemory(
            task_id="failed_task",
            repo_fingerprint="abc123",
            issue_summary="failed api",
            plan_summary="graph plan",
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
        issue="api fix",
        repo_path="/repo",
        test_command="pytest -q",
        tags=["api"],
    )
    selection = retriever.select(task, "abc123")
    assert selection.candidate_count >= 2
    assert selection.injected_count <= 3
    assert selection.injected[0]["type"] in {"procedural", "repo_profile"}
    assert "source_task_id" in selection.injected[0]


def test_graph_runner_records_skill_memory_injection_stats(tmp_path: Path):
    task = TaskSpec(
        id="fix_import_error",
        issue="Fix module import error with ModuleNotFoundError",
        repo_path=str(Path("benchmarks/repos/fix_import_error").resolve()),
        test_command="python -m pytest tests/ -q",
        expected_files=["app/calculator.py"],
        tags=["import", "bugfix"],
    )
    runner = TaskGraphRunner(
        adapter="fake",
        trace_dir=tmp_path / "traces",
        work_dir=tmp_path / "work",
        use_skills=True,
        use_memory=True,
        memory_dir=tmp_path / "memory",
        developer_mode="llm",
        model_client=_mock_llm_client(),
    )
    result = runner.run(task)
    extra = result.metrics.extra
    assert int(extra.get("skill_candidate_count", 0)) >= 1
    assert int(extra.get("skill_injected_count", 0)) <= 2
    assert int(extra.get("memory_candidate_count", 0)) >= 0


def test_prompt_without_skill_memory_is_shorter():
    task = TaskSpec(
        id="rename_symbol_hard_01",
        issue="Rename normalize_text to clean_text",
        repo_path="repo",
        test_command="pytest -q",
        expected_files=["app/processor.py"],
        tags=["rename"],
    )
    node = TaskNode(id="patch", goal="patch", owner="developer", expected_artifact="x")
    base_ctx = AgentContext(task=task, node=node)
    rich_ctx = AgentContext(
        task=task,
        node=node,
        active_skills=[
            {
                "id": "rename_symbol_across_files",
                "pattern": "rename across files",
                "required_evidence": ["rename", "expected_files"],
                "edit_recipe": ["rename definition", "update callers"],
                "anti_patterns": ["import only"],
                "verifier": "tests_pass",
            }
        ],
        memory_hints=[
            {
                "type": "procedural",
                "source_task_id": "prev",
                "successful_pattern": "rename then test",
                "likely_files": ["app/processor.py"],
                "repo_convention": "keep tests green",
                "warning": "",
                "confidence": 0.8,
                "applies_when": ["rename"],
            }
        ],
    )
    base_user = build_user_prompt(
        context=base_ctx,
        file_contents={"app/processor.py": "x = 1\n"},
        allowed_paths=["app/processor.py"],
        repo_files=["app/processor.py"],
        test_output="",
    )
    rich_user = build_user_prompt(
        context=rich_ctx,
        file_contents={"app/processor.py": "x = 1\n"},
        allowed_paths=["app/processor.py"],
        repo_files=["app/processor.py"],
        test_output="FAILED test_rename",
    )
    system = build_system_prompt()
    base_len = len(system) + len(base_user)
    rich_len = len(system) + len(rich_user)
    assert rich_len - base_len < 1200


def _mock_llm_client():
    from reposkill_agent.llm.client import MockModelClient

    return MockModelClient(
        responses=[
            {
                "summary": "mock",
                "edits": [
                    {
                        "path": "app/calculator.py",
                        "content": (
                            '"""Simple calculator module."""\n\n\n'
                            "def add(a: int, b: int) -> int:\n"
                            "    return a + b\n\n\n"
                            "def subtract(a: int, b: int) -> int:\n"
                            "    return a - b\n"
                        ),
                        "reason": "mock",
                    }
                ],
                "confidence": 1.0,
                "needs_more_context": False,
            }
        ]
        * 5
    )
