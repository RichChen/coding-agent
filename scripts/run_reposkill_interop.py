#!/usr/bin/env python3
"""Explicit trusted-source, empty-memory H4 cross-repository smoke (off/on).

Without --allow-paid: freeze inputs and check the REAL adapter offline only.
No writes to the source repository. No proposal execution or model-use receipts.
"""
import argparse
import asyncio
import copy
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
# Never write bytecode into the reviewed external package/snapshot.
sys.dont_write_bytecode = True

from src.config.schema import HarnessConfig
from src.eval.contracts import PublicTask, EvaluationSpec, canonical_hash
from src.eval.deepseek_demo import candidate_diff, usage_report
from src.eval.grader import IndependentGrader, regenerate_report, save_json, tree_hash
from src.eval.h3_runner import run_h3
from src.execution.docker import read_workspace, validate_files
from src.harness.factory import build_agent, load_config
from src.policy.plugin import validate_decision
from src.policy.registry import PolicyPluginRegistry
from src.policy.reposkill import register_reposkill, source_files, source_digest
from src.runtime.hooks import HookContext
from src.runtime.session import RunSession, source_fingerprint
from src.runtime.window import view_hash
from src.tracing.store import EventStore, utc_now


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def copy_handoff(bundle, output):
    manifest = read(bundle/'manifest.json')
    require(manifest['policy_wire']=='0.1' and manifest['memory_snapshot']=='empty', 'unsupported handoff')
    # Copy only frozen artifacts, not the other project's reports, .env or history.
    for name, sha in manifest['artifacts'].items():
        validate_files({name:b''})
        path=bundle/name
        require(path.resolve().is_relative_to(bundle.resolve()) and not path.is_symlink(), 'unsafe handoff path')
        content=path.read_bytes()
        require(hashlib.sha256(content).hexdigest()==sha, 'handoff artifact changed')
        target=output/name
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(content)
    save_json(output/'manifest.json',manifest)
    return manifest


def configuration(requirements, spec):
    config=load_config('configs/deepseek.yaml')
    require(config['llm']['model']=='deepseek-flash', 'this frozen smoke requires deepseek-flash')
    config['llm']['max_tokens']=requirements['model_max_output_tokens']
    config['runtime'].update(max_steps=requirements['max_steps'],
        step_timeout_seconds=requirements['step_timeout_seconds'],
        total_timeout_seconds=requirements['total_timeout_seconds'])
    config['runtime']['context'].update(strategy=requirements['context_strategy'],
        max_tokens=requirements['context_max_tokens'], max_injection_bytes=requirements['max_injection_bytes'],
        plugin='reposkill', dispatcher='read_search', dispatcher_max_calls=8)
    config['runtime']['budget'].update(max_model_calls=requirements['max_model_calls'],
        max_tokens=requirements['max_tokens'], max_cost_usd=0.03,
        price_table={'prompt_per_1k':0.0003,'completion_per_1k':0.0012})
    config['retry']['max_retries']=0
    config['policy']['command']['docker_image']=spec.image
    config['tracing']['lifecycle_events']=False  # Session is the authoritative evidence.
    return HarnessConfig.model_validate(config).model_dump()


def make_registry(source, sha, task, tree, enabled):
    registry=PolicyPluginRegistry()
    adapter=register_reposkill(registry,source_root=source,approved_sha256=sha,
                               public_task=task,public_tree=tree,enabled=enabled)
    return registry, adapter


