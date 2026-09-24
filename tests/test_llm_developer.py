"""Tests for LLMDeveloperAgent."""

from __future__ import annotations

from pathlib import Path

from reposkill_agent.adapters.fake_adapter import FakeAdapter
from reposkill_agent.agents import AgentContext, LLMDeveloperAgent
from reposkill_agent.core.contracts import TaskSpec
from reposkill_agent.core.task_graph import TaskNode
from reposkill_agent.eval.scripted_fixes import SCRIPTED_FIXES
from reposkill_agent.llm.client import MockModelClient

BENCHMARKS_ROOT = Path(__file__).parent.parent / "benchmarks"


def _rename_task() -> TaskSpec:
    return TaskSpec(
        id="rename_symbol_hard_01",
        issue="Rename normalize_text to clean_text",
        repo_path=str(BENCHMARKS_ROOT / "repos" / "rename_symbol"),
        test_command="python -m pytest tests/ -q",
        expected_files=["app/processor.py"],
        tags=["rename"],
    )


def _workspace(task: TaskSpec, tmp_path: Path) -> FakeAdapter:
    workspace = tmp_path / "ws"
    import shutil

    shutil.copytree(task.repo_path, workspace)
    return FakeAdapter(workspace, scripted_fixes=SCRIPTED_FIXES, allow_prefix_scripted_fixes=False)


def test_llm_developer_rejects_out_of_scope_path(tmp_path: Path):
    task = _rename_task()
    adapter = _workspace(task, tmp_path)
    client = MockModelClient(
        responses=[
            {
                "summary": "bad path",
                "edits": [
                    {
                        "path": "app/other.py",
                        "content": "x = 1\n",
                        "reason": "wrong",
                    }
                ],
                "confidence": 0.5,
                "needs_more_context": False,
            }
        ]
    )
    agent = LLMDeveloperAgent(client)
    node = TaskNode(
        id="patch",
        goal="patch",
        owner="developer",
        expected_artifact="PatchResult list",
    )
    result = agent.run(AgentContext(task=task, node=node), adapter)
    assert not result.success
    assert result.payload["llm_metrics"]["llm_patch_rejected_count"] == 1


def test_llm_developer_applies_full_file_edit(tmp_path: Path):
    task = _rename_task()
    adapter = _workspace(task, tmp_path)
    fixed = (
        '"""Text processing helpers."""\n\n\n'
        "def clean_text(text: str) -> str:\n"
        '    return " ".join(text.strip().split()).lower()\n'
    )
    client = MockModelClient(
        responses=[
            {
                "summary": "rename symbol",
                "edits": [
                    {
                        "path": "app/processor.py",
                        "content": fixed,
                        "reason": "tests expect clean_text",
                    }
                ],
                "confidence": 0.9,
                "needs_more_context": False,
            }
        ]
    )
    agent = LLMDeveloperAgent(client)
    node = TaskNode(
        id="patch",
        goal="patch",
        owner="developer",
        expected_artifact="PatchResult list",
    )
    result = agent.run(AgentContext(task=task, node=node), adapter)
    assert result.success
    assert result.payload["llm_metrics"]["llm_patch_applied_count"] == 1
    test = adapter.run_tests(task.test_command)
    assert test.passed


def test_llm_developer_parse_error(tmp_path: Path):
    task = _rename_task()
    adapter = _workspace(task, tmp_path)
    client = MockModelClient(responses=[])
    agent = LLMDeveloperAgent(client)
    node = TaskNode(
        id="patch",
        goal="patch",
        owner="developer",
        expected_artifact="PatchResult list",
    )
    result = agent.run(AgentContext(task=task, node=node), adapter)
    assert not result.success
    assert result.payload["llm_metrics"]["llm_error_type"] == "mock_empty"


def test_llm_developer_rejects_test_path_even_when_expanded(tmp_path: Path):
    task = _rename_task()
    adapter = _workspace(task, tmp_path)
    client = MockModelClient(
        responses=[
            {
                "summary": "cheat by editing tests",
                "edits": [
                    {
                        "path": "tests/test_processor.py",
                        "content": "def test_rename_symbol():\n    assert True\n",
                        "reason": "weaken assertion",
                    }
                ],
                "confidence": 0.9,
                "needs_more_context": False,
            }
        ]
    )
    agent = LLMDeveloperAgent(client)
    node = TaskNode(
        id="patch",
        goal="patch",
        owner="developer",
        expected_artifact="PatchResult list",
    )
    context = AgentContext(
        task=task,
        node=node,
        expanded_paths=["tests/test_processor.py"],
    )
    result = agent.run(context, adapter)
    assert not result.success
    metrics = result.payload["llm_metrics"]
    assert metrics["llm_patch_rejected_count"] == 1
    assert "tests/test_processor.py" in metrics["prompt_summary"]["readable_paths"]
    assert "tests/test_processor.py" not in metrics["prompt_summary"]["allowed_paths"]


def test_llm_developer_reads_expanded_tests_for_context(tmp_path: Path):
    task = _rename_task()
    adapter = _workspace(task, tmp_path)
    original_test = adapter.read_file("tests/test_processor.py")
    client = MockModelClient(
        responses=[
            {
                "summary": "need more context",
                "edits": [],
                "confidence": 0.1,
                "needs_more_context": True,
                "requested_context": ["tests/test_processor.py"],
            }
        ]
    )
    agent = LLMDeveloperAgent(client)
    node = TaskNode(
        id="patch",
        goal="patch",
        owner="developer",
        expected_artifact="PatchResult list",
    )
    context = AgentContext(
        task=task,
        node=node,
        expanded_paths=["tests/test_processor.py"],
    )
    agent.run(context, adapter)
    assert original_test
