"""R2-lite offline behavior and real adapter contract (MockTransport, no network)."""
import asyncio
import copy
import json
import subprocess
import sys
from pathlib import Path
from dataclasses import replace

import httpx
import pytest

from src.harness.factory import build_agent
from src.llm.client import LLMClient, LLMResponse, ToolCall
from src.policy.model_budget import ModelBudgetLedger, BudgetLedgerError
from src.runtime.deadline import DeadlineClock, UserCancelled, DeadlineExceeded
from src.runtime.session import RunSession
from src.runtime.summary import LLMSummaryProvider, SUMMARY_SYSTEM, summary_totals
from src.runtime.window import WindowPolicy, WindowPolicyHooks, ContextWindowError, ContextOverflowError, view_hash
from tests.test_context_window import history, ctx
from tests.fixtures.h4_worker import expected, make_loop


class FakeSummaryProvider:
    def __init__(self, response=None, *, stall=False):
        self.response = response or LLMResponse(text='{"summary":"Read public files; task remains unresolved."}',
            usage=dict(prompt_tokens=100, completion_tokens=20, total_tokens=120, provenance='provider'))
        self.calls = []
        self.stall = stall
        self.started = asyncio.Event()
        self.stopped = False

    def fingerprint(self):
        return dict(provider='llm', model='offline-fake', adapter='test-only')

    async def generate(self, messages, *, max_tokens):
        self.calls.append(copy.deepcopy(messages))
        self.started.set()
        try:
            if self.stall: await asyncio.Event().wait()
            return self.response
        finally:
            self.stopped = True


def ledger(**kwargs):
    return ModelBudgetLedger(**dict(dict(max_model_calls=10, max_tokens=300000, max_cost_usd=1,
        price_table={'prompt_per_1k':.001,'completion_per_1k':.002}), **kwargs))


def setup(provider=None, **kwargs):
    hook = WindowPolicyHooks(WindowPolicy('summary', max_tokens=6000, keep_recent=1,
        summary_provider='llm', **kwargs), summary_provider=provider)
    context = ctx(model_ledger=ledger(), source_event_seq=7)
    return hook, context


