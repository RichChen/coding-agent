#!/usr/bin/env python3
"""Corrected offline preflight. Keeps frozen experiment inputs and old tables intact."""
import argparse
import asyncio
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import run_summary_wrapper as frozen
from src.eval.grader import save_json
from src.runtime.hooks import HookContext
from src.runtime.window import WindowPolicy, WindowPolicyHooks, ContextWindowError, request_size, view_hash
from src.tracing.artifacts import atomic_replace


def layout(raw,tools):
    # The legacy masking helper mutates its list. Never pass authoritative raw to it.
    result=frozen.layout(copy.deepcopy(raw),tools)
    size=request_size(raw,tools,2048)
    result['raw']=dict(size,required_window=size['admission_input_tokens']+2048)
    return result


async def check(output):
    frozen.verify(output)
    events={}; details=[]; decisions=[]; first_seen=set()
    inputs=[]
    for path in sorted((output/'window-inputs').glob('*.json')):
        item=frozen.read(path); inputs.append(item)
    inputs.sort(key=lambda x:(x['run_id'],x['seq']))
    for item in inputs:
        run_id=item['run_id']; seq=item['seq']; raw=item['raw']; tools=item['tools']
        if run_id not in events:
            events[run_id]=frozen.events_resolved(frozen.BASE/'runs'/run_id/'session')
        source=events[run_id][seq-1]
        frozen.require(source['event_type']=='state.saved' and source['payload']['messages']==raw,'frozen raw not original snapshot')
        first=run_id not in first_seen; first_seen.add(run_id)
        raw_hash=view_hash(raw); sizes=layout(raw,tools)
        frozen.require(view_hash(raw)==raw_hash,'preflight mutated raw')
        for limit in (12000,16000,24000):
            for strategy in ('none','masking','summary'):
                hook=WindowPolicyHooks(WindowPolicy(strategy,max_tokens=limit,keep_recent=1))
                ctx=HookContext(extra=dict(tools=tools,max_output_tokens=2048))
                try:
                    view=await hook.before_llm(raw,ctx)
                    status='ready'; required=request_size(view,tools,2048)['admission_input_tokens']+2048
                except ContextWindowError as exc:
                    status=exc.kind; required=exc.stats.get('admission_input_tokens',0)+2048
                frozen.require(view_hash(raw)==raw_hash,'window hook mutated raw')
                details.append(dict(run_id=run_id,task_id=item['task_id'],source_seq=seq,raw_hash=raw_hash,
                    first_batch=first,window=limit,strategy=strategy,status=status,required_window=required,
                    fixture_summaries=hook.state['summary_calls'],
                    summary_skip_reason=ctx.extra.get('context_stats',{}).get('summary_skip_reason'),**sizes))
    for run_id in events:
        history=[r for r in details if r['run_id']==run_id]
        first=next(r for r in history if r['first_batch'])
        recorded=frozen.read(frozen.BASE/'runs'/run_id/'run-result.json')['context_events']
        match=next((r for r in recorded if r['raw_message_hash']==first['raw_hash']),None)
        frozen.require(match is not None,'first raw hash absent from original admission events')
        # Compare original rejection/ready request sizes only where no summary/masking changed that view.
        if first['task_id']=='boltons-475-strutils-slice':
            strategy=frozen.read(frozen.BASE/'runs'/run_id/'manifest.json')['context_policy']['policy']['strategy']
            measured=next(r for r in history if r['first_batch'] and r['window']==12000 and r['strategy']==strategy)
            frozen.require(match['admission_input_tokens']+match['reserved_output_tokens']==measured['required_window'],'original Boltons admission not reproduced')
        for limit in (12000,16000,24000):
            group=[r for r in history if r['window']==limit]
            first_fit=next(r for r in group if r['first_batch'] and r['strategy']=='none')['status']=='ready'
            no_pressure=all(r['status']=='ready' for r in group if r['strategy']=='none')
            skip=limit==12000 and not first_fit and not first['eligible_batches']
            decisions.append(dict(run_id=run_id,window=limit,first_batch_required=first['raw']['required_window'],
                first_batch_eligible=len(first['eligible_batches']),first_batch_feasible=first_fit,
                no_observed_summary_pressure=no_pressure,observed_snapshots=len({r['source_seq'] for r in group}),
                decision='skip_paid' if skip else ('no_observed_summary_pressure' if no_pressure else 'observed_pressure_requires_new_repair_contract')))
    result=dict(model_calls=0,docker_calls=0,details=details,decisions=decisions,script_sha256=frozen.sha(__file__),
        supersedes='window-preflight.json (masking helper mutated in-memory raw before measurements; saved window-inputs remained original)',
        original_snapshot_hashes_verified=True,pilot_01_unchanged=True)
    save_json(output/'window-preflight-corrected.json',result)
    lines=['# Corrected window feasibility','','No model calls or Docker execution. Original snapshots verified; policy checks cannot mutate raw.',
        'Supersedes window-preflight.json. That first preflight inadvertently used an in-place masking helper on its raw list; saved window-inputs were written before mutation and remain authoritative. Paid wrapper inputs and results are unaffected.','',
        '| Source run | Window | First batch required | Eligible batches | First batch fits | Any observed raw pressure | Decision |',
        '|---|---:|---:|---:|---|---|---|']
    for r in decisions:
        lines.append(f"| {r['run_id']} | {r['window']} | {r['first_batch_required']} | {r['first_batch_eligible']} | {r['first_batch_feasible']} | {not r['no_observed_summary_pressure']} | {r['decision']} |")
    lines+=['','Required window is conservative byte-based admission plus 2048 output reservation, not provider tokenizer usage.',
        'Each snapshot is checked independently; fixture fit does not prove LLM summary fit, and a larger window does not predict the next trajectory.','']
    atomic_replace(output/'window-report.md','\n'.join(lines).encode())
    frozen.require(frozen.file_hashes(frozen.BASE)==frozen.read(output/'pilot-01-hashes.json'),'pilot-01 changed')
    print(json.dumps(dict(verified_snapshots=len(inputs),checks=len(details),model_calls=0,
        first_batch_required=sorted({r['first_batch_required'] for r in decisions}))),flush=True)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--output-dir',required=True,type=Path)
    asyncio.run(check(parser.parse_args().output_dir.resolve()))
