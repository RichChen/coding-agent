#!/usr/bin/env python3
"""Frozen R2 context-policy pilot. Prepare/audit are offline; runs require --allow-paid."""
from __future__ import annotations

import argparse
import asyncio
import copy
import hashlib
import json
import random
import sys
import time
from dataclasses import asdict, replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config.schema import HarnessConfig
from src.eval.contracts import PublicTask, EvaluationSpec, canonical_hash
from src.eval.deepseek_demo import prepare as prepare_boltons, candidate_diff, usage_report
from src.eval.grader import IndependentGrader, save_json, tree_hash
from src.eval.h3_runner import run_h3
from src.execution.docker import read_workspace
from src.harness.factory import build_agent, load_config
from src.runtime.hooks import HookContext
from src.runtime.loop import AgentRunResult, FailureReason
from src.runtime.session import RunSession, compatibility, plain, runtime_fingerprint, source_fingerprint
from src.runtime.summary import summary_totals
from src.runtime.window import WindowPolicy, WindowPolicyHooks, ContextWindowError, view_hash, request_size
from src.tracing.artifacts import atomic_replace
from src.tracing.store import EventStore, utc_now

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT/'docs/upgrade/R2-EXPERIMENT-CONTRACT.zh-CN.md'
PRICE_VERSION = 'deepseek-official-2026-09-21-peak'
STRATEGIES = ('none', 'masking', 'summary', 'mask-then-summary')
FIELDS = ('endpoint', 'timeout_ms', 'retry_limit', 'idempotency_header')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dataset():
    """Authored synthetic histories, not represented as actual executed tools."""
    tasks = []
    for index, name in enumerate(('old-facts', 'assistant-pressure', 'short-control')):
        facts = dict(endpoint=('/v2/telemetry', '/v3/batch-events', '/v1/health-events')[index],
            timeout_ms=(1750, 2350, 850)[index], retry_limit=(3, 2, 4)[index],
            idempotency_header=('X-Run-Token','X-Batch-Key','X-Event-Nonce')[index])
        task = ('Recover the CURRENT accepted deployment settings from the earlier public observations. '
            'Return ONLY a JSON object with exactly these keys: endpoint, timeout_ms, retry_limit, '
            'idempotency_header. Use the documented string/integer values, not defaults or guesses. '
            'If a value is not supported by visible evidence, return null for that key. '
            'Do not infer configuration from record counts, timestamps, or route enumeration. '
            'No new tools are available; do not claim the integration issue is fixed.')
        raw = [dict(role='system',content='Use only visible public evidence. Preserve uncertainty. Return the requested JSON.'),
               dict(role='user',content=task)]
        count = 1 if name == 'short-control' else 4
        for batch in range(count):
            notes = f'Read public deployment evidence batch {batch}.'
            if name == 'assistant-pressure':
                notes += '\n' + '\n'.join(
                    f'Navigation item {i:03d}: inspect module dependency references without changing deployment configuration.'
                    for i in range(24))
            content = ('Accepted CURRENT deployment configuration; authoritative public release record:\n'
                + json.dumps(facts, sort_keys=True) + '\n') if batch == 0 else (
                f'Public inventory batch {batch}; navigation records only, not configuration defaults.\n')
            if name != 'short-control':
                content += '\n'.join(f'Inventory record {i:03d}: module component_{batch}_{i:03d}; public interface listed; review pending.'
                                     for i in range(44))
            call = f'public-{batch}'
            raw += [dict(role='assistant',content=notes,tool_calls=[dict(id=call,type='function',
                function=dict(name='read_file',arguments=json.dumps({'path':f'public-{batch}.txt'})))]),
                dict(role='tool',tool_call_id=call,content=content)]
        if name != 'short-control':
            raw += [dict(role='assistant',content='Check the latest public integration observation.',tool_calls=[
                dict(id='latest',type='function',function=dict(name='run_command',arguments='{"command":"public-check"}'))]),
                dict(role='tool',tool_call_id='latest',content='Error: integration remains unresolved. Recover documented settings before proposing changes.')]
        tasks.append(dict(task_id=name, raw=raw, private_expected=facts))
    return tasks


