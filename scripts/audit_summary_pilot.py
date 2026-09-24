#!/usr/bin/env python3
"""Offline R2 audit and detailed report. No API requests, tools, or candidate execution."""
from __future__ import annotations

import argparse
import copy
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.run_summary_pilot import read, verify_frozen, score_answer, sha, ROOT
from src.eval.contracts import EvaluationSpec, canonical_hash
from src.eval.deepseek_demo import usage_report
from src.eval.grader import decode_snapshot, tree_hash, save_json
from src.harness.factory import load_config
from src.runtime.session import RunSession
from src.runtime.window import view_hash
from src.tracing.artifacts import ArtifactStore, atomic_replace
from src.tracing.store import EventStore


def require(value, message):
    if not value:
        raise ValueError(message)


def jsonl(text):
    # JSON strings may contain literal U+2028/U+2029. Only LF separates records.
    return [json.loads(line) for line in text.split('\n') if line]


def usage(attempts):
    result = usage_report(attempts, 'deepseek-flash')
    if not attempts:
        result['estimated_cost_usd_range'] = [0.0, 0.0]
        result['estimate_basis'] = 'no provider requests'
    return result


def audit_session(directory, *, context_only=False):
    run = read(directory/'run-result.json')
    require(RunSession.replay(directory/'session').terminal == run, 'replay terminal mismatch')
    with EventStore(directory/'session', readonly=True) as store:
        events = store.read_events()
        require(events == jsonl((directory/'events.jsonl').read_text(encoding='utf-8')), 'JSONL/SQLite mismatch')
        events = copy.deepcopy(events)
        artifacts = ArtifactStore(directory/'session/artifacts',store.run_id,readonly=True)
        for event in events:
            if set(event['payload']) == {'artifact_ref'}:
                event['payload'] = json.loads(artifacts.read(event['payload']['artifact_ref']))
    main = run.get('llm_attempts',[])
    summary = run.get('summary') or {}
    records = summary.get('records',[])
    called = [r for r in records if r.get('model_calls')]
    require(run['model_budget']['calls_started'] == len(main)+len(called), 'call ledger mismatch')
    require(sum(e['event_type']=='model.started' for e in events) == len(main), 'main intent mismatch')
    require(sum(e['event_type']=='summary.started' for e in events) == len(called), 'summary intent mismatch')
    states = {e['seq']:e['payload'] for e in events if e['event_type']=='state.saved'}
    for record in records:
        if record.get('source_event_seq'):
            original = states[record['source_event_seq']]['messages']
            require(view_hash(original) == record['raw_message_hash'], 'raw summary hash mismatch')
            require(view_hash(original[record['source_start']:record['source_end']]) == record['source_hash'], 'summary source hash mismatch')
    raw_hashes = {view_hash(s['messages']) for s in states.values() if 'messages' in s}
    prepared = [e['payload'] for e in events if e['event_type']=='context.prepared']
    for item in prepared:
        require(item['raw_message_hash'] in raw_hashes, 'view has no raw snapshot')
        require(view_hash(item['view']) == item['stats']['view_hash'], 'prepared view hash mismatch')
    if (directory/'view.json').exists():
        require(read(directory/'view.json') == prepared[-1]['view'], 'exported view mismatch')
    if (directory/'raw-messages.json').exists():
        require(view_hash(read(directory/'raw-messages.json')) in raw_hashes, 'exported raw mismatch')
    summary_attempts = [dict(usage=r.get('usage')) for r in called]
    all_usage = usage(main+summary_attempts)
    if not all_usage['unknown_usage_attempts']:
        require(all_usage['known_subtotals']['total_tokens'] == run['total_tokens'], 'total tokens mismatch')
        require(run['model_budget']['tokens_committed'] == run['total_tokens'], 'token ledger mismatch')
    # Every prepared main view is sent once under this no-retry contract.
    require(len(prepared) == (1 if context_only else len(main)), 'prepared/main call mismatch')
    return dict(run=run, prepared=prepared, records=records, main_usage=usage(main),
        summary_usage=usage(summary_attempts), total_usage=all_usage,
        audit=dict(journal_equals_jsonl=True,replay_equal=True,raw_view_source_hashes=True,
                   call_and_token_accounting=True,replay_external_calls=0))


