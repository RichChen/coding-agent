#!/usr/bin/env python3
"""Run LLM mechanism ablations (L0-L5) against hard tasks."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from reposkill_agent.eval.llm_ablation import LLMAblationRunner
from reposkill_agent.eval.report import write_llm_ablation_markdown
from reposkill_agent.eval.task_spec import TaskCatalog, load_tasks
from reposkill_agent.llm.client import (
    LLMConfig,
    MissingLLMConfigError,
    MockModelClient,
    ModelClient,
)

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
    fixed_rename = (
        '"""Text processing helpers."""\n\n\n'
        "def clean_text(text: str) -> str:\n"
        '    """Normalize and lowercase text."""\n'
        '    return " ".join(text.strip().split()).lower()\n'
    )
    generic = {
        "summary": "mock patch",
        "edits": [
            {
                "path": "app/processor.py",
                "content": fixed_rename,
                "reason": "mock fix",
            }
        ],
        "confidence": 0.9,
        "needs_more_context": False,
    }
    return MockModelClient(responses=[generic] * 200)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run LLM mechanism ablation suite.")
    parser.add_argument(
        "--tasks",
        default="benchmarks/tasks/phase6_hard_12.yaml",
        help="Task YAML path relative to repo root.",
    )
    parser.add_argument("--repeats", type=int, default=1, help="Repeats per config.")
    parser.add_argument("--seed", type=int, default=42, help="Base random seed.")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of tasks.")
    parser.add_argument(
        "--seed-memory",
        action="store_true",
        help="Reuse one memory directory across repeats.",
    )
    parser.add_argument(
        "--mock-llm",
        action="store_true",
        help="Use MockModelClient (offline, no API key).",
    )
    parser.add_argument(
        "--configs",
        default=None,
        help="Comma-separated config names (e.g. L1_llm_planner,L2_llm_multi). Default: all L0-L5.",
    )
    parser.add_argument(
        "--max-llm-calls-per-task",
        type=int,
        default=3,
        help="LLM call budget per task (patch + repair + context retry). Default: 3.",
    )
    parser.add_argument(
        "--tags",
        default=None,
        help="Comma-separated tags; keep tasks that contain all listed tags.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "reports" / "llm",
        help="Directory for ablation reports. Tests should pass a temporary directory.",
    )
    args = parser.parse_args()

    if args.mock_llm:
        model_client = _mock_client()
    else:
        _bootstrap_env_from_dotenv()
        try:
            config = LLMConfig.from_env(require_key=True)
        except MissingLLMConfigError as exc:
            print(str(exc), file=sys.stderr)
            raise SystemExit(2) from exc
        model_client = ModelClient(config)

    tasks_path = (ROOT / args.tasks).resolve()
    full_catalog = load_tasks(tasks_path, benchmarks_root=ROOT / "benchmarks")
    catalog = full_catalog
    if args.limit is not None:
        catalog = TaskCatalog(tasks=full_catalog.tasks[: args.limit])
    runner = LLMAblationRunner(
        output_root=args.output,
        model_client=model_client,
        seed=args.seed,
        seed_memory=args.seed_memory,
        max_llm_calls_per_task=args.max_llm_calls_per_task,
    )
    config_names = None
    if args.configs:
        config_names = [name.strip() for name in args.configs.split(",") if name.strip()]
    include_tags = None
    if args.tags:
        include_tags = [tag.strip() for tag in args.tags.split(",") if tag.strip()]
    summary = runner.run(
        catalog=catalog,
        repeats=args.repeats,
        limit=args.limit,
        config_names=config_names,
        full_catalog=full_catalog,
        include_tags=include_tags,
    )
    summary["cli_args"] = {
        "tasks": args.tasks,
        "repeats": args.repeats,
        "seed": args.seed,
        "limit": args.limit,
        "seed_memory": args.seed_memory,
        "mock_llm": args.mock_llm,
        "configs": config_names,
        "max_llm_calls_per_task": args.max_llm_calls_per_task,
        "tags": include_tags,
    }
    json_path = runner.run_dir / "llm-ablation-summary.json"
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    md_path = runner.run_dir / "llm-ablation-summary.md"
    write_llm_ablation_markdown(summary, md_path)
    print("LLM ablation completed:")
    print(f"  JSON: {json_path}")
    print(f"  MD:   {md_path}")


if __name__ == "__main__":
    main()
