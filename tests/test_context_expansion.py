"""Tests for context expansion and JSON repair retry."""

from __future__ import annotations

import shutil
from pathlib import Path

from reposkill_agent.adapters.fake_adapter import FakeAdapter
from reposkill_agent.agents import AgentContext, LLMDeveloperAgent, LocatorAgent
from reposkill_agent.core.context_expansion import expand_allowed_paths
from reposkill_agent.core.contracts import TaskSpec
from reposkill_agent.core.task_graph import TaskNode
from reposkill_agent.eval.graph_runner import TaskGraphRunner
from reposkill_agent.eval.scripted_fixes import SCRIPTED_FIXES
from reposkill_agent.llm.client import MockModelClient
from reposkill_agent.llm.prompts import build_json_repair_prompt

ROOT = Path(__file__).parent.parent


def test_expand_allowed_paths_adds_tests_and_package_modules(tmp_path: Path):
    repo = ROOT / "benchmarks" / "repos" / "medium_inventory"
    workspace = tmp_path / "ws"
    shutil.copytree(repo, workspace)
    adapter = FakeAdapter(workspace, allow_prefix_scripted_fixes=False)
    task = TaskSpec(
        id="inv_api_tax_01",
        issue="fix pricing tax",
        repo_path=str(workspace),
        test_command="python -m pytest tests/test_api_tax.py -q",
        expected_files=["inventory/pricing.py"],
        tags=["multi_file_api"],
    )
    added, reasons = expand_allowed_paths(
        adapter=adapter,
        task=task,
        requested_context=["tests", "package_modules"],
        current_paths={"inventory/pricing.py"},
    )
    assert added
    assert len(added) <= 3
    assert any("tests/" in path for path in added)
    assert reasons


def test_locator_expands_after_needs_more_context(tmp_path: Path):
    repo = ROOT / "benchmarks" / "repos" / "medium_inventory"
    workspace = tmp_path / "ws"
    shutil.copytree(repo, workspace)
    adapter = FakeAdapter(workspace, allow_prefix_scripted_fixes=False)
    task = TaskSpec(
        id="inv_api_tax_01",
        issue="fix pricing tax",
        repo_path=str(workspace),
        test_command="python -m pytest tests/test_api_tax.py -q",
        expected_files=["inventory/pricing.py"],
        tags=["context_heavy"],
    )
    node = TaskNode(id="locate", goal="locate", owner="locator", expected_artifact="matches")
    context = AgentContext(
        task=task,
        node=node,
        previous_actions=[
            {
                "node_id": "patch",
                "success": False,
                "llm_error_type": "needs_more_context",
                "requested_context": ["tests", "inventory/api.py"],
            }
        ],
    )
    result = LocatorAgent().run(context, adapter)
    assert result.payload["expanded_paths"]
    assert "inventory/pricing.py" in result.payload["matches"]


def test_llm_json_repair_recovers_parse_error(tmp_path: Path):
    task = TaskSpec(
        id="rename_symbol_hard_01",
        issue="Rename normalize_text to clean_text",
        repo_path=str(ROOT / "benchmarks" / "repos" / "rename_symbol"),
        test_command="python -m pytest tests/ -q",
        expected_files=["app/processor.py"],
        tags=["rename"],
    )
    workspace = tmp_path / "ws"
    shutil.copytree(task.repo_path, workspace)
    adapter = FakeAdapter(
        workspace,
        scripted_fixes=SCRIPTED_FIXES,
        allow_prefix_scripted_fixes=False,
    )
    fixed = (
        '"""Text processing helpers."""\n\n\n'
        "def clean_text(text: str) -> str:\n"
        '    return " ".join(text.strip().split()).lower()\n'
    )
    client = MockModelClient(
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
                        "path": "app/processor.py",
                        "content": fixed,
                        "reason": "repair",
                    }
                ],
                "confidence": 0.9,
                "needs_more_context": False,
            },
        ]
    )
    agent = LLMDeveloperAgent(client, max_calls_per_task=2)
    node = TaskNode(id="patch", goal="patch", owner="developer", expected_artifact="x")
    result = agent.run(AgentContext(task=task, node=node), adapter)
    assert result.success
    metrics = result.payload["llm_metrics"]
    assert metrics["llm_parse_repair_attempt_total"] == 1
    assert metrics["llm_parse_repair_success_total"] == 1


def test_build_json_repair_prompt_is_compact():
    prompt = build_json_repair_prompt(
        allowed_paths=["app/a.py"],
        raw_preview='{"broken": true}',
    )
    assert "allowed_paths" in prompt
    assert "raw_response_preview" in prompt
    assert len(prompt) < 500


def test_graph_runner_context_recovery_flow(tmp_path: Path):
    repo = ROOT / "benchmarks" / "repos" / "rename_symbol"
    task = TaskSpec(
        id="rename_symbol_hard_01",
        issue="Rename normalize_text to clean_text",
        repo_path=str(repo),
        test_command="python -m pytest tests/ -q",
        expected_files=["app/processor.py"],
        tags=["rename", "context_heavy"],
    )
    fixed = (
        '"""Text processing helpers."""\n\n\n'
        "def clean_text(text: str) -> str:\n"
        '    return " ".join(text.strip().split()).lower()\n'
    )
    mock = MockModelClient(
        responses=[
            {
                "summary": "need tests",
                "edits": [],
                "confidence": 0.2,
                "needs_more_context": True,
                "requested_context": ["tests/test_processor.py"],
            },
            {
                "summary": "rename",
                "edits": [
                    {
                        "path": "app/processor.py",
                        "content": fixed,
                        "reason": "fix",
                    }
                ],
                "confidence": 0.9,
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
    assert int(extra.get("context_expansion_count", 0)) >= 1
    assert int(extra.get("needs_more_context_recovered_count", 0)) == 1
    assert result.metrics.success