def score_answer(text, expected):
    try:
        answer = json.loads(text)
        valid = isinstance(answer, dict) and set(answer) == set(FIELDS)
    except (ValueError, TypeError):
        answer, valid = {}, False
    correct = {k: valid and type(answer.get(k)) is type(v) and answer.get(k) == v for k,v in expected.items()}
    return dict(valid_json=valid, correct=sum(correct.values()), total=len(expected),
                success=all(correct.values()), fields=correct,
                abstentions=sum(valid and answer.get(k) is None for k in expected),
                unsupported_values=sum(valid and answer.get(k) is not None and not correct[k] for k in expected))


def config_for(strategy, phase, image=None):
    c = load_config(ROOT/'configs/deepseek.yaml')
    c['llm'].update(model='deepseek-flash',thinking='disabled',temperature=0,
                    max_tokens=512 if phase == 'trace' else 2048)
    c['retry']['max_retries'] = 0
    c['runtime'].update(max_steps=1 if phase == 'trace' else 20,
        step_timeout_seconds=120,total_timeout_seconds=120 if phase == 'trace' else 600)
    c['runtime']['context'].update(strategy=strategy,max_tokens=8000 if phase == 'trace' else 12000,
        keep_recent_tool_results=1,summary_provider='llm' if strategy in ('summary','mask-then-summary') else 'fixture',
        summary_max_calls=1 if phase == 'trace' else 2,summary_max_tokens=131072,
        summary_max_output_tokens=512,summary_failure='reject',summary_price_version=PRICE_VERSION,
        plugin='noop',dispatcher='disabled',dispatcher_max_calls=0)
    c['runtime']['budget'].update(max_model_calls=2 if phase == 'trace' else 24,
        max_tokens=131072 if phase == 'trace' else 200000,max_cost_usd=.05 if phase == 'trace' else .30,
        price_table={'prompt_per_1k':.0003,'completion_per_1k':.0012})
    c['tracing'].update(lifecycle_events=False,llm_stream_events=False)
    if phase == 'trace':
        c['tools']['enabled'] = []
        c['policy']['command']['execution_profile'] = 'legacy_host'
    else:
        c['policy']['tool_output_max_chars'] = 4000
        c['policy']['command']['docker_image'] = image
    return HarnessConfig.model_validate(c).model_dump()


def public_config(config):
    result = copy.deepcopy(config)
    result['llm']['api_key'] = '[REDACTED]'
    return result


def schedule():
    rng = random.Random(20260921)
    rows = []
    for phase, tasks, repeats, variants in [('trace', [d['task_id'] for d in dataset()], 3, STRATEGIES),
            ('repair', ['boltons-475-strutils-slice','public-settings-001'], 2, ('masking','summary'))]:
        for task in tasks:
            for repeat in range(1,repeats+1):
                ordered = list(variants); rng.shuffle(ordered)
                for strategy in ordered:
                    rows.append(dict(phase=phase,task_id=task,repeat=repeat,strategy=strategy,
                                     run_id=f'{phase}-{task}-r{repeat}-{strategy}'))
    return rows