@pytest.mark.asyncio
async def test_success_cache_raw_binding_untrusted_and_separate_budget():
    provider = FakeSummaryProvider()
    hook, context = setup(provider)
    raw = history()
    original = copy.deepcopy(raw)
    view = await hook.before_llm(raw, context)
    record = hook.state['summaries'][0]
    assert record['status'] == 'llm_success' and record['provider'] == 'llm'
    assert record['source_hash'] == view_hash(raw[record['source_start']:record['source_end']])
    assert record['raw_message_hash'] == view_hash(raw)
    assert record['source_event_range'] == [7,7]
    assert record['source_step_range'] == [0,3]
    assert record['after_bytes'] < record['before_bytes']
    assert record['usage_provenance'] == 'provider' and record['total_tokens'] == 120
    assert record['cost_usd'] == pytest.approx(.00014)
    assert record['cost_provenance'] == 'price_table_estimate'
    assert context.extra['model_ledger'].calls_started == 1
    assert context.extra['model_ledger'].tokens_committed == 120
    assert view[2]['role'] == 'user' and 'Untrusted summary' in view[2]['content']
    assert view[:2] == raw[:2] and view[-1] == raw[-1] and raw == original
    assert provider.calls[0][0]['content'] == SUMMARY_SYSTEM
    payload = json.loads(provider.calls[0][1]['content'])
    assert payload == dict(constraints=raw[:2], raw_events=raw[2:-2])
    restored, _ = setup(provider)
    restored.restore(hook.state)
    assert await restored.before_llm(raw, context) == view
    assert len(provider.calls) == 1 and restored.state['summary_calls'] == 1
    raw[3]['content'] += 'changed'
    with pytest.raises(ContextWindowError, match='source changed'):
        await restored.before_llm(raw, context)
    assert len(provider.calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize('strategy', ['none','masking','summary','mask-then-summary'])
async def test_no_unnecessary_calls(strategy):
    p = FakeSummaryProvider()
    hook, c = setup(p)
    hook.policy = replace(hook.policy, strategy=strategy)
    await hook.before_llm(history(count=0), c)
    assert not p.calls
    if strategy in ('none','masking'):
        try: await hook.before_llm(history(), c)
        except ContextOverflowError: pass
        assert not p.calls


@pytest.mark.asyncio
@pytest.mark.parametrize('response', [
    LLMResponse(text='not JSON'), LLMResponse(text='{"summary":"partial'),
    LLMResponse(text='{"summary":"ok"}', finish_reason='length'),
    LLMResponse(text='{"summary":"ok"}', finish_reason=None),
    LLMResponse(text='{"summary":"ok"}', tool_calls=[ToolCall('x','write_file',{})]),
    LLMResponse(text='{"summary":"ok","action":"write_file"}'),
    LLMResponse(text='{"summary":"first","summary":"second"}'),
    LLMResponse(text='{"summary":null}'), LLMResponse(text='{"summary":""}'),
])
async def test_invalid_output_fallback_retains_raw_and_unknown_reserve(response):
    p = FakeSummaryProvider(response)
    hook, c = setup(p)
    raw = history()
    before = copy.deepcopy(raw)
    view = await hook.before_llm(raw, c)
    r = hook.state['summary_attempts'][0]
    assert r['status'] == 'invalid_output' and r['text'] is None
    assert not hook.state['summaries'] and 'Untrusted summary' not in repr(view)
    assert c.extra['context_stats']['fallback'] == 'summary_failure_masking'
    assert r['usage_provenance'] == 'unknown' and r['cost_usd'] is None
    assert r['tokens_committed'] > 0 and r['cost_committed_usd'] > 0
    assert raw == before
    # Same source failure cannot spend another call, including after restore.
    hook.policy = replace(hook.policy, max_summary_calls=3)
    again, _ = setup(p, max_summary_calls=3)
    again.restore(hook.state)
    await again.before_llm(raw, c)
    assert len(p.calls) == 1


@pytest.mark.asyncio
async def test_unknown_usage_success_is_not_free():
    p = FakeSummaryProvider(LLMResponse(text='{"summary":"Public observation."}'))
    hook, c = setup(p)
    await hook.before_llm(history(), c)
    r = hook.state['summaries'][0]
    assert r['status'] == 'llm_success' and r['usage_provenance'] == 'unknown'
    assert r['total_tokens'] is None and r['cost_usd'] is None
    assert c.extra['model_ledger'].tokens_committed == r['tokens_committed'] > 0
    assert summary_totals(hook.state)['unknown_usage_calls'] == 1


@pytest.mark.asyncio
async def test_invalid_json_still_billed_and_summary_only_masks_when_it_fits():
    response = LLMResponse(text='invalid', usage=dict(prompt_tokens=100,completion_tokens=20,total_tokens=120))
    hook, c = setup(FakeSummaryProvider(response))
    with pytest.raises(ContextOverflowError):
        await hook.before_llm(history(reasoning=4000), c)
    assert hook.state['summary_attempts'][0]['status'] == 'invalid_output'
    assert c.extra['model_ledger'].tokens_committed == 120
    assert c.extra['model_ledger'].cost_committed == pytest.approx(.00014)


@pytest.mark.asyncio
async def test_time_and_token_subbudgets_survive_restore():
    p = FakeSummaryProvider()
    hook, c = setup(p, max_summary_calls=3)
    await hook.before_llm(history(), c)
    for key, value in [('elapsed_seconds', 60), ('tokens_committed', 131000)]:
        state = copy.deepcopy(hook.state)
        state['summary_attempts'][0][key] = value
        restored, next_context = setup(p, max_summary_calls=3)
        restored.restore(state)
        with pytest.raises(ContextWindowError,match='summary_budget_exhausted'):
            await restored.before_llm(history(count=8), next_context)
        assert len(p.calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize('failure', ['masking','reject'])
async def test_unavailable_never_labels_fixture_as_real(failure):
    hook, c = setup(summary_failure=failure)
    if failure == 'reject':
        with pytest.raises(ContextWindowError, match='provider_unavailable'):
            await hook.before_llm(history(), c)
    else:
        view = await hook.before_llm(history(), c)
        assert 'summary' not in repr(view)
    assert hook.state['summary_calls'] == 0 and not hook.state['summaries']
    assert c.extra['model_ledger'].calls_started == 0


@pytest.mark.asyncio
async def test_timeout_cancel_and_host_deadline():
    p = FakeSummaryProvider(stall=True)
    hook, c = setup(p, summary_timeout_seconds=.02)
    await hook.before_llm(history(), c)
    assert p.stopped and hook.state['summary_attempts'][0]['status'] == 'timeout'
    for cancelled in (True,False):
        p = FakeSummaryProvider(stall=True)
        hook, c = setup(p)
        cancel = asyncio.Event()
        c.extra['cancel_event'] = cancel
        clock = DeadlineClock()
        clock.set_run(10 if cancelled else .04)
        c.extra['deadline'] = clock
        task = asyncio.create_task(hook.before_llm(history(), c))
        await asyncio.wait_for(p.started.wait(), 1)
        if cancelled: cancel.set()
        with pytest.raises(UserCancelled if cancelled else DeadlineExceeded):
            await task
        assert p.stopped and not hook.state['summaries']
        assert c.extra['model_ledger'].calls_started == 1
        assert not c.extra['model_ledger'].outstanding


@pytest.mark.asyncio
async def test_budget_input_limits_and_reported_overrun():
    for kwargs, status in [({'summary_max_tokens':10},'summary_budget_exhausted'),
                           ({'summary_input_max_bytes':100},'input_limit')]:
        p = FakeSummaryProvider()
        hook, c = setup(p, summary_failure='reject', **kwargs)
        with pytest.raises(ContextWindowError): await hook.before_llm(history(), c)
        assert hook.state['summary_attempts'][0]['status'] == status
        assert not p.calls
    p = FakeSummaryProvider()
    hook, c = setup(p)
    c.extra['model_ledger'] = ledger(max_tokens=100)
    with pytest.raises(BudgetLedgerError): await hook.before_llm(history(), c)
    assert not p.calls and hook.state['summary_attempts'][0]['status'] == 'run_budget_exhausted'
    p = FakeSummaryProvider(LLMResponse(text='{"summary":"done"}', usage={
        'prompt_tokens':400000,'completion_tokens':1,'total_tokens':400001}))
    hook, c = setup(p)
    with pytest.raises(ContextWindowError, match='usage exceeded'): await hook.before_llm(history(), c)
    assert not hook.state['summaries'] and c.extra['model_ledger'].tokens_committed == 400001
    restored, _ = setup(p)
    restored.restore(hook.state)
    with pytest.raises(ContextWindowError, match='terminal failure'):
        await restored.before_llm(history(), c)
    assert len(p.calls) == 1


@pytest.mark.asyncio
async def test_new_source_never_contains_previous_summary_and_max_calls_survives_restore():
    p = FakeSummaryProvider()
    hook, c = setup(p, max_summary_calls=2)
    await hook.before_llm(history(), c)
    larger = history(count=8)
    await hook.before_llm(larger, c)
    assert len(p.calls) == 2
    assert 'Read public files; task remains unresolved.' not in repr(p.calls[1])
    restored, c = setup(p, max_summary_calls=2)
    restored.restore(hook.state)
    with pytest.raises(ContextOverflowError): await restored.before_llm(history(count=12), c)
    assert len(p.calls) == 2


@pytest.mark.asyncio
async def test_llm_adapter_payload_usage_and_borrowed_http_lifecycle():
    requests = []
    def transport(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={'choices':[{'message':{'content':'{"summary":"public evidence"}'},
            'finish_reason':'stop'}], 'usage':{'prompt_tokens':100,'completion_tokens':20,'total_tokens':120}})
    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as http:
        client = LLMClient('https://fixture.invalid/v1','fake-test-key','chosen-model',
            max_tokens=999, temperature=.8, http_client=http, thinking='disabled')
        hook, c = setup(LLMSummaryProvider(client))
        await hook.before_llm(history(), c)
        payload = requests[0]
        assert payload['model'] == 'chosen-model' and payload['max_tokens'] == 512
        assert payload['temperature'] == 0 and payload['thinking'] == {'type':'disabled'}
        assert 'tools' not in payload and 'tool_choice' not in payload
        assert payload['messages'][0]['content'] == SUMMARY_SYSTEM
        assert hook.state['summaries'][0]['total_tokens'] == 120
        assert client.max_tokens == 999 and client.temperature == .8
        assert 'fake-test-key' not in repr(hook.state)
        await client.aclose()
        assert not http.is_closed


@pytest.mark.asyncio
async def test_llm_adapter_missing_finish_is_incomplete_not_success():
    def transport(request):
        return httpx.Response(200,json={'choices':[{'message':{'content':'{"summary":"plausible"}'}}]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as http:
        client = LLMClient('https://fixture.invalid/v1','fake','model',http_client=http)
        hook, c = setup(LLMSummaryProvider(client))
        await hook.before_llm(history(), c)
        assert hook.state['summary_attempts'][0]['status'] == 'invalid_output'
        assert not hook.state['summaries']


@pytest.mark.asyncio
async def test_paid_demo_requires_explicit_inputs_before_loading_credentials_or_creating_files(tmp_path):
    from scripts.demo_true_summary import parser, run_demo
    destination = tmp_path/'must-not-exist'
    args = parser().parse_args(['--provider','llm','--output-dir',str(destination)])
    with pytest.raises(ValueError,match='requires --allow-paid'):
        await run_demo(args)
    assert not destination.exists()


@pytest.mark.asyncio
async def test_paid_demo_full_adapter_is_offline_with_one_summary_and_replay(tmp_path, monkeypatch):
    from scripts import demo_true_summary as demo
    from src.config.schema import HarnessConfig
    requests = []
    def transport(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200,json={'choices':[{'message':{'content':'{"summary":"Observed public files; latest failure unresolved."}'},
            'finish_reason':'stop'}], 'usage':{'prompt_tokens':100,'completion_tokens':20,'total_tokens':120}})
    config = HarnessConfig.model_validate(dict(llm=dict(base_url='https://fixture.invalid/v1',
        api_key='fake-test-only',model='unused',thinking='disabled'))).model_dump()
    monkeypatch.setattr(demo,'load_config',lambda path:copy.deepcopy(config))
    original_build = demo.build_agent
    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as http:
        def build(*args,**kwargs):
            loop = original_build(*args,**kwargs)
            loop.llm._http = http
            loop.llm._owns_http_client = False
            return loop
        monkeypatch.setattr(demo,'build_agent',build)
        destination = tmp_path/'demo'
        args = demo.parser().parse_args(['--provider','llm','--allow-paid','--config','unused.yaml',
            '--model','offline-transport-model','--max-cost-usd','1','--prompt-per-1k','.001',
            '--completion-per-1k','.002','--price-version','fake-test-price','--output-dir',str(destination)])
        assert await demo.run_demo(args) == 0
        assert len(requests) == 1 and not http.is_closed
    manifest = json.loads((destination/'manifest.json').read_text())
    result = json.loads((destination/'run-result.json').read_text())
    assert manifest['provider'] == 'llm' and manifest['main_model_calls'] == 0
    assert result['summary']['model_calls'] == result['model_budget']['calls_started'] == 1
    assert result['total_tokens'] == 120
    replay = RunSession.replay(destination/'session')
    assert replay.terminal['summary'] == result['summary']
    record = result['summary']['records'][0]
    assert record['raw_message_hash'] == view_hash(replay.messages)
    assert record['source_hash'] == view_hash(replay.messages[record['source_start']:record['source_end']])
    assert record['source_event_range'] == [3,3]
    assert 'fake-test-only' not in repr(result) + repr(manifest) + repr(replay)


@pytest.mark.asyncio
@pytest.mark.parametrize('boundary', ['summary.started','summary.settled','context.prepared'])
async def test_persistent_crash_boundaries_replay_resume_no_duplicate_summary(tmp_path, boundary):
    workspace = tmp_path/'workspace'; workspace.mkdir()
    directory = tmp_path/'session'
    raw = history()
    p = FakeSummaryProvider()
    hook, c = setup(p)
    loop = make_loop(workspace, resumed=True)
    loop.hooks = hook
    loop.model_ledger = c.extra['model_ledger']
    class Crash(BaseException): pass
    with RunSession.create(directory, task_id='r2', expected=expected(workspace)) as session:
        loop.session = session
        session.save_loop(dict(messages=raw, step_number=0))
        append = session.append
        def crash(kind, payload, **metadata):
            result = append(kind, payload, **metadata)
            if kind == boundary: raise Crash()
            return result
        session.append = crash
        with pytest.raises(Crash): await loop._model_view(raw, [], 'Original task', 'r2', 0, [])
    snapshot = RunSession.replay(directory)
    assert snapshot.messages == raw and snapshot.plugin_state['h4']['summary_calls'] == 1
    calls_before = len(p.calls)
    assert snapshot.budget['calls_started'] == 1
    with RunSession.resume(directory, expected=expected(workspace)) as session:
        restored, c = setup(p)
        restored.restore(session.state.plugin_state['h4'])
        loop.hooks = restored
        loop.session = session
        if boundary == 'summary.started':
            with pytest.raises(ContextWindowError, match='outcome_unknown'):
                await loop._model_view(raw, [], 'Original task', 'r2', 0, [])
        else:
            view = await loop._model_view(raw, [], 'Original task', 'r2', 0, [])
            assert 'Untrusted summary' in repr(view)
        session.store.export_jsonl(tmp_path/'events.jsonl')
    assert len(p.calls) == calls_before
    assert 'summary.started' in (tmp_path/'events.jsonl').read_text()


def test_factory_explicit_real_adapter_same_client(tmp_path):
    config = dict(llm=dict(base_url='https://fixture.invalid',api_key='',model='m'),
        runtime=dict(max_steps=3,total_timeout_seconds=10,step_timeout_seconds=5,
                     context=dict(strategy='summary',summary_provider='llm')))
    loop = build_agent(config, tmp_path)
    assert loop.hooks.summary_provider.client is loop.llm
    assert loop.hooks.fingerprint()['policy']['summary_provider'] == 'llm'


@pytest.mark.asyncio
@pytest.mark.parametrize('boundary', ['summary.started','summary.settled','context.prepared'])
async def test_actual_process_death_full_loop_budget_and_append_recovery(tmp_path, boundary):
    from tests.fixtures.summary_worker import make_loop as summary_loop
    workspace = tmp_path/'workspace'; workspace.mkdir()
    directory = tmp_path/'session'
    process = subprocess.run([sys.executable,'-m','tests.fixtures.summary_worker',str(directory),
        str(workspace),boundary],cwd=Path(__file__).resolve().parents[1],capture_output=True,text=True,timeout=25)
    assert process.returncode == 74, process.stderr
    state = RunSession.replay(directory)
    assert state.plugin_state['h4']['summary_calls'] == 1
    assert state.budget['calls_started'] == 2  # first main + summary intent
    with RunSession.resume(directory,expected=expected(workspace)) as session:
        loop = summary_loop(workspace,resumed=True)
        result = await session.run(loop,'perform fixture write')
        if boundary == 'summary.started':
            assert not result.success and loop.llm._call_count == 0
            assert result.summary['records'][0]['status'] == 'started'
            assert result.summary['unknown_usage_calls'] == 1
            assert not (workspace/'summary-calls.txt').exists()
        else:
            assert result.success and loop.llm._call_count == 1
            assert result.total_tokens == 140
            assert result.summary['model_calls'] == 1
            assert result.model_budget['calls_started'] == 3
            assert len(result.llm_attempts) == 2
            assert (workspace/'summary-calls.txt').read_text() == 's'
        assert (workspace/'calls.txt').read_text() == 'x'
    assert RunSession.replay(directory).terminal['summary'] == result.summary


@pytest.mark.asyncio
async def test_loop_cancellation_during_summary_stops_before_next_main_call(tmp_path):
    from tests.fixtures.summary_worker import make_loop as summary_loop
    loop = summary_loop(tmp_path)
    provider = FakeSummaryProvider(stall=True)
    loop.hooks.summary_provider = provider
    loop.cancel_event = asyncio.Event()
    task = asyncio.create_task(loop.run('perform fixture write'))
    await asyncio.wait_for(provider.started.wait(),2)
    loop.cancel_event.set()
    result = await task
    assert result.termination_kind == 'user_cancelled'
    assert loop.llm._call_count == 1 and provider.stopped
    assert result.summary['records'][0]['status'] == 'cancelled'
    assert result.model_budget['calls_started'] == 2
    assert (tmp_path/'calls.txt').read_text() == 'x'
