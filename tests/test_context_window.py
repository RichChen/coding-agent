import asyncio
import copy
import json
from dataclasses import replace

import pytest

from src.runtime.window import (WindowPolicy, WindowPolicyHooks, ContextOverflowError,
                                ContextWindowError, request_size, validate_pairs, view_hash)
from src.runtime.hooks import HookContext
from src.policy.plugin import FixturePolicyPlugin, NoOpPolicyPlugin, validate_decision, json_data


def history(count=4, body=8000, reasoning=600):
    messages=[{'role':'system','content':'System constraints'}, {'role':'user','content':'Original task'}]
    for i in range(count):
        messages += [{'role':'assistant','content':'analysis '* (reasoning//9), 'tool_calls':[
            {'id':f'call{i}','type':'function','function':{'name':'read_file','arguments':'{}'}}]},
            {'role':'tool','tool_call_id':f'call{i}','content':'raw-'+str(i)+'x'*body}]
    messages += [{'role':'assistant','content':None,'tool_calls':[
        {'id':'latest','type':'function','function':{'name':'run_command','arguments':'{}'}}]},
        {'role':'tool','tool_call_id':'latest','content':'Error: current failure must remain'}]
    return messages


def ctx(**kwargs):
    return HookContext(extra={'tools':[],'max_output_tokens':64,'public_task':{'task_id':'test'}, **kwargs})


@pytest.mark.asyncio
@pytest.mark.parametrize('strategy',['none','masking','summary','mask-then-summary'])
async def test_long_trace_strategy_views_are_legal_or_rejected_without_mutation(strategy):
    raw=history(); original=copy.deepcopy(raw)
    hook=WindowPolicyHooks(WindowPolicy(strategy,max_tokens=6000,keep_recent=1))
    context=ctx(source_event_seq=12)
    if strategy=='none':
        with pytest.raises(ContextOverflowError): await hook.before_llm(raw,context)
    else:
        view=await hook.before_llm(raw,context)
        validate_pairs(view)
        assert view[:2]==original[:2]
        assert view[-1]==original[-1]
        assert request_size(view)['admission_input_tokens']+64<=6000
        assert len(json.dumps(view))<len(json.dumps(raw))
    assert raw==original
    assert context.extra['context_stats']['raw_message_hash']==view_hash(raw)


@pytest.mark.asyncio
async def test_mask_then_summary_reduces_long_assistant_arguments_and_provenance():
    raw=history(reasoning=2000)
    context=ctx(source_event_seq=17)
    hook=WindowPolicyHooks(WindowPolicy('mask-then-summary',max_tokens=4000,keep_recent=1))
    view=await hook.before_llm(raw,context)
    stats=context.extra['context_stats']
    assert stats['actually_injected']=='mask-then-summary'
    record=stats['summary_records'][0]
    assert record['source_hash']==view_hash(raw[record['source_start']:record['source_end']])
    assert record['source_event_seq']==17 and record['model_calls']==0 and record['cost_provenance']=='no_model_call'
    assert record['model'] is None
    again=await hook.before_llm(raw,ctx())
    assert view==again and hook.state['summary_calls']==1


@pytest.mark.asyncio
async def test_none_counts_tools_unicode_arguments_and_output_reserve():
    raw=[{'role':'system','content':'sys'},{'role':'user','content':'task'}]
    hook=WindowPolicyHooks(WindowPolicy('none',max_tokens=2000))
    for context in [ctx(tools=[{'description':'汉'*1000}]),ctx(max_output_tokens=2000)]:
        with pytest.raises(ContextOverflowError): await hook.before_llm(raw,context)
    view=await hook.before_llm(raw,ctx())
    assert view==raw and view is not raw


@pytest.mark.asyncio
async def test_protected_failure_and_writes_never_masked_to_fit():
    raw=history(count=1,body=8000)
    raw[2]['tool_calls'][0]['function']['name']='write_file'
    for strategy in ('masking','summary','mask-then-summary'):
        with pytest.raises(ContextOverflowError):
            await WindowPolicyHooks(WindowPolicy(strategy,max_tokens=4000,keep_recent=0)).before_llm(raw,ctx())
    assert raw[3]['content'].startswith('raw-0')