async def prepare(output):
    output.mkdir(parents=True,exist_ok=False)
    metadata = dict(contract_sha256=sha(CONTRACT),code_hash=source_fingerprint(ROOT),
        runner_sha256=sha(__file__),created_at=utc_now(),order_seed=20260921,provider_seed=None,
        assigned=schedule(),model='deepseek-flash',price_version=PRICE_VERSION,
        phase_hard_cost_usd={'trace':1.8,'repair':2.4},provider_requests_serial=True)
    checks = []
    for item in dataset():
        directory = output/'data'/item['task_id']
        save_json(directory/'raw.json',item['raw'])
        save_json(output/'private'/f"{item['task_id']}.json",item['private_expected'])
        for strategy in STRATEGIES:
            hook = WindowPolicyHooks(WindowPolicy(strategy,max_tokens=8000,keep_recent=1))
            ctx = HookContext(extra={'tools':[],'max_output_tokens':512})
            try:
                view = await hook.before_llm(item['raw'],ctx)
                status = 'ready'
            except ContextWindowError as exc:
                status = exc.kind
            checks.append(dict(task_id=item['task_id'],strategy=strategy,status=status,
                fixture_generations=hook.state['summary_calls']))
    wanted = {'old-facts':('context_overflow','ready','ready','ready'),
              'assistant-pressure':('context_overflow','context_overflow','ready','ready'),
              'short-control':('ready',)*4}
    for name, expected in wanted.items():
        actual = tuple(x['status'] for x in checks if x['task_id'] == name)
        if actual != expected: raise ValueError(f'offline window baseline mismatch: {name}: {actual}')
    save_json(output/'offline-preflight.json',dict(model_calls=0,windows=checks))
    local = ROOT/'docs/upgrade/evidence/H5/deepseek-flash-attempt-01/seed'
    base, task, spec = await prepare_boltons(output/'repair-data'/'boltons-475-strutils-slice',local)
    handoff = ROOT/'docs/upgrade/evidence/H5-interop/real-04/handoff'
    directory = output/'repair-data'/'public-settings-001'
    base = read_workspace(handoff/'public-workspace')
    spec = EvaluationSpec.from_mapping(read(handoff/'private/evaluation-spec.json'))
    if tree_hash(base) != spec.base_hash: raise ValueError('settings seed drift')
    for name, content in base.items():
        target = directory/'seed'/name; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(content)
    save_json(directory/'public-task.json',read(handoff/'public-task.json'))
    save_json(directory/'private-spec.json',asdict(spec))
    for strategy in STRATEGIES:
        save_json(output/'configs'/f'trace-{strategy}.json',public_config(config_for(strategy,'trace')))
    for task_id in ('boltons-475-strutils-slice','public-settings-001'):
        image = read(output/'repair-data'/task_id/'private-spec.json')['image']
        for strategy in ('masking','summary'):
            save_json(output/'configs'/f'repair-{task_id}-{strategy}.json',public_config(config_for(strategy,'repair',image)))
    metadata['data_sha256'] = {p.relative_to(output).as_posix():sha(p) for parent in ('data','private','repair-data','configs')
                               for p in sorted((output/parent).rglob('*')) if p.is_file()}
    save_json(output/'experiment.json',metadata)
    print(json.dumps(dict(preflight='passed',assigned=len(metadata['assigned']),model_calls=0)),flush=True)


def verify_frozen(output):
    m = read(output/'experiment.json')
    if (m['contract_sha256'] != sha(CONTRACT) or m['code_hash'] != source_fingerprint(ROOT)
            or m['runner_sha256'] != sha(__file__)):
        raise ValueError('frozen code/contract drift; create a new attempt, do not overwrite')
    for name, checksum in m['data_sha256'].items():
        if sha(output/name) != checksum: raise ValueError('frozen data drift: '+name)
    return m


