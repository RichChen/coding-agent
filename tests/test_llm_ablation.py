"""Tests for LLM ablation runner and script."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from reposkill_agent.eval.llm_ablation import LLMAblationRunner
from reposkill_agent.eval.task_spec import TaskCatalog, load_tasks
from reposkill_agent.llm.client import MissingLLMConfigError, MockModelClient

ROOT = Path(__file__).parent.parent
TASKS = ROOT / "benchmarks" / "tasks" / "phase6_hard_12.yaml"


def test_llm_ablation_mock_runs(tmp_path: Path):
    catalog = load_tasks(TASKS, benchmarks_root=ROOT / "benchmarks")
    rename = catalog.get("rename_symbol_hard_01")
    assert rename is not None
    catalog = TaskCatalog(tasks=[rename])
    fixed = (
        '"""Text processing helpers."""\n\n\n'
        "def clean_text(text: str) -> str:\n"
        '    return " ".join(text.strip().split()).lower()\n'
    )
    mock = MockModelClient(
        responses=[
            {
                "summary": "mock",
                "edits": [
                    {
                        "path": "app/processor.py",
                        "content": fixed,
                        "reason": "mock",
                    }
                ],
                "confidence": 1.0,
                "needs_more_context": False,
            }
        ]
        * 50
    )
    runner = LLMAblationRunner(
        output_root=tmp_path / "llm",
        model_client=mock,
        seed=42,
    )
    summary = runner.run(catalog, repeats=1, limit=1)
    assert summary["task_count"] == 1
    assert "L0_llm_single" in summary["results"]
    assert (runner.run_dir / "llm-ablation-summary.json").exists()


def test_run_llm_ablation_mock_cli(tmp_path: Path):
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "run_llm_ablation.py"),
            "--tasks",
            "benchmarks/tasks/phase6_hard_12.yaml",
            "--limit",
            "1",
            "--mock-llm",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "LLM ablation completed" in proc.stdout


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    with pytest.raises(MissingLLMConfigError):
        from reposkill_agent.llm.client import LLMConfig

        LLMConfig.from_env(require_key=True)
