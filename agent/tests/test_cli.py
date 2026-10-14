"""CLI smoke tests."""

from pathlib import Path

from typer.testing import CliRunner

from reposkill_agent.cli import app

runner = CliRunner()


def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "reposkill-agent" in result.stdout.lower() or "baseline" in result.stdout.lower()


def test_list_tasks():
    result = runner.invoke(app, ["list-tasks"])
    assert result.exit_code == 0
    assert "fix_import_error" in result.stdout


def _graph(tmp_path: Path, *extra: str):
    return runner.invoke(
        app,
        ["run-graph", "--task-id", "fix_import_error", "--trace-dir", str(tmp_path), *extra],
    )


def test_run_graph_single_task(tmp_path: Path):
    result = _graph(tmp_path)
    assert result.exit_code == 0
    assert "Task Graph Results" in result.stdout


def test_run_graph_with_skills_single_task(tmp_path: Path):
    result = _graph(tmp_path, "--use-skills")
    assert result.exit_code == 0
    assert "Task Graph Results" in result.stdout


def test_run_graph_with_memory_single_task(tmp_path: Path):
    result = _graph(tmp_path, "--use-memory")
    assert result.exit_code == 0
    assert "Task Graph Results" in result.stdout