@pytest.mark.parametrize('raw', [
    [{'role':'tool','tool_call_id':'missing','content':'x'}],
    [{'role':'assistant','tool_calls':[{'id':'x'},{'id':'x'}]}],
    [{'role':'assistant','tool_calls':[{'id':'x'}]}, {'role':'user','content':'interleaved'}, {'role':'tool','tool_call_id':'x'}],
    [{'role':'assistant','tool_calls':[{'id':'x'}]}],
])
def test_invalid_pairing_rejected(raw):
    with pytest.raises(ContextWindowError): validate_pairs(raw)


def candidate(name='valid', **kwargs):
    return dict(id=name,text='Use the public API',source='fixture://public-doc',reason='public hint',**kwargs)


@pytest.mark.asyncio
async def test_plugin_requested_actual_valid_stale_and_large_candidates():
    items=[candidate(),candidate('stale',repo_revision='old'),{**candidate('big'),'text':'z'*5000}]
    hook=WindowPolicyHooks(WindowPolicy('none',max_tokens=6000,max_injection_bytes=1000),FixturePolicyPlugin(items))
    raw=history(count=0)
    context=ctx(repo_revision='new')
    view=await hook.before_llm(raw,context)
    p=context.extra['context_stats']['plugin']
    assert len(p['requested'])==3 and [c['id'] for c in p['actually_injected']]==['valid']
    assert {c['rejection'] for c in p['rejected']}=={'revision_mismatch','injection_quota'}
    assert hook.state['plugin_state']=={'calls':1}
    assert 'Use the public API' in view[-1]['content'] and len(raw)==4


@pytest.mark.asyncio
async def test_optional_minor_fields_compatible_major_forbidden_and_actions_rejected():
    class Plugin(NoOpPolicyPlugin):
        schema_version='0.2'
        async def decide(self, data):
            return dict(schema_version='0.2',candidates=[candidate()],state={},optional_future={'x':1},
                        action_proposals=[{'tool':'run_command','arguments':{'command':'forbidden'}}])
    hook=WindowPolicyHooks(WindowPolicy(),Plugin())
    context=ctx()
    await hook.before_llm(history(count=0),context)
    p=context.extra['context_stats']['plugin']
    assert p['actually_injected'] and p['ignored_optional_fields']==['optional_future']
    assert p['action_proposals'][0]['status']=='rejected'
    with pytest.raises(ValueError): validate_decision({'schema_version':'1.0'})
    with pytest.raises(ValueError): validate_decision({'schema_version':'0.2','extension':{'hidden_tests':'no'}})
    with pytest.raises(ValueError): json_data({'oracle':'secret'})


@pytest.mark.asyncio
async def test_plugin_error_degrades_without_secret_error_text_or_private_input():
    class Broken(NoOpPolicyPlugin):
        async def decide(self, data):
            assert set(data)=={'schema_version','task','observations','repo_revision','budget','state'}
            assert all(set(x)=={'role','sha256'} for x in data['observations'])
            raise RuntimeError('SECRET_FROM_PROVIDER')
    context=ctx()
    raw=history(count=0)
    view=await WindowPolicyHooks(WindowPolicy(),Broken()).before_llm(raw,context)
    assert view==raw and context.extra['context_stats']['plugin']['method_degraded']
    assert 'SECRET_FROM_PROVIDER' not in repr(context.extra)


@pytest.mark.asyncio
async def test_summary_limit_does_not_reset_on_restore():
    raw=history(reasoning=2000)
    hook=WindowPolicyHooks(WindowPolicy('summary',max_tokens=4000,keep_recent=1,max_summary_calls=1))
    await hook.before_llm(raw,ctx())
    restored=WindowPolicyHooks(hook.policy)
    restored.restore(hook.state)
    assert restored.state['summary_calls']==1
    with pytest.raises(ContextOverflowError):
        await restored.before_llm(history(count=10,reasoning=2000),ctx())