async def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle',required=True,type=Path)
    parser.add_argument('--plugin-source',required=True,type=Path)
    parser.add_argument('--approved-source-sha256',required=True)
    parser.add_argument('--output-dir',required=True,type=Path)
    parser.add_argument('--allow-paid',action='store_true')
    args=parser.parse_args()
    require(source_digest(args.plugin_source)==args.approved_source_sha256,'source does not match approval')
    output=args.output_dir.resolve()
    require(not output.is_relative_to(args.plugin_source.resolve()), 'evidence must not modify plugin repository')
    output.mkdir(parents=True,exist_ok=False)
    handoff=output/'handoff'
    manifest=copy_handoff(args.bundle,handoff)
    snapshot=output/'plugin-source'
    files=source_files(args.plugin_source)
    for name, data in files.items():
        path=snapshot/name; path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(data)
    require(source_digest(snapshot)==args.approved_source_sha256,'snapshot differs from approval')
    public=read(handoff/'agent-public-task.json')
    task=PublicTask.from_mapping(read(handoff/'public-task.json'))
    spec=EvaluationSpec.from_mapping(read(handoff/'private/evaluation-spec.json'))
    base=read_workspace(handoff/'public-workspace')
    require(tree_hash(base)==manifest['base_hash']==spec.base_hash, 'base mismatch')
    config=configuration(manifest['host_budget_requirements'],spec)
    registries={}
    checks={}
    policy_input=read(handoff/'fixture/policy-input.json')
    for enabled in (False,True):
        mode='on' if enabled else 'off'
        registry,adapter=make_registry(snapshot,args.approved_source_sha256,public,tuple(base),enabled)
        registries[mode]=registry
        projected=adapter.harness_public_task(adapter.decode_public_task(public)[0])
        require(projected==task.agent_payload(),'public DTO projection mismatch')
        plugin=registry.create('reposkill')
        first=validate_decision(await plugin.decide(copy.deepcopy(policy_input)))
        require(first==read(handoff/f'fixture/plugin-{mode}-decision.json'),'adapter differs from frozen handoff fixture')
        second_input=dict(policy_input,state=first['state'])
        second=validate_decision(await registry.create('reposkill').decide(second_input))
        require(second==validate_decision(await plugin.decide(second_input)),'new-instance restoration differs')
        checks[mode]=dict(binding=plugin.fingerprint(), fixture_equal=True, new_instance_state_equal=True,
                          candidates=len(first['candidates']), proposals=len(first['action_proposals']))
    require(checks['off']['binding']!=checks['on']['binding'],'enabled flag missing from binding')
    safe_config=copy.deepcopy(config); safe_config['llm']['api_key']='[REDACTED]'
    save_json(output/'frozen-config.json',safe_config)
    save_json(output/'preflight.json',dict(checks=checks, model_calls=0,
        source_sha256=args.approved_source_sha256,task_hash=canonical_hash(task.agent_payload()),
        private_spec_hash=spec.manifest()['private_spec_hash'],harness_code_hash=source_fingerprint(Path.cwd()),
        frozen_at=utc_now(), wire='0.1', memory_snapshot=[], proposals='host_dispatch_read_search',
        cost_limit_basis='USD 0.03 per run; peak uncached input/output prices, conservative cache-blind estimate; not billing',
        original_public_budget=public['budget'],
        budget_mapping='model calls and wall time enforced exactly; total tokens combined at 16000; input/output/tool sublimits not separately enforced',
        system_instruction='Use python -B for public checks; only edit settings.py. No new workspace files.'))
    print('real adapter offline preflight passed (off/on)',flush=True)
    if not args.allow_paid:
        return
    require(bool(config['llm']['api_key']), 'missing LLM_API_KEY')
    baseline=await IndependentGrader().evaluate(base,base,spec)
    save_json(output/'baseline-evaluation.json',baseline.to_dict())
    require(baseline.status in ('partial','fail') and baseline.failed>0,'baseline must fail before paid runs')
    print(f'baseline: {baseline.status} {baseline.passed}/{baseline.collected}',flush=True)
    results=[]; attempts=[]
    for mode in ('off','on'):
        agent=build_agent(copy.deepcopy(config),handoff/'public-workspace',plugin_registry=registries[mode])
        agent.system_prompt+='\nUse python -B for public checks; only edit settings.py. No new workspace files.'
        run_dir=output/mode
        try:
            evaluation=await run_h3(agent,task,spec,run_dir,config_hash=canonical_hash(config))
        finally:
            await agent.llm.aclose()
        row=dict(variant=mode,status=evaluation.status,passed=evaluation.passed,collected=evaluation.collected)
        if (run_dir/'run-result.json').exists():
            run=read(run_dir/'run-result.json')
            attempts.extend(run['llm_attempts'])
            row.update(model_calls=len(run['llm_attempts']),termination=run['termination_kind'],
                       usage=usage_report(run['llm_attempts'],config['llm']['model']))
            context=[e['plugin'] for e in run['context_events'] if 'plugin' in e]
            row['requested']=sum(len(p['requested']) for p in context)
            row['prepared_view_injections']=sum(len(p['actually_injected']) for p in context)
            row['proposals_rejected']=sum(len(p['action_proposals']) for p in context)
            row['degraded']=any(p['method_degraded'] for p in context)
            with EventStore(run_dir/'session',readonly=True) as store:
                events=store.read_events()
            if mode == 'off':
                require(all(p['reason']=='dispatcher_not_enabled' and p['status']=='rejected'
                            for ctx in context for p in ctx['action_proposals']), 'off proposal boundary changed')
            else:
                executed = [p for ctx in context for p in ctx['action_proposals']
                            if p['status'] == 'executed']
                require(executed and all(p['receipt']['success'] for p in executed),
                        'read/search proposals were not executed successfully')
                require(all(p['receipt']['tool'] in ('read', 'search') for p in executed),
                        'dispatcher executed an unsupported tool')
                require(any(e['event_type'] == 'plugin.dispatch' for e in events),
                        'dispatch receipt was not journaled')
            state=RunSession.replay(run_dir/'session')
            require(state.terminal==run,'terminal replay differs')
            exported=[json.loads(line) for line in (run_dir/'events.jsonl').read_bytes().splitlines()]
            require(events==exported,'JSONL differs from journal')
            # Evidence link only; NOT an InjectionReceipt or claim of model following.
            prepared_seq=None; links=[]
            for event in events:
                if event['event_type']=='context.prepared': prepared_seq=event['seq']
                if event['event_type']=='model.started':
                    require(prepared_seq is not None,'model started without a prepared view')
                    links.append(dict(context_seq=prepared_seq,model_seq=event['seq'],
                                      operation_id=event['operation_id'],attempt_id=event['attempt_id']))
            row['model_start_links']=links
            # Exact private canary + current credential scan across model-side data only.
            for path in run_dir.rglob('*'):
                if path.is_file() and 'evaluation' not in path.relative_to(run_dir).parts and path.name!='evaluation-result.json':
                    data=path.read_bytes()
                    require(b'PRIVATE_H4_CANARY_7f2c' not in data,'private grader canary reached agent evidence')
                    require(config['llm']['api_key'].encode() not in data,'credential leaked')
            row['private_canary_and_key_absent']=True
            row['replay_equal']=True
            if agent.execution_backend.snapshot is not None:
                (run_dir/'candidate.patch').write_text(candidate_diff(base,agent.execution_backend.snapshot),encoding='utf-8')
        before=(run_dir/'evaluation/report.md').read_bytes()
        regenerate_report(run_dir/'evaluation')
        require(before==(run_dir/'evaluation/report.md').read_bytes(),'report regeneration differs')
        results.append(row)
        save_json(output/'results.json',results)
        print(json.dumps(row,ensure_ascii=False),flush=True)
    save_json(output/'summary.json',dict(variants=results,full_denominator=2,
        passed=sum(r['status']=='pass' for r in results),usage=usage_report(attempts,config['llm']['model']),
        note='connection smoke only; synthetic task, empty memory, host read/search dispatch only; no performance conclusion'))
    require(not any(r.get('degraded',True) for r in results),'plugin integration degraded')
    require(results[0]['prepared_view_injections']==0 and results[1]['prepared_view_injections']>0,'plugin off/on injection not demonstrated')


if __name__=='__main__':
    asyncio.run(main())
