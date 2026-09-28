"""Tests for external baseline runners."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from reposkill_agent.baselines import BaselineRunRequest, get_baseline
from reposkill_agent.baselines.aider import AiderBaseline
from reposkill_agent.baselines.openhands_sdk import OpenHandsSdkBaseline
from reposkill_agent.baselines.swe_agent import SweAgentBaseline
from reposkill_agent.baselines.vanilla_deepseek import VanillaDeepSeekBaseline
from reposkill_agent.llm.client import MockModelClient

ROOT = Path(__file__).parent.parent


def test_get_baseline_unknown():
    with pytest.raises(ValueError, match="Unknown baseline"):
        get_baseline("nonexistent")


def test_optional_baselines_skip_when_unavailable(tmp_path: Path):
    request = BaselineRunRequest(
        task_id="dummy",
        issue="fix something",
        repo_path=tmp_path,
        test_command="python -m pytest -q",
        expected_files=[],
        output_dir=tmp_path / "out",
    )
    for baseline in (OpenHandsSdkBaseline(), SweAgentBaseline(), AiderBaseline()):
        available, reason = baseline.is_available()
        if not available:
            result = baseline.run(request)
            assert result.status == "skipped"
            assert result.skip_reason == reason


def test_vanilla_deepseek_mock_runs(tmp_path: Path):
    repo = ROOT / "benchmarks" / "repos" / "medium_inventory"
    if not repo.exists():
        pytest.skip("medium_inventory not yet created")
    catalog_path = ROOT / "benchmarks" / "tasks" / "phase7_medium_24.yaml"
    if not catalog_path.exists():
        pytest.skip("phase7_medium_24 not yet created")

    from reposkill_agent.eval.task_spec import load_tasks

    catalog = load_tasks(catalog_path, benchmarks_root=ROOT / "benchmarks")
    task = catalog.tasks[0]
    mock = MockModelClient(
        responses=[
            {
                "summary": "mock",
                "edits": [{"path": "inventory/pricing.py", "content": "# x\n", "reason": "m"}],
                "confidence": 0.5,
                "needs_more_context": False,
            }
        ]
        * 10
    )
    baseline = VanillaDeepSeekBaseline(model_client=mock)
    result = baseline.run(
        BaselineRunRequest(
            task_id=task.id,
            issue=task.issue,
            repo_path=Path(task.repo_path),
            test_command=task.test_command,
            expected_files=task.expected_files,
            output_dir=tmp_path,
        )
    )
    assert result.status in ("failure", "success")
    assert result.llm_calls >= 1


def test_run_external_baselines_cli_skip(tmp_path: Path):
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "run_external_baselines.py"),
            "--tasks",
            "benchmarks/tasks/phase6_hard_12.yaml",
            "--baseline",
            "swe_agent",
            "--limit",
            "1",
            "--output",
            str(tmp_path / "baselines"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "External baseline run completed" in proc.stdout
