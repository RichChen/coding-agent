"""Offline checks for the frozen pilot, including accounting and full denominators."""
import json

import pytest

from scripts import run_summary_pilot as pilot
from src.llm.client import LLMResponse
from src.runtime.session import RunSession
from tests.test_true_summary import FakeSummaryProvider
from scripts.audit_summary_pilot import jsonl, usage


def test_jsonl_unicode_separators_and_zero_call_cost():
    value = dict(content='alpha\u2028beta\u2029gamma')
    assert jsonl(json.dumps(value,ensure_ascii=False)+'\n') == [value]
    assert usage([])['estimated_cost_usd_range'] == [0.0,0.0]


def test_exact_scoring_and_abstention():
    expected = pilot.dataset()[0]['private_expected']
    assert pilot.score_answer(json.dumps(expected), expected)['success']
    wrong = dict(expected, retry_limit=True)
    score = pilot.score_answer(json.dumps(wrong), expected)
    assert score['correct'] == 3 and score['unsupported_values'] == 1
    score = pilot.score_answer(json.dumps(dict.fromkeys(expected)), expected)
    assert score['correct'] == 0 and score['abstentions'] == 4
    for value in (None, '[]', '{', json.dumps(dict(expected, extra=1))):
        assert pilot.score_answer(value, expected)['correct'] == 0


def test_assigned_schedule_is_paired_and_complete():
    rows = pilot.schedule()
    assert rows == pilot.schedule() and len(rows) == 44
    assert len({r['run_id'] for r in rows}) == 44
    for task in pilot.dataset():
        for repeat in range(1, 4):
            assert {r['strategy'] for r in rows if r['task_id'] == task['task_id'] and r['repeat'] == repeat} == set(pilot.STRATEGIES)


@pytest.mark.asyncio
async def test_prepare_frozen_data_and_window_expectations(tmp_path):
    output = tmp_path/'pilot'
    await pilot.prepare(output)
    assert len(pilot.verify_frozen(output)['assigned']) == 44
    assert pilot.read(output/'offline-preflight.json')['model_calls'] == 0
    target = output/'data/old-facts/raw.json'
    target.write_text('[]', encoding='utf-8')
    with pytest.raises(ValueError, match='frozen data drift'):
        pilot.verify_frozen(output)


@pytest.mark.asyncio
async def test_trace_accounting_replay_and_private_grading(tmp_path, monkeypatch):
    output = tmp_path/'pilot'
    await pilot.prepare(output)
    original_build = pilot.build_agent
    expected = pilot.dataset()[0]['private_expected']

    def build(config, workspace):
        agent = original_build(config, workspace)
        agent.llm.api_key = 'offline-placeholder'
        agent.hooks.summary_provider = FakeSummaryProvider(LLMResponse(
            text=json.dumps({'summary': json.dumps(expected)}),
            usage=dict(prompt_tokens=100,completion_tokens=20,total_tokens=120,provenance='provider')))

        async def chat(*args, **kwargs):
            return LLMResponse(text=json.dumps(expected),finish_reason='stop',
                usage=dict(prompt_tokens=80,completion_tokens=20,total_tokens=100,provenance='provider'))

        agent.llm.chat = chat
        return agent

    monkeypatch.setattr(pilot, 'build_agent', build)
    row = next(r for r in pilot.schedule() if r['task_id']=='old-facts' and r['strategy']=='summary')
    result = await pilot.run_trace(output,row)
    assert result['success']
    run = pilot.read(output/'runs'/row['run_id']/'run-result.json')
    assert run['summary']['model_calls'] == 1
    assert run['model_budget']['calls_started'] == 2
    assert run['total_tokens'] == 220
    assert RunSession.replay(output/'runs'/row['run_id']/'session').terminal == run
    # Independent repair grades use status, not a serialized success property.
    repair = next(r for r in pilot.schedule() if r['phase']=='repair')
    pilot.save_json(output/'runs'/repair['run_id']/'evaluation-result.json',
                    dict(status='pass',passed=18,collected=18))
    rows = pilot.audit(output)
    assert len(rows) == 44
    assert next(r for r in rows if r['run_id']==repair['run_id'])['success']
    assert sum(r['status']=='not_completed' for r in rows) == 42
