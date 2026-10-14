import asyncio
import copy
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from src.harness.factory import build_agent
from src.llm.client import LLMResponse
from src.policy.plugin import NoOpPolicyPlugin
from src.runtime.loop import FailureReason
from src.runtime.session import RunSession
from src.runtime.window import WindowPolicy, WindowPolicyHooks, view_hash
from src.tracing.store import StoreError
from tests.fixtures.h4_worker import expected, make_loop


@pytest.mark.asyncio
async def test_preflight_overflow_has_zero_model_calls_and_no_tool_effect(tmp_path):
    loop=make_loop(tmp_path)
    loop.hooks=WindowPolicyHooks(WindowPolicy('none',max_tokens=1000))
    result=await loop.run('a'*5000)
    assert result.failure_reason==FailureReason.CONTEXT_OVERFLOW
    assert loop.llm._call_count==0 and not (tmp_path/'calls.txt').exists()
    assert result.context_events[-1]['overflow']


@pytest.mark.asyncio
async def test_distinct_runs_do_not_reuse_plugin_state(tmp_path):
    loop=make_loop(tmp_path,resumed=True)
    loop.llm._responses.append(LLMResponse(text='second run'))
    assert (await loop.run('first')).success
    assert loop.hooks.state['plugin_state']=={'calls':1}
    assert (await loop.run('second')).success
    assert loop.hooks.state['plugin_state']=={'calls':1}


@pytest.mark.asyncio
async def test_raw_history_and_artifacts_survive_masking_and_replay(tmp_path):
    workspace=tmp_path/'workspace'; workspace.mkdir()
    directory=tmp_path/'session'
    loop=make_loop(workspace)
    with RunSession.create(directory,task_id='h4',expected=expected(workspace)) as session:
        result=await session.run(loop,'perform fixture write')
        assert result.success
        state=session.state
        assert 'r'*10000 in state.loop['messages'][-1]['content']
        assert 'r'*10000 not in repr(loop.llm.calls[-1]['messages'])
        assert state.plugin_state['h4']['plugin_state']=={'calls':2}
        op=next(iter(state.operations.values()))
        assert len(op['result']['output'])>20000
        # The durable raw boundary precedes the prepared view in the journal.
        events=session.store.read_events()
        prepared=[e for e in events if e['event_type']=='context.prepared'][-1]
        assert events[prepared['seq']-2]['event_type']=='state.saved'
    restored=RunSession.replay(directory)
    assert restored.context['stats']['view_hash']==view_hash(restored.context['view'])
    assert restored.terminal['success']
    if os.environ.get('HARNESS_H4_EVIDENCE'):
        from src.eval.grader import save_json
        save_json(Path(os.environ['HARNESS_H4_EVIDENCE'])/'raw-view.json',dict(
            raw_hash=restored.context['raw_message_hash'],view_hash=restored.context['stats']['view_hash'],
            stats=restored.context['stats'],operations=len(restored.operations),replay_model_calls=0))


@pytest.mark.asyncio
async def test_real_crash_restores_prepared_view_without_duplicate_plugin_or_effect(tmp_path):
    workspace=tmp_path/'workspace'; workspace.mkdir()
    directory=tmp_path/'session'
    process=subprocess.run([sys.executable,'-m','tests.fixtures.h4_worker',str(directory),str(workspace)],
        cwd=Path(__file__).resolve().parents[1],capture_output=True,text=True,timeout=25)
    assert process.returncode==73,process.stderr
    before=RunSession.replay(directory)
    assert before.terminal is None and before.plugin_state['h4']['plugin_state']=={'calls':2}
    prepared_hash=before.context['stats']['view_hash']
    with RunSession.resume(directory,expected=expected(workspace)) as session:
        loop=make_loop(workspace,resumed=True)
        result=await session.run(loop,'perform fixture write')
        assert result.success
        assert loop.llm._call_count==1
        assert view_hash(loop.llm.calls[0]['messages'])==prepared_hash
        assert session.state.plugin_state['h4']['plugin_state']=={'calls':2}
        assert session.state.budget['calls_started']==2
    assert (workspace/'calls.txt').read_text()=='x'


@pytest.mark.asyncio
async def test_resume_rejects_changed_window_policy(tmp_path):
    workspace=tmp_path/'workspace';workspace.mkdir();directory=tmp_path/'session'
    process=subprocess.run([sys.executable,'-m','tests.fixtures.h4_worker',str(directory),str(workspace)],
        cwd=Path(__file__).resolve().parents[1],capture_output=True,timeout=25)
    assert process.returncode==73
    with RunSession.resume(directory,expected=expected(workspace)) as session:
        loop=make_loop(workspace,resumed=True)
        loop.hooks.policy=WindowPolicy('none',max_tokens=16000)
        with pytest.raises(StoreError,match='runtime configuration changed'):
            await session.run(loop,'perform fixture write')
        assert loop.llm._call_count==0


@pytest.mark.asyncio
async def test_plugin_await_obeys_deadline_and_cancel(tmp_path):
    class Stall(NoOpPolicyPlugin):
        def __init__(self): self.started=asyncio.Event();self.stopped=False
        async def decide(self,data):
            self.started.set()
            try: await asyncio.Event().wait()
            finally: self.stopped=True
    for cancel in (False,True):
        loop=make_loop(tmp_path,resumed=True)
        plugin=Stall();loop.hooks=WindowPolicyHooks(WindowPolicy(),plugin)
        loop.budget.step_timeout_seconds=.05 if not cancel else 10
        loop.cancel_event=asyncio.Event()
        task=asyncio.create_task(loop.run('fixture'))
        await asyncio.wait_for(plugin.started.wait(),2)
        if cancel:loop.cancel_event.set()
        result=await asyncio.wait_for(task,3)
        assert result.termination_kind==('user_cancelled' if cancel else 'step_deadline')
        assert loop.llm._call_count==0 and plugin.stopped