async def run_trace(output, row):
    directory = output/'runs'/row['run_id']; directory.mkdir(parents=True,exist_ok=False)
    workspace = directory/'workspace'; workspace.mkdir()
    raw = read(output/'data'/row['task_id']/'raw.json')
    c = config_for(row['strategy'],'trace')
    if public_config(c) != read(output/'configs'/f"trace-{row['strategy']}.json"):
        raise ValueError('frozen trace config drift')
    agent = build_agent(c,workspace)
    if not agent.llm.api_key: raise ValueError('host credentials unavailable')
    manifest = dict(row,raw_message_hash=view_hash(raw),config=public_config(c),
        context_policy=agent.hooks.fingerprint(),code_hash=source_fingerprint(ROOT),
        source='synthetic-public-history', started_at=utc_now())
    save_json(directory/'manifest.json',manifest)
    expected = compatibility(workspace=workspace,code_id=source_fingerprint(ROOT),config=manifest,backend='context-only')
    started = time.monotonic(); events = []; answer = None; error = None
    try:
        with RunSession.create(directory/'session',task_id=row['task_id'],expected=expected,timeout_seconds=120) as session:
            agent.session = session; agent.retry.session = session
            agent.deadline.set_run(120); agent.deadline.begin_step(120)
            session.append('runtime.bound',dict(hash=runtime_fingerprint(agent)))
            session.save_loop(dict(messages=raw,step_number=0))
            try:
                view = await agent._model_view(raw,[],raw[1]['content'],row['task_id'],0,events)
                save_json(directory/'view.json',view)
                response = await agent._call_llm(view,[],0)
                if response.finish_reason != 'stop' or response.tool_calls:
                    error = 'incomplete_answer'
                else:
                    answer = response.text
                session.save_loop(dict(messages=raw,step_number=0,response=plain(response)))
            except Exception as exc:
                error = exc.kind if isinstance(exc,ContextWindowError) else type(exc).__name__
                if isinstance(exc,ContextWindowError):
                    events.append(dict(exc.stats,error_kind=exc.kind))
                    session.append('context.rejected',dict(exc.stats,error_kind=exc.kind))
            summary = summary_totals(agent.hooks.state)
            attempts = agent._attempt_dicts()
            main_tokens = sum((a.get('usage') or {}).get('total_tokens') or 0 for a in attempts)
            result = AgentRunResult(task_id=row['task_id'],success=error is None,
                final_answer=answer,failure_reason=FailureReason.NONE if error is None else FailureReason.CONTEXT_INVALID,
                termination_kind=error,total_elapsed_ms=(time.monotonic()-started)*1000,
                total_tokens=main_tokens+summary['known_total_tokens'],llm_attempts=attempts,
                context_events=events,summary=summary,model_budget=agent.model_ledger.snapshot())
            session.finish(result); session.store.export_jsonl(directory/'events.jsonl')
            save_json(directory/'run-result.json',plain(result))
    finally:
        await agent.llm.aclose()
    expected_answer = read(output/'private'/f"{row['task_id']}.json")
    evaluation = score_answer(answer,expected_answer)
    evaluation['summary_exact_value_mentions'] = {k:any(str(v) in r.get('text','') for r in agent.hooks.state['summaries'])
                                                 for k,v in expected_answer.items()}
    evaluation['summary_coverage_method'] = 'literal value presence only, not semantic verification'
    save_json(directory/'evaluation-result.json',evaluation)
    return evaluation


async def run_repairs(output, rows):
    # All baseline defects are reproduced before any paid repair invocation.
    for task_id in dict.fromkeys(r['task_id'] for r in rows):
        directory = output/'repair-data'/task_id
        spec = EvaluationSpec.from_mapping(read(directory/'private-spec.json'))
        base = read_workspace(directory/'seed')
        path = output/'baselines'/f'{task_id}.json'
        if path.exists():
            baseline = read(path)
        else:
            baseline = (await IndependentGrader().evaluate(base,base,spec)).to_dict()
            save_json(path,baseline)
        if baseline['status'] not in ('partial','fail') or baseline['failed'] <= 0:
            raise ValueError('baseline defect/environment not verified: '+task_id)
    for row in rows:
        run_dir = output/'runs'/row['run_id']
        if run_dir.exists():
            if (run_dir/'evaluation-result.json').exists(): continue
            raise ValueError('incomplete prior attempt; refusing automatic retry: '+row['run_id'])
        directory = output/'repair-data'/row['task_id']
        spec = EvaluationSpec.from_mapping(read(directory/'private-spec.json'))
        c = config_for(row['strategy'],'repair',spec.image)
        if public_config(c) != read(output/'configs'/f"repair-{row['task_id']}-{row['strategy']}.json"):
            raise ValueError('frozen repair config drift')
        task = PublicTask.from_mapping(read(directory/'public-task.json'))
        budgets = {k:c['runtime'][k] for k in ('max_steps','step_timeout_seconds','total_timeout_seconds')}
        budgets.update({k:c['runtime']['budget'][k] for k in ('max_model_calls','max_tokens','max_cost_usd')})
        task = replace(task,budget=budgets)
        agent = build_agent(c,directory/'seed')
        agent.system_prompt += '\nUse python -B for public checks. Only edit the requested implementation file. Do not create new files or modify tests.'
        print('starting '+row['run_id'],flush=True)
        try:
            result = await run_h3(agent,task,spec,run_dir,config_hash=canonical_hash(c))
        finally:
            await agent.llm.aclose()
        if agent.execution_backend.snapshot is not None:
            atomic_replace(run_dir/'candidate.patch',candidate_diff(read_workspace(directory/'seed'),agent.execution_backend.snapshot).encode())
        save_json(run_dir/'pilot-row.json',row)
        print(json.dumps(dict(row,status=result.status,passed=result.passed,collected=result.collected)),flush=True)


