"""Typer CLI entry point."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from reposkill_agent.eval.graph_runner import TaskGraphRunner
from reposkill_agent.eval.runner import BaselineRunner
from reposkill_agent.eval.task_spec import load_tasks
from reposkill_agent.llm.client import LLMConfig, MissingLLMConfigError, ModelClient

app = typer.Typer(
    name="reposkill-agent",
    help="RepoSkillAgent — PlanAct + MultiAgent + Skill + Memory repo task agent.",
    no_args_is_help=True,
)
console = Console()


@app.command("run-baseline")
def run_baseline(
    tasks_file: Annotated[
        Path,
        typer.Option("--tasks", help="YAML file listing benchmark tasks."),
    ] = Path("benchmarks/tasks/tiny_python_tasks.yaml"),
    trace_dir: Annotated[
        Path,
        typer.Option("--trace-dir", help="Directory for JSONL traces."),
    ] = Path("traces"),
    adapter: Annotated[
        str,
        typer.Option("--adapter", help="Adapter to use: fake or openhands."),
    ] = "fake",
    task_id: Annotated[
        str | None,
        typer.Option("--task-id", help="Run a single task by ID."),
    ] = None,
    use_agent: Annotated[
        bool,
        typer.Option("--use-agent", help="Use OpenHands agent (requires LLM_API_KEY)."),
    ] = False,
) -> None:
    """Run single-agent baseline on tiny repo tasks."""
    catalog = load_tasks(tasks_file)
    selected = catalog.tasks
    if task_id:
        task = catalog.get(task_id)
        if task is None:
            console.print(f"[red]Task not found:[/red] {task_id}")
            raise typer.Exit(1)
        selected = [task]

    if adapter == "openhands":
        adapter_kind = "openhands"
    else:
        adapter_kind = "fake"

    runner = BaselineRunner(adapter=adapter_kind, trace_dir=trace_dir)
    results = []
    for task in selected:
        console.print(f"[bold]Running[/bold] {task.id} …")
        result = runner.run(task, use_agent=use_agent)
        results.append(result)
        status = "[green]PASS[/green]" if result.metrics.success else "[red]FAIL[/red]"
        console.print(
            f"  {status}  steps={result.metrics.steps}  "
            f"time={result.metrics.wall_time_ms:.0f}ms  "
            f"trace={result.metrics.trace_path}"
        )

    table = Table(title="Baseline Results")
    table.add_column("Task")
    table.add_column("Success")
    table.add_column("Steps")
    table.add_column("Wall Time (ms)")
    table.add_column("Adapter")
    for r in results:
        table.add_row(
            r.task.id,
            "PASS" if r.metrics.success else "FAIL",
            str(r.metrics.steps),
            f"{r.metrics.wall_time_ms:.0f}",
            r.metrics.adapter,
        )
    console.print(table)

    summary_path = trace_dir / "baseline_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps([r.metrics.model_dump(mode="json") for r in results], indent=2),
        encoding="utf-8",
    )
    console.print(f"Summary written to {summary_path}")


@app.command("run-graph")
def run_graph(
    tasks_file: Annotated[
        Path,
        typer.Option("--tasks", help="YAML file listing benchmark tasks."),
    ] = Path("benchmarks/tasks/tiny_python_tasks.yaml"),
    trace_dir: Annotated[
        Path,
        typer.Option("--trace-dir", help="Directory for JSONL traces."),
    ] = Path("traces"),
    adapter: Annotated[
        str,
        typer.Option("--adapter", help="Adapter to use: fake or openhands."),
    ] = "fake",
    task_id: Annotated[
        str | None,
        typer.Option("--task-id", help="Run a single task by ID."),
    ] = None,
    max_replans: Annotated[
        int,
        typer.Option("--max-replans", help="Maximum number of replans."),
    ] = 1,
    use_skills: Annotated[
        bool,
        typer.Option("--use-skills", help="Enable skill retrieval and validation."),
    ] = False,
    use_memory: Annotated[
        bool,
        typer.Option("--use-memory", help="Enable memory retrieval and persistence."),
    ] = False,
    developer_mode: Annotated[
        str,
        typer.Option(
            "--developer-mode",
            help="Developer patch mode: deterministic or llm.",
        ),
    ] = "deterministic",
) -> None:
    """Run deterministic or LLM task-graph planner and executor."""
    catalog = load_tasks(tasks_file)
    selected = catalog.tasks
    if task_id:
        task = catalog.get(task_id)
        if task is None:
            console.print(f"[red]Task not found:[/red] {task_id}")
            raise typer.Exit(1)
        selected = [task]

    adapter_kind = "openhands" if adapter == "openhands" else "fake"
    dev_mode = "llm" if developer_mode == "llm" else "deterministic"
    model_client = None
    if dev_mode == "llm":
        try:
            model_client = ModelClient(LLMConfig.from_env(require_key=True))
        except MissingLLMConfigError as exc:
            console.print(f"[red]{exc}[/red]")
            raise typer.Exit(2) from exc
    runner = TaskGraphRunner(
        adapter=adapter_kind,
        trace_dir=trace_dir,
        max_replans=max_replans,
        use_skills=use_skills,
        use_memory=use_memory,
        developer_mode=dev_mode,
        model_client=model_client,
        allow_prefix_scripted_fixes=dev_mode == "deterministic",
    )
    results = []
    for task in selected:
        console.print(f"[bold]Graph run[/bold] {task.id} ...")
        result = runner.run(task)
        results.append(result)
        status = "[green]PASS[/green]" if result.metrics.success else "[red]FAIL[/red]"
        console.print(
            f"  {status}  steps={result.metrics.steps}  "
            f"replans={result.metrics.replan_count}  "
            f"time={result.metrics.wall_time_ms:.0f}ms"
        )

    table = Table(title="Task Graph Results")
    table.add_column("Task")
    table.add_column("Success")
    table.add_column("Steps")
    table.add_column("Replans")
    table.add_column("Skills")
    table.add_column("Memory")
    table.add_column("Wall Time (ms)")
    for result in results:
        table.add_row(
            result.task.id,
            "PASS" if result.metrics.success else "FAIL",
            str(result.metrics.steps),
            str(result.metrics.replan_count),
            str(result.metrics.extra.get("skill_validated_count", 0)),
            str(result.metrics.extra.get("memory_retrieval_count", 0)),
            f"{result.metrics.wall_time_ms:.0f}",
        )
    console.print(table)

    summary_path = trace_dir / "graph_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps([result.metrics.model_dump(mode="json") for result in results], indent=2),
        encoding="utf-8",
    )
    console.print(f"Summary written to {summary_path}")


@app.command("list-tasks")
def list_tasks(
    tasks_file: Annotated[Path, typer.Option("--tasks")] = Path(
        "benchmarks/tasks/tiny_python_tasks.yaml"
    ),
) -> None:
    """List available benchmark tasks."""
    catalog = load_tasks(tasks_file)
    table = Table(title="Benchmark Tasks")
    table.add_column("ID")
    table.add_column("Issue")
    table.add_column("Test Command")
    for task in catalog.tasks:
        table.add_row(task.id, task.issue[:60], task.test_command)
    console.print(table)


@app.command("upgrade-demo")
def upgrade_demo(
    output: Annotated[Path, typer.Option("--output", help="New offline demo directory.")],
) -> None:
    """Run public evidence and memory validity fixtures (no model calls)."""
    from reposkill_agent.eval.upgrade_demo import run_demo

    try:
        result = run_demo(output)
    except (ValueError, OSError) as exc:
        console.print(f"[red]Offline demo failed:[/red] {exc}")
        raise typer.Exit(2) from exc
    console.print(f"Offline comparisons: {len(result['drift_matrix'])}; model calls=0")
    console.print(f"Report: {output / 'report.md'}")


if __name__ == "__main__":
    app()