def audit_repair(output, row, directory, run):
    data = output/'repair-data'/row['task_id']
    spec = EvaluationSpec.from_mapping(read(data/'private-spec.json'))
    manifest = read(directory/'manifest.json')
    grade = read(directory/'evaluation-result.json')
    baseline = read(output/'baselines'/f"{row['task_id']}.json")
    require(baseline['failed'] > 0 and baseline['manifest']['candidate_hash']==spec.base_hash, 'unverified original defect')
    require(baseline['manifest']['private_spec_hash']==spec.manifest()['private_spec_hash'], 'baseline spec mismatch')
    require(tree_hash(decode_snapshot(read(directory/'base.json'))) == spec.base_hash == manifest['base_hash'], 'base drift')
    require(canonical_hash(read(directory/'public-task.json')) == manifest['public_task_hash'], 'public task drift')
    require(grade == read(directory/'evaluation/results.json')[0], 'grade bundle mismatch')
    require(manifest['private_spec_hash'] == spec.manifest()['private_spec_hash'] == grade['manifest']['private_spec_hash'], 'grader spec drift')
    if (directory/'candidate.json').exists():
        require(tree_hash(decode_snapshot(read(directory/'candidate.json'))) == run['execution']['candidate_hash'] == grade['manifest']['candidate_hash'], 'candidate drift')
    return dict(baseline_passed=baseline['passed'],passed=grade['passed'],collected=grade['collected'],
        agent_cleanup_ok=(run.get('execution') or {}).get('cleanup_ok'),
        grader_cleanup_ok=all(c['cleanup_ok'] for c in grade['cases']),
        baseline_cleanup_ok=all(c['cleanup_ok'] for c in baseline['cases']))


