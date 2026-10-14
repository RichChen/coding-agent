"""Offline process death at each summary boundary; an earlier append must not repeat."""
import asyncio
import os
import sys
from pathlib import Path

from src.llm.client import LLMResponse
from src.policy.model_budget import ModelBudgetLedger
from src.runtime.session import RunSession
from src.runtime.window import WindowPolicy, WindowPolicyHooks
from tests.fixtures.h4_worker import expected, make_loop as base_loop


class Provider:
    def __init__(self, workspace):
        self.workspace = workspace
    def fingerprint(self):
        return dict(provider='llm',model='process-fixture',adapter='test-only')
    async def generate(self, messages, *, max_tokens):
        with (self.workspace/'summary-calls.txt').open('a') as file:
            file.write('s')
        return LLMResponse(text='{"summary":"The earlier fixture append completed."}',
            usage=dict(prompt_tokens=100,completion_tokens=20,total_tokens=120,provenance='provider'))


def make_loop(workspace, resumed=False):
    loop = base_loop(workspace, resumed)
    loop.llm.max_tokens = 64
    for response in loop.llm._responses:
        response.usage = dict(prompt_tokens=8,completion_tokens=2,total_tokens=10,provenance='provider')
    loop.hooks = WindowPolicyHooks(WindowPolicy('summary',max_tokens=6000,keep_recent=0,
        summary_provider='llm'),summary_provider=Provider(workspace))
    loop.model_ledger = ModelBudgetLedger(max_model_calls=4,max_tokens=131072)
    loop.budget.model_ledger = loop.model_ledger
    loop.retry.model_ledger = loop.model_ledger
    return loop


async def main():
    directory, workspace, boundary = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    with RunSession.create(directory,task_id='r2-process',expected=expected(workspace)) as session:
        append = session.append
        def crash(kind,payload,**metadata):
            event = append(kind,payload,**metadata)
            if kind == boundary and (kind != 'context.prepared' or payload['step'] == 1):
                os._exit(74)
            return event
        session.append = crash
        await session.run(make_loop(workspace),'perform fixture write')


if __name__ == '__main__': asyncio.run(main())
