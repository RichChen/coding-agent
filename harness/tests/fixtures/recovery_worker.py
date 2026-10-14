"""Real process-death fixture. All effects are confined to the caller's temp workspace."""
import asyncio
import os
import sys
from pathlib import Path

from src.llm.client import LLMResponse, ToolCall
from src.policy.budget import Budget
from src.policy.sandbox import Sandbox
from src.runtime.loop import AgentLoop
from src.runtime.session import RunSession, compatibility
from src.tools.base import Tool, ToolResult
from src.tools.files import WriteFileTool
from src.tools.registry import ToolRegistry
from tests.fixtures.mock_llm import MockLLMClient


class AppendTool(Tool):
    name = "append_fixture"
    parameters = {"type": "object", "properties": {}, "additionalProperties": False}

    async def execute(self, params, ctx):
        with open(ctx.workspace_root / "calls.txt", "a") as stream:
            stream.write("x")
        with open(ctx.workspace_root / "value.txt", "a") as stream:
            stream.write("x")
            stream.flush()
            os.fsync(stream.fileno())
        return ToolResult(ctx.call_id, self.name, True, "raw observation " + "r" * 20000)


def expected(workspace):
    return compatibility(workspace=workspace, code_id="fixture-v1", config={"api_key": "FAKE_SECRET"}, backend="fixture")


def make_loop(workspace, mode, resumed=False):
    registry = ToolRegistry()
    if mode == "replace":
        tool = WriteFileTool()
        registry.register(tool)
        original = tool.execute

        async def counted(params, ctx):
            with open(ctx.workspace_root / "calls.txt", "a") as stream:
                stream.write("x")
            return await original(params, ctx)

        tool.execute = counted
        call = ToolCall("provider-id", "write_file", {"path": "value.txt", "content": "new"})
    else:
        registry.register(AppendTool())
        call = ToolCall("provider-id", "append_fixture", {})
    responses = [LLMResponse(text="finished")]
    if not resumed:
        responses.insert(0, LLMResponse(tool_calls=[call]))
    return AgentLoop(MockLLMClient(responses), registry, Sandbox(workspace), Budget(max_steps=5))


async def main():
    directory, workspace, window, mode = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], sys.argv[4]
    with RunSession.create(directory, task_id="crash", expected=expected(workspace)) as session:
        append = session.append
        def crash_append(kind, payload, **metadata):
            if window == "before_intent" and kind == "tool.intent":
                os._exit(71)
            event = append(kind, payload, **metadata)
            if kind == "state.saved" and session.state.loop.get("response") is None:
                session.checkpoint()  # Deliberately stale by the time tool.result commits.
            if window == "after_intent" and kind == "tool.intent":
                os._exit(71)
            if window == "after_result" and kind == "tool.result":
                os._exit(71)
            return event
        session.append = crash_append
        record = session.record_result
        def crash_result(*args, **kwargs):
            if window == "after_effect":
                os._exit(71)
            return record(*args, **kwargs)
        session.record_result = crash_result
        await session.run(make_loop(workspace, mode), "perform fixture write")


if __name__ == "__main__":
    asyncio.run(main())
