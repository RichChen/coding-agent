#!/usr/bin/env python3
"""单任务 CLI：用于调试 AgentLoop 与 M1 验证。

English: single-task entry — loads YAML config, runs one natural-language task.

用法示例见 README / README.zh-CN.md。
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import tempfile
from pathlib import Path

# 允许从仓库根目录直接 `python scripts/run_single.py`（无需先 pip -e）
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.harness.factory import build_agent, load_config
from src.tracing.logger import TraceLogger
from src.tracing.models import TraceRun


async def main():
    parser = argparse.ArgumentParser(description="Run a single task through the agent loop.")
    parser.add_argument("task", nargs="?", default="Create a file hello.py that prints 'Hello, World!'")
    parser.add_argument("--config", default="configs/baseline.yaml", help="Config file path")
    parser.add_argument("--workspace", default=None, help="Workspace dir (default: temp dir)")
    args = parser.parse_args()

    config = load_config(args.config)

    if args.workspace:
        workspace = Path(args.workspace)
        workspace.mkdir(parents=True, exist_ok=True)
    else:
        workspace = Path(tempfile.mkdtemp(prefix="harness_"))

    print(f"Workspace: {workspace}")
    print(f"Model: {config['llm']['model']}")
    print(f"Config: {args.config}")
    print(f"Task: {args.task}")
    print("-" * 50)

    tracer = TraceLogger(output_dir=config.get("tracing", {}).get("output_dir", "traces"))
    agent = build_agent(config, workspace, tracer=tracer)

    if tracer:
        tracer.open_run("single_task")

    result = await agent.run(args.task, task_id="single_task")

    if tracer:
        trace = TraceRun(
            task_id="single_task",
            config_name="single",
            steps=result.steps,
            success=result.success,
            final_answer=result.final_answer,
            failure_reason=result.failure_reason.value if result.failure_reason else None,
            total_elapsed_ms=result.total_elapsed_ms,
            total_tokens=result.total_tokens,
            tool_failures=result.tool_failures,
            policy_blocks=result.policy_blocks,
            metadata={
                "context_events": result.context_events,
                "subagent_traces": result.subagent_traces,
            },
        )
        tracer.log_run(trace)
        tracer.close()

    print("-" * 50)
    print(f"Success: {result.success}")
    print(f"Steps: {len(result.steps)}")
    print(f"Elapsed: {result.total_elapsed_ms:.0f}ms")
    print(f"Tokens: {result.total_tokens}")
    print(f"Tool failures: {result.tool_failures}")
    print(f"Failure reason: {result.failure_reason.value}")
    print()
    if result.final_answer:
        print(f"Final Answer:\n{result.final_answer}")


if __name__ == "__main__":
    asyncio.run(main())