def audit(output):
    manifest = read(output/'experiment.json'); rows = []; checks = []
    for assigned in manifest['assigned']:
        directory = output/'runs'/assigned['run_id']
        if not (directory/'evaluation-result.json').exists():
            rows.append(dict(assigned,status='not_completed',success=False)); continue
        evaluation = read(directory/'evaluation-result.json')
        run = read(directory/'run-result.json') if (directory/'run-result.json').exists() else {}
        summary = run.get('summary') or {}
        attempts = run.get('llm_attempts',[])
        summary_attempts = [dict(usage=r.get('usage')) for r in summary.get('records',[]) if r.get('model_calls')]
        usage = usage_report(attempts+summary_attempts,'deepseek-flash')
        state = RunSession.replay(directory/'session') if (directory/'session').exists() else None
        if state:
            with EventStore(directory/'session',readonly=True) as store:
                exported = [json.loads(s) for s in (directory/'events.jsonl').read_text(encoding='utf-8').splitlines()]
                if exported != store.read_events(): raise ValueError('JSONL/journal mismatch')
            if state.terminal != run: raise ValueError('terminal/replay mismatch')
            budget = run['model_budget']
            if budget['calls_started'] != len(attempts)+summary.get('model_calls',0):
                raise ValueError('call ledger mismatch')
            # Resolve source snapshots from the authoritative journal including artifact payloads.
            with EventStore(directory/'session',readonly=True) as store:
                source_events = store.read_events()
            from src.tracing.artifacts import ArtifactStore
            # Artifact ownership is bound to the store run ID, not the public manifest.
            with EventStore(directory/'session',readonly=True) as store:
                artifacts = ArtifactStore(directory/'session/artifacts',store.run_id,readonly=True)
                for event in source_events:
                    if set(event['payload']) == {'artifact_ref'}:
                        event['payload'] = json.loads(artifacts.read(event['payload']['artifact_ref']))
            for record in summary.get('records',[]):
                seq = record.get('source_event_seq')
                if seq:
                    original = source_events[seq-1]['payload']['messages']
                    if view_hash(original) != record['raw_message_hash'] or view_hash(original[record['source_start']:record['source_end']]) != record['source_hash']:
                        raise ValueError('summary source mismatch')
            checks.append(dict(run_id=assigned['run_id'],journal_equals_jsonl=True,source_hashes=True,replay_external_calls=0))
        estimates = [e.get('serialized_bytes') for e in run.get('context_events',[]) if e.get('view_hash')]
        rows.append(dict(assigned,status=evaluation.get('status') or run.get('termination_kind') or 'answered',
            success=evaluation.get('success',evaluation.get('status') == 'pass'),correct=evaluation.get('correct'),facts=evaluation.get('total'),
            passed=evaluation.get('passed'),collected=evaluation.get('collected'),
            abstentions=evaluation.get('abstentions'),unsupported_values=evaluation.get('unsupported_values'),
            summary_calls=summary.get('model_calls',0),main_calls=len(attempts),usage=usage,
            summary_known_tokens=summary.get('known_total_tokens',0),
            committed_usd=(run.get('model_budget') or {}).get('cost_committed'),
            total_elapsed_ms=run.get('total_elapsed_ms'),sent_view_bytes=sum(estimates),
            cleanup_ok=(run.get('execution') or {}).get('cleanup_ok'),
            termination=run.get('termination_kind')))
    save_json(output/'results.json',dict(assigned=len(manifest['assigned']),rows=rows))
    save_json(output/'audit.json',dict(checks=checks,completed=len(checks),assigned=len(rows)))
    lines = ['# R2 summary pilot results','','Exploratory fixed-history and two-task repair pilot; not a benchmark success-rate claim.','',
        '| Phase | Task | Strategy | Completed / assigned | Exact facts | Independent pass | Summary calls | Provider tokens | Peak estimate USD |',
        '|---|---|---|---:|---:|---:|---:|---:|---:|']
    for phase in ('trace','repair'):
        for task_id in dict.fromkeys(r['task_id'] for r in rows if r['phase']==phase):
            for strategy in STRATEGIES if phase=='trace' else ('masking','summary'):
                group = [r for r in rows if r['phase']==phase and r['task_id']==task_id and r['strategy']==strategy]
                completed = [r for r in group if r['status']!='not_completed']
                tokens = sum(r['usage']['known_subtotals']['total_tokens'] for r in completed)
                if any(r['usage']['unknown_usage_attempts'] for r in completed):
                    tokens = str(tokens) + ' + unknown'
                costs = [r['usage']['estimated_cost_usd_range'] for r in completed]
                cost = sum(c[1] for c in costs if c) if all(c or r['main_calls']+r['summary_calls']==0 for c,r in zip(costs,completed)) else None
                facts = f"{sum(r.get('correct') or 0 for r in group)}/{4*len(group)}" if phase=='trace' else '-'
                lines.append(f"| {phase} | {task_id} | {strategy} | {len(completed)}/{len(group)} | {facts} | {sum(r['success'] for r in group)}/{len(group)} | {sum(r.get('summary_calls',0) for r in group)} | {tokens} | {cost} |")
    lines += ['', 'All assigned runs retained, including overflow and invalid environment. No automatic paid retry.',
        'Unknown usage/cost is retained in results.json; 0-call rejected requests cost zero.',
        'Fixed-history exact facts and repair grader pass are different outcomes; do not pool them.',
        'Cache/time-of-day affect billed estimates. Both cache-aware intervals and conservative run commitments are retained.',
        'Literal summary value presence is not a semantic-faithfulness guarantee.', '']
    atomic_replace(output/'report.md','\n'.join(lines).encode())
    print('\n'.join(lines),flush=True)
    return rows


async def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=['prepare','run-traces','run-repairs','audit'])
    p.add_argument('--output-dir',required=True,type=Path)
    p.add_argument('--allow-paid',action='store_true')
    args = p.parse_args(); output = args.output_dir.resolve()
    if args.mode == 'prepare': return await prepare(output)
    if args.mode == 'audit': return audit(output)
    if not args.allow_paid: p.error('paid phases require --allow-paid')
    manifest = verify_frozen(output)
    if not load_config(ROOT/'configs/deepseek.yaml')['llm']['api_key']:
        raise ValueError('host credentials unavailable')
    rows = [r for r in manifest['assigned'] if r['phase']==('trace' if args.mode=='run-traces' else 'repair')]
    if args.mode == 'run-traces':
        for row in rows:
            directory = output/'runs'/row['run_id']
            if directory.exists():
                if (directory/'evaluation-result.json').exists(): continue
                raise ValueError('incomplete prior attempt; refusing paid retry')
            print('starting '+row['run_id'],flush=True)
            evaluation = await run_trace(output,row)
            print(json.dumps(dict(row,correct=evaluation['correct'],success=evaluation['success'])),flush=True)
    else:
        await run_repairs(output,rows)
    audit(output)


if __name__ == '__main__': asyncio.run(main())
