#!/usr/bin/env python3
"""批量评测：对数据集 × 多份 YAML 配置跑 EvalRunner，并生成 Markdown/CSV 报告。

English: batch eval CLI — dataset × configs → reports/.

常用命令见 README / README.zh-CN.md。
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("run_eval")

from src.harness.factory import build_agent, load_config
from src.tracing.logger import TraceLogger


def agent_factory(config: dict):
    """Return a function that creates an AgentLoop from a config dict.

    Each agent gets its own TraceLogger so eval runs produce per-task traces.
    """
    def _build(config: dict):
        workspace = Path(tempfile.mkdtemp(prefix="eval_"))
        tracing_cfg = config.get("tracing", {})
        tracer = TraceLogger(output_dir=tracing_cfg.get("output_dir", "traces"))
        return build_agent(config, workspace, tracer=tracer)

    return _build(config)


def main():
    parser = argparse.ArgumentParser(description="Batch eval runner")
    parser.add_argument("--dataset", default="datasets/mini_tasks.json")
    parser.add_argument(
        "--configs", nargs="+", default=["baseline"],
        help="Config names to run (from configs/ dir, without .yaml)"
    )
    parser.add_argument(
        "--compare", action="store_true",
        help="Run both baseline and hardened, then compare"
    )
    parser.add_argument(
        "--runs", type=int, default=1,
        help="Number of repeated eval runs per config (default: 1)"
    )
    parser.add_argument(
        "--cost-per-1k",
        type=float,
        default=0.0,
        help="Estimated cost per 1k tokens for report (0 = show n/a)",
    )
    args = parser.parse_args()

    if args.compare:
        args.configs = ["baseline", "hardened"]

    # Load configs
    configs = {}
    for name in args.configs:
        path = f"configs/{name}.yaml"
        if not os.path.exists(path):
            logger.error(f"Config not found: {path}")
            sys.exit(1)
        configs[name] = load_config(path)
        logger.info(f"Loaded config: {name}")

    # Run eval
    from src.eval.runner import EvalRunner
    runner = EvalRunner(agent_factory=agent_factory, dataset_path=args.dataset)
    metrics_list = runner.run_all(
        configs, runs=args.runs, cost_per_1k_tokens=args.cost_per_1k
    )

    # Generate reports
    from src.eval.report import ReportGenerator, config_content_hash, get_git_commit_short
    reporter = ReportGenerator()
    run_metadata = {
        "git_commit": get_git_commit_short(),
        "runs": args.runs,
        "timestamp": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "configs": {
            name: {
                "model": cfg.get("llm", {}).get("model", "n/a"),
                "config_hash": config_content_hash(cfg),
            }
            for name, cfg in configs.items()
        },
        "cost_per_1k_tokens": args.cost_per_1k,
    }
    md_path, csv_path = reporter.generate(
        metrics_list, dataset_name=args.dataset, run_metadata=run_metadata
    )

    print(f"\nReport written to: {md_path}")
    print(f"CSV written to: {csv_path}")

    # Print summary to stdout
    for m in metrics_list:
        print(f"\n=== {m.config_name} ===")
        if hasattr(m, "run_count"):
            print(f"  Runs: {m.run_count}")
            print(f"  Success Rate mean/std: {m.success_rate.mean:.1f}% / {m.success_rate.std:.1f}")
            print(f"  Avg Steps mean/std: {m.avg_steps.mean:.1f} / {m.avg_steps.std:.1f}")
            print(f"  Avg Time mean/std: {m.avg_elapsed_ms.mean:.0f}ms / {m.avg_elapsed_ms.std:.0f}")
            print(f"  Tool Failure Rate mean/std: {m.tool_failure_rate.mean:.1f}% / {m.tool_failure_rate.std:.1f}")
            print(f"  Policy Blocks mean/std: {m.policy_block_count.mean:.1f} / {m.policy_block_count.std:.1f}")
        else:
            print(f"  Success Rate: {m.success_rate:.1f}% ({m.passed}/{m.total_tasks})")
            print(f"  Avg Steps: {m.avg_steps:.1f}")
            print(f"  Avg Time: {m.avg_elapsed_ms:.0f}ms")
            print(f"  Tool Failure Rate: {m.tool_failure_rate:.1f}%")
            print(f"  Policy Blocks: {m.policy_block_count}")
            print(f"  Failure breakdown: {m.failure_breakdown}")


if __name__ == "__main__":
    main()
