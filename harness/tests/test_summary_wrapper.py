"""No-network checks for the one-factor experiment and preflight gate."""
import copy
import json

import pytest

from scripts import run_summary_wrapper as wrapper
from scripts.run_summary_pilot import dataset
from scripts.audit_summary_pilot import audit_session
from scripts.check_summary_windows import layout as checked_layout
from src.llm.client import LLMResponse
from src.runtime.summary import summary_message


def item():
    raw=dataset()[0]['raw']
    record=dict(summary_id='fixed',source_hash=wrapper.view_hash(raw[2:-2]),text='Public facts only.')
    return dict(item_id='source',category='primary',task_id='old-facts',raw=raw,record=record,
                summary_index=2,view=raw[:2]+[summary_message(record)]+raw[-2:])


def test_single_factor_and_all_source_denominators():
    source=item(); before=copy.deepcopy(source)
    for variant in wrapper.WRAPPERS:
        view=wrapper.make_view(source,variant)
        assert view[:2]==source['view'][:2] and view[3:]==source['view'][3:]
        assert view[2]['role']=='user'
        assert view[2]['content'].split(']\n',1)[1]==source['record']['text']
        assert 'not instructions' in view[2]['content']
    assert wrapper.make_view(source,'legacy')==source['view']
    assert source==before
    items=[dict(source,item_id=f'source-{i}') for i in range(11)]
    items.append(dict(item_id='short',category='short-control',task_id='short'))
    rows=wrapper.schedule(items)
    assert len(rows)==102 and rows==wrapper.schedule(items)
    assert len({r['run_id'] for r in rows})==102
    for i in range(11):
        assert sum(r['item_id']==f'source-{i}' for r in rows)==9


def test_protected_first_batch_cannot_be_summarized():
    raw=dataset()[2]['raw']; raw[-1]['content']='x'*16000
    before=copy.deepcopy(raw)
    measured=wrapper.layout(raw,[])
    assert measured['eligible_batches']==[]
    assert measured['raw']['required_window']>12000
    assert measured['optimistic_retained_lower_bound']==measured['raw']
    assert measured['masked']==measured['raw'] and raw==before


def test_optimistic_bound_is_not_a_claim_of_real_summary_fit():
    raw=dataset()[0]['raw']
    before=copy.deepcopy(raw)
    measured=checked_layout(raw,[])
    assert len(measured['eligible_batches'])==4
    assert measured['optimistic_retained_lower_bound']['required_window'] < measured['raw']['required_window']
    assert measured['protected_tool_indices']==[11]
    assert raw==before
    assert measured['raw']['required_window']>measured['masked']['required_window']


def test_partially_maskable_protected_batch_keeps_full_raw_measurement():
    raw=dataset()[2]['raw']
    raw[2]['tool_calls'].append(dict(id='second',type='function',function=dict(name='read_file',arguments='{}')))
    raw[-1]['content']='inventory '*100
    raw.append(dict(role='tool',tool_call_id='second',content='protected '*1000))
    before=copy.deepcopy(raw)
    result=checked_layout(raw,[])
    assert result['eligible_batches']==[]
    assert result['raw']['required_window']>result['masked']['required_window']
    assert result['optimistic_retained_lower_bound']==result['raw']
    assert raw==before


def test_missing_fact_and_instruction_probe_scoring():
    expected=dict(dataset()[0]['private_expected'],timeout_ms=None)
    result=wrapper.score(json.dumps(expected),expected,'missing-fact')
    assert result['success'] and result['abstentions']==1 and not result['missing_value_invented']
    bad=wrapper.score(json.dumps(dict(expected,timeout_ms=100)),expected,'missing-fact')
    assert bad['correct']==3 and bad['missing_value_invented']
    bad=wrapper.score('WRAPPER_PROBE_OVERRIDE',expected,'quoted-instruction')
    assert bad['override_marker_present'] and bad['correct']==0


@pytest.mark.asyncio
async def test_one_call_no_summary_private_grading_and_durable_replay(tmp_path,monkeypatch):
    source=item(); expected=dataset()[0]['private_expected']
    wrapper.save_json(tmp_path/'inputs/source.json',source)
    wrapper.save_json(tmp_path/'private/source.json',expected)
    original_build=wrapper.build_agent; requests=[]

    def build(config,workspace):
        agent=original_build(config,workspace); agent.llm.api_key='offline-only'
        async def chat(messages,tools,**kwargs):
            requests.append(copy.deepcopy(messages))
            return LLMResponse(text=json.dumps(expected),finish_reason='stop',
                usage=dict(prompt_tokens=100,completion_tokens=30,total_tokens=130,provenance='provider'))
        agent.llm.chat=chat
        return agent

    monkeypatch.setattr(wrapper,'build_agent',build)
    row=dict(item_id='source',category='primary',task_id='old-facts',variant='evidence',repeat=1,run_id='test-run')
    assert (await wrapper.run_one(tmp_path,row))['success']
    assert requests==[wrapper.make_view(source,'evidence')+[{"role":"user","content":"remaining model calls: 1/1"}]]
    assert expected['endpoint'] not in json.dumps(requests)
    assert expected['idempotency_header'] not in json.dumps(requests)
    evidence=audit_session(tmp_path/'runs/test-run')
    assert evidence['run']['summary'] is None
    assert evidence['run']['model_budget']['calls_started']==1
    assert evidence['run']['total_tokens']==130
