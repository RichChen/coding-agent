"""Tests for Phase 5 memory MVP."""

from pathlib import Path

from reposkill_agent.core.contracts import TaskSpec
from reposkill_agent.eval.graph_runner import TaskGraphRunner
from reposkill_agent.memory import EpisodicStore, ProceduralStore, RepoProfileStore


def test_graph_runner_with_memory_persists_records(tmp_path: Path):
    task = TaskSpec(
        id="fix_import_error",
        issue="Fix module import error",
        repo_path=str(Path("benchmarks/repos/fix_import_error").resolve()),
        test_command="python -m pytest tests/ -q",
        expected_files=["app/calculator.py"],
        tags=["import", "bugfix"],
    )
    memory_dir = tmp_path / "memory"
    runner = TaskGraphRunner(
        adapter="fake",
        trace_dir=tmp_path / "traces",
        work_dir=tmp_path / "work",
        use_memory=True,
        memory_dir=memory_dir,
    )
    result = runner.run(task)
    assert result.metrics.success
    assert int(result.metrics.extra["memory_retrieval_count"]) >= 0

    episodic = EpisodicStore(memory_dir).list_recent(limit=10)
    assert len(episodic) >= 1
    assert episodic[-1].task_id == "fix_import_error"

    procedural = ProceduralStore(memory_dir).list_all()
    assert len(procedural) >= 1

    profile = RepoProfileStore(memory_dir)
    record = profile.get(episodic[-1].repo_fingerprint)
    assert record is not None
    assert "python -m pytest tests/ -q" in record.test_commands


def test_skill_negative_transfer_counts_when_test_fails(tmp_path: Path):
    failing_task = TaskSpec(
        id="fix_import_error",
        issue="Fix module import error",
        repo_path=str(Path("benchmarks/repos/fix_import_error").resolve()),
        test_command="python -m pytest tests/not_exist -q",
        expected_files=["app/calculator.py"],
        tags=["import", "bugfix"],
    )
    runner = TaskGraphRunner(
        adapter="fake",
        trace_dir=tmp_path / "traces",
        work_dir=tmp_path / "work",
        use_skills=True,
    )
    result = runner.run(failing_task)
    assert not result.metrics.success
    assert int(result.metrics.extra["skill_validated_count"]) >= 1
    assert int(result.metrics.extra["skill_negative_transfer_count"]) == 1
