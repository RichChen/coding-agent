#!/usr/bin/env python3
"""Run Phase 6 ablations (A0-A5) and generate reports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from reposkill_agent.eval.ablation import AblationRunner
from reposkill_agent.eval.report import write_ablation_markdown
from reposkill_agent.eval.task_spec import load_tasks

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Phase 6 ablation suite.")
    parser.add_argument(
        "--tasks",
        default="benchmarks/tasks/phase6_tiny_24.yaml",
        help="Task YAML path relative to repo root.",
    )
    parser.add_argument("--repeats", type=int, default=3, help="Repeats per config.")
    parser.add_argument("--seed", type=int, default=42, help="Base random seed.")
    parser.add_argument(
        "--seed-memory",
        action="store_true",
        help="Reuse one memory directory across repeats as seeded memory.",
    )
    args = parser.parse_args()

    tasks_path = (ROOT / args.tasks).resolve()
    catalog = load_tasks(tasks_path, benchmarks_root=ROOT / "benchmarks")
    runner = AblationRunner(
        output_root=ROOT / "reports" / "phase6",
        adapter="fake",
        seed_memory=args.seed_memory,
        seed=args.seed,
    )
    summary = runner.run(catalog=catalog, repeats=args.repeats)
    summary["cli_args"] = {
        "tasks": args.tasks,
        "repeats": args.repeats,
        "seed": args.seed,
        "seed_memory": args.seed_memory,
        "adapter": "fake",
    }
    summary_path = runner.run_dir / "ablation-summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    md_path = runner.run_dir / "ablation-summary.md"
    write_ablation_markdown(summary, md_path)
    print("Phase 6 ablation completed:")
    print(f"  JSON: {summary_path}")
    print(f"  MD:   {md_path}")


if __name__ == "__main__":
    main()