def audit(output, smoke):
    frozen = verify_frozen(output)
    rows, all_main, all_summary = [], [], []
    for assigned in frozen['assigned']:
        directory = output/'runs'/assigned['run_id']
        require((directory/'evaluation-result.json').exists(), 'assigned run missing: '+assigned['run_id'])
        evidence = audit_session(directory)
        run = evidence['run']; grade = read(directory/'evaluation-result.json')
        called = [r for r in evidence['records'] if r.get('model_calls')]
        all_main.extend(run.get('llm_attempts',[]))
        all_summary.extend(dict(usage=r.get('usage')) for r in called)
        row = dict(assigned,status=grade.get('status') or run.get('termination_kind') or 'answered',
            success=grade.get('success',grade.get('status')=='pass'),
            termination=run.get('termination_kind') or run.get('failure_reason'),
            main_calls=len(run.get('llm_attempts',[])),summary_calls=len(called),
            summary_statuses=[r['status'] for r in called],
            main_usage=evidence['main_usage'],summary_usage=evidence['summary_usage'],total_usage=evidence['total_usage'],
            conservative_cost_usd=run['model_budget']['cost_committed'],
            total_elapsed_ms=run['total_elapsed_ms'],summary_elapsed_ms=sum(r.get('elapsed_seconds',0)*1000 for r in called),
            main_elapsed_ms=sum(a['elapsed_ms'] for a in run.get('llm_attempts',[])),
            main_request_bytes=sum(p['stats']['serialized_bytes'] for p in evidence['prepared']),
            summary_request_bytes=sum(r['request_size']['serialized_bytes'] for r in called),
            main_estimated_input_tokens=sum(p['stats']['estimated_input_tokens'] for p in evidence['prepared']),
            tools=run['total_tool_invocations'],audit=evidence['audit'])
        if assigned['phase']=='trace':
            expected = read(output/'private'/f"{assigned['task_id']}.json")
            scored = score_answer(run['final_answer'],expected)
            require(all(grade[k]==v for k,v in scored.items()), 'trace score drift')
            raw = read(output/'data'/assigned['task_id']/'raw.json')
            require(read(directory/'manifest.json')['raw_message_hash']==view_hash(raw), 'frozen trace raw drift')
            row.update(scored)
            row['summary_exact_value_mentions'] = grade['summary_exact_value_mentions']
        else:
            row.update(audit_repair(output,assigned,directory,run))
        rows.append(row)
    smoke_data = audit_session(smoke, context_only=True)
    smoke_run = smoke_data['run']
    require(smoke_run['success'] and smoke_run['summary']['model_calls']==1, 'smoke unsuccessful')
    # Check the exact configured secret without logging it; all evidence files, including SQLite.
    key = load_config(ROOT/'configs/deepseek.yaml')['llm']['api_key']
    require(bool(key), 'credential scan unavailable')
    scanned = 0
    for root in (output,smoke):
        for path in root.rglob('*'):
            if path.is_file():
                require(key.encode() not in path.read_bytes(), 'configured key found in evidence')
                scanned += 1
    public_paths = []
    for directory in (output/'runs').iterdir():
        public_paths.extend(p for p in (directory/'session').rglob('*') if p.is_file())
        public_paths.extend(directory/name for name in ('run-result.json','events.jsonl','manifest.json','view.json','public-task.json') if (directory/name).exists())
    for path in public_paths:
        require(b'PRIVATE_H4_CANARY_7f2c' not in path.read_bytes(), 'private grader canary entered agent evidence')
    smoke_attempts = [dict(usage=r['usage']) for r in smoke_run['summary']['records'] if r.get('model_calls')]
    result = dict(assigned=len(rows),completed=len(rows),rows=rows,
        pilot_main_usage=usage(all_main),pilot_summary_usage=usage(all_summary),
        including_smoke_usage=usage(all_main+all_summary+smoke_attempts),
        including_smoke_conservative_usd=sum(r['conservative_cost_usd'] for r in rows)+smoke_run['model_budget']['cost_committed'],
        smoke=dict(audit=smoke_data['audit'],usage=smoke_data['total_usage'],summary_calls=1),
        credential_scan=dict(configured_key_absent=True,files_scanned=scanned),
        private_canary_absent_from_agent_artifacts=True, auditor_sha256=sha(__file__))
    save_json(output/'detailed-audit.json',result)
    lines = ['# R2 detailed offline audit','','All 44 assigned runs retained. Repeats are not independent tasks; trace and repair outcomes are not pooled.','',
        '| Phase / task | Strategy | Completed | Exact facts | All-correct / grader pass | Overflow | Null facts | Wrong nonnull | Summary calls | Main / summary tokens | Peak cache-aware USD | Mean elapsed s |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for phase,task,strategy in dict.fromkeys((r['phase'],r['task_id'],r['strategy']) for r in rows):
        group = [r for r in rows if (r['phase'],r['task_id'],r['strategy'])==(phase,task,strategy)]
        facts = f"{sum(r.get('correct',0) for r in group)}/{4*len(group)}" if phase=='trace' else '-'
        costs = [r['total_usage']['estimated_cost_usd_range'] for r in group]
        peak = f'{sum(c[1] for c in costs):.8f}' if all(c is not None for c in costs) else 'unknown'
        main_tokens = sum(r['main_usage']['known_subtotals']['total_tokens'] for r in group)
        summary_tokens = sum(r['summary_usage']['known_subtotals']['total_tokens'] for r in group)
        unknown = ' + unknown' if any(r['total_usage']['unknown_usage_attempts'] for r in group) else ''
        lines.append(f"| {phase} / {task} | {strategy} | {len(group)}/{len(group)} | {facts} | {sum(r['success'] for r in group)}/{len(group)} | {sum(r['termination']=='context_overflow' for r in group)} | {sum(r.get('abstentions',0) for r in group)} | {sum(r.get('unsupported_values',0) for r in group)} | {sum(r['summary_calls'] for r in group)} | {main_tokens} / {summary_tokens}{unknown} | {peak} | {sum(r['total_elapsed_ms'] for r in group)/len(group)/1000:.3f} |")
    lines += ['', 'Per-run input bytes, estimated input tokens, main/summary elapsed time and usage, cleanup, grades, and terminations: detailed-audit.json.',
        'All cached/time-of-day costs are estimates, not account billing. Provider usage is kept separate from byte-based admission estimates.',
        'All sources, prepared views, terminal replay, SQLite/JSONL, calls and token ledgers checked offline. No model/tool execution during audit.',
        'The original frozen runner remains unchanged. This auditor parses JSONL by LF so literal Unicode line separators remain inside JSON strings.', '']
    atomic_replace(output/'detailed-report.md','\n'.join(lines).encode())
    print(json.dumps(dict(assigned=len(rows),audited=len(rows)+1,
        total_usage=result['including_smoke_usage'],conservative_usd=result['including_smoke_conservative_usd'],
        statuses=dict(Counter(r['status'] for r in rows))),ensure_ascii=False,indent=2))


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',required=True,type=Path)
    parser.add_argument('--smoke-dir',required=True,type=Path)
    args = parser.parse_args()
    audit(args.output_dir.resolve(),args.smoke_dir.resolve())
