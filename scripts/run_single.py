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
import json
from pathlib import Path

# 允许从仓库根目录直接 `python scripts/run_single.py`（无需先 pip -e）
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.harness.factory import build_agent, load_config
from src.tracing.logger import TraceLogger
from src.tracing.models import TraceRun
from src.runtime.session import RunSession, compatibility, source_fingerprint


async def main():
    parser = argparse.ArgumentParser(description="Run a single task through the agent loop.")
    parser.add_argument("task", nargs="?", default="Create a file hello.py that prints 'Hello, World!'")
    parser.add_argument("--config", default="configs/baseline.yaml", help="Config file path")
    parser.add_argument("--workspace", default=None, help="Workspace dir (default: temp dir)")
    sessions = parser.add_mutually_exclusive_group()
    sessions.add_argument("--session-dir", help="Create persistent session outside the agent workspace")
    sessions.add_argument("--resume", help="Resume a session with the same task/config/workspace; unknown writes never replay")
    sessions.add_argument("--replay", help="Read session state only; no config, model, or tool execution")
    args = parser.parse_args()

    if args.replay:
        state = RunSession.replay(Path(args.replay))
        print(json.dumps({"last_seq": state.last_seq, "terminated": state.terminal is not None,
                          "operations": {k: (v["result"] or {}).get("status", "pending") for k, v in state.operations.items()},
                          "model_budget": state.budget}, ensure_ascii=False, indent=2))
        return
    if args.resume and not args.workspace:
        parser.error("--resume requires the original --workspace and task")

    config = load_config(args.config)
    if config['policy']['command']['execution_profile'] == 'docker_linux' and not (args.session_dir or args.resume):
        parser.error('docker_linux requires --session-dir to persist the candidate; use scripts/run_h3.py for independent grading')

    if args.workspace:
        workspace = Path(args.workspace)
        if args.resume:
            workspace = workspace.resolve(strict=True)
        else:
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

    try:
        if args.session_dir or args.resume:
            expected = compatibility(workspace=workspace,
                code_id=source_fingerprint(Path(__file__).resolve().parent.parent), config=config,
                backend={"execution_profile": config.get("policy", {}).get("command", {}).get("execution_profile", "legacy_host"),
                         "platform": sys.platform})
            session = (RunSession.resume(Path(args.resume), expected=expected) if args.resume else
                       RunSession.create(Path(args.session_dir), task_id="single_task", expected=expected,
                                         timeout_seconds=agent.budget.total_timeout_seconds))
            with session:
                result = await session.run(agent, args.task)
        else:
            result = await agent.run(args.task, task_id="single_task")
    finally:
        aclose = getattr(agent.llm, "aclose", None)
        if callable(aclose):
            await aclose()

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
                "summary": result.summary,
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
    if result.summary:
        print(f"Summary provider: {result.summary['provider']}; model calls: {result.summary['model_calls']}; "
              f"unknown usage calls: {result.summary['unknown_usage_calls']}")
    print(f"Tool failures: {result.tool_failures}")
    print(f"Failure reason: {result.failure_reason.value}")
    print()
    if result.final_answer:
        print(f"Final Answer:\n{result.final_answer}")


if __name__ == "__main__":
    asyncio.run(main())
