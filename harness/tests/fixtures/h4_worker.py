"""A real process exit after context publication, before the next model call."""
import asyncio
import os
import sys
from pathlib import Path

from src.llm.client import LLMResponse, ToolCall
from src.policy.budget import Budget
from src.policy.plugin import FixturePolicyPlugin
from src.policy.sandbox import Sandbox
from src.runtime.loop import AgentLoop
from src.runtime.window import WindowPolicy, WindowPolicyHooks
from src.runtime.session import RunSession, compatibility
from src.tools.registry import ToolRegistry
from tests.fixtures.recovery_worker import AppendTool
from tests.fixtures.mock_llm import MockLLMClient


def expected(workspace):
    return compatibility(workspace=workspace,code_id='h4-fixture-v1',config={},backend='trusted-fixture')


def make_loop(workspace,resumed=False):
    tools=ToolRegistry(); tools.register(AppendTool())
    responses=[LLMResponse(text='done')]
    if not resumed: responses.insert(0,LLMResponse(tool_calls=[ToolCall('append','append_fixture',{})]))
    return AgentLoop(MockLLMClient(responses),tools,Sandbox(workspace),Budget(max_steps=5),
                     hooks=WindowPolicyHooks(WindowPolicy('masking',max_tokens=16000,keep_recent=0),FixturePolicyPlugin()))


async def main():
    directory,workspace=map(Path,sys.argv[1:3])
    with RunSession.create(directory,task_id='h4-crash',expected=expected(workspace)) as session:
        append=session.append
        def crash(kind,payload,**metadata):
            event=append(kind,payload,**metadata)
            if kind=='context.prepared' and payload['step']==1:
                os._exit(73)
            return event
        session.append=crash
        await session.run(make_loop(workspace),'perform fixture write')


if __name__=='__main__': asyncio.run(main())
