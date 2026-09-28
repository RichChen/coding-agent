#!/usr/bin/env python3
"""Run optional external baselines (vanilla DeepSeek, OpenHands, SWE-agent, Aider)."""

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from reposkill_agent.baselines import BASELINE_REGISTRY, BaselineRunRequest, get_baseline
from reposkill_agent.eval.task_spec import load_tasks
from reposkill_agent.llm.client import MockModelClient

ROOT = Path(__file__).resolve().parent.parent


def _bootstrap_env_from_dotenv() -> None:
    if os.environ.get("LLM_API_KEY"):
        return
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _mock_client() -> MockModelClient:
    generic = {
        "summary": "mock baseline patch",
        "edits": [
            {
                "path": "inventory/pricing.py",
                "content": "# mock patch\n",
                "reason": "mock",
            }
        ],
        "confidence": 0.5,
        "needs_more_context": False,
    }
    return MockModelClient(responses=[generic] * 200)


def _write_summary_md(run_dir: Path, summary: dict) -> Path:
    lines = [
        "# External Baseline Summary",
        "",
        f"Run ID: `{summary['run_id']}`",
        f"Generated at: {summary['generated_at']}",
        f"Baseline: `{summary['baseline']}`",
        f"Task count: {summary['task_count']}",
        "",
        "| Task | Status | Test Passed | Wall Time (ms) | Skip Reason |",
        "| --- | --- | ---: | ---: | --- |",
    ]
    for row in summary["rows"]:
        lines.append(
            f"| {row['task_id']} | {row['status']} | "
            f"{'yes' if row['test_passed'] else 'no'} | "
            f"{row['wall_time_ms']:.0f} | {row.get('skip_reason', '')} |"
        )
    lines.extend(
        [
            "",
            f"Success rate: **{summary['success_rate']:.2f}**",
            f"Skipped: {summary['skipped_count']}",
        ]
    )
    md_path = run_dir / "summary.md"
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return md_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Run external baseline comparisons.")
    parser.add_argument(
        "--tasks",
        default="benchmarks/tasks/phase7_medium_24.yaml",
        help="Task YAML path relative to repo root.",
    )
    parser.add_argument(
        "--baseline",
        required=True,
        choices=sorted(BASELINE_REGISTRY),
        help="Baseline runner name.",
    )
    parser.add_argument("--limit", type=int, default=None, help="Limit number of tasks.")
    parser.add_argument(
        "--mock-llm",
        action="store_true",
        help="Use MockModelClient for vanilla_deepseek (offline).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Directory for this run. Tests should pass a temporary directory.",
    )
    args = parser.parse_args()

    tasks_path = (ROOT / args.tasks).resolve()
    catalog = load_tasks(tasks_path, benchmarks_root=ROOT / "benchmarks")
    tasks = catalog.tasks[: args.limit] if args.limit else catalog.tasks

    run_id = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    run_dir = args.output or (ROOT / "reports" / "external_baselines" / run_id)
    run_dir.mkdir(parents=True, exist_ok=True)

    kwargs: dict = {}
    if args.baseline == "vanilla_deepseek":
        if args.mock_llm:
            kwargs["model_client"] = _mock_client()
        else:
            _bootstrap_env_from_dotenv()

    baseline = get_baseline(args.baseline, **kwargs)
    rows: list[dict] = []
    for task in tasks:
        request = BaselineRunRequest(
            task_id=task.id,
            issue=task.issue,
            repo_path=Path(task.repo_path),
            test_command=task.test_command,
            expected_files=task.expected_files,
            output_dir=run_dir,
        )
        result = baseline.run(request)
        rows.append(result.model_dump(mode="json"))

    executed = [r for r in rows if r["status"] not in ("skipped",)]
    passed = [r for r in executed if r["test_passed"]]
    skipped = [r for r in rows if r["status"] == "skipped"]
    success_rate = len(passed) / len(executed) if executed else 0.0

    summary = {
        "run_id": run_id,
        "generated_at": datetime.now(UTC).isoformat(),
        "baseline": args.baseline,
        "task_count": len(tasks),
        "success_rate": success_rate,
        "skipped_count": len(skipped),
        "rows": rows,
        "cli_args": {
            "tasks": args.tasks,
            "baseline": args.baseline,
            "limit": args.limit,
            "mock_llm": args.mock_llm,
        },
    }
    json_path = run_dir / "summary.json"
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    md_path = _write_summary_md(run_dir, summary)

    print("External baseline run completed:")
    print(f"  JSON: {json_path}")
    print(f"  MD:   {md_path}")
    print(f"  Success rate: {success_rate:.2f} ({len(passed)}/{len(executed)} executed)")


if __name__ == "__main__":
    main()
