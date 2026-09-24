"""CLI smoke tests."""

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


def test_run_graph_single_task():
    result = runner.invoke(app, ["run-graph", "--task-id", "fix_import_error"])
    assert result.exit_code == 0
    assert "Task Graph Results" in result.stdout


def test_run_graph_with_skills_single_task():
    result = runner.invoke(app, ["run-graph", "--task-id", "fix_import_error", "--use-skills"])
    assert result.exit_code == 0
    assert "Task Graph Results" in result.stdout


def test_run_graph_with_memory_single_task():
    result = runner.invoke(app, ["run-graph", "--task-id", "fix_import_error", "--use-memory"])
    assert result.exit_code == 0
    assert "Task Graph Results" in result.stdout
