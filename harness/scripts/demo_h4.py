#!/usr/bin/env python3
"""Offline H4 mechanism demo: four model views, policy gating, raw evidence.

No model or Docker access. This demonstrates mechanisms, not model task scores.
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))

from src.eval.grader import save_json
from src.policy.plugin import FixturePolicyPlugin
from src.runtime.hooks import HookContext
from src.runtime.window import WindowPolicy, WindowPolicyHooks, ContextWindowError, view_hash
from src.runtime.session import source_fingerprint
from src.tracing.artifacts import atomic_replace


def transcript():
    raw=[{'role':'system','content':'Preserve constraints and verify changes.'},
         {'role':'user','content':'Fix the public function; keep the latest failure in view.'}]
    for index in range(4):
        raw += [{'role':'assistant','content':'past analysis '*160,'tool_calls':[
                    {'id':f'call-{index}','type':'function','function':{'name':'read_file','arguments':'{}'}}]},
                {'role':'tool','tool_call_id':f'call-{index}','content':f'public file {index}\n'+'x'*8000}]
    raw += [{'role':'assistant','content':None,'tool_calls':[
                {'id':'current','type':'function','function':{'name':'run_command','arguments':'{}'}}]},
            {'role':'tool','tool_call_id':'current','content':'Error: latest public test still fails.'}]
    return raw


async def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',required=True,help='New directory; prior results are never overwritten')
    args=parser.parse_args()
    directory=Path(args.output_dir); directory.mkdir(parents=True,exist_ok=False)
    raw=transcript(); raw_hash=view_hash(raw)
    save_json(directory/'raw-messages.json',raw)
    candidates=[dict(id='valid',text='Consult the current public API.',source='fixture://api',reason='known current',repo_revision='v2'),
                dict(id='old',text='Use the old public API.',source='fixture://api-v1',reason='stale example',repo_revision='v1'),
                dict(id='large',text='z'*8000,source='fixture://large',reason='quota example')]
    results=[]
    for strategy in ('none','masking','summary','mask-then-summary'):
        hook=WindowPolicyHooks(WindowPolicy(strategy,max_tokens=6000,keep_recent=1,max_injection_bytes=1000),FixturePolicyPlugin(candidates))
        context=HookContext(extra={'public_task':{'task_id':'mechanism'},'repo_revision':'v2',
                                  'tools':[],'max_output_tokens':256,'source_event_seq':None})
        try:
            view=await hook.before_llm(raw,context)
            save_json(directory/(strategy+'-view.json'),view)
            result=dict(strategy=strategy,status='ready',stats=context.extra['context_stats'])
        except ContextWindowError as exc:
            result=dict(strategy=strategy,status=exc.kind,stats=exc.stats)
        assert view_hash(raw)==raw_hash
        results.append(result)
    save_json(directory/'manifest.json',dict(schema_version='0.1',experiment='offline-fixture',raw_hash=raw_hash,
        code_hash=source_fingerprint(Path(__file__).resolve().parents[1]),model_calls=0,model_cost_usd=0,
        cost_provenance='no_model_call',window=6000,reserved_output_tokens=256))
    save_json(directory/'results.json',results)
    lines=['# H4 offline mechanism evidence','','All four policies consume the same raw transcript. No model calls.',
           'Overflow means a request was rejected before sending, not a failed provider request.','',
           '| Policy | Status | Applied | Summary calls (fixture) | Plugin requested / injected |',
           '| --- | --- | --- | --- | --- |']
    for r in results:
        s=r['stats']; p=s.get('plugin',{})
        lines.append(f"| {r['strategy']} | {r['status']} | {s.get('actually_injected','none')} | {s.get('summary_calls',0)} | {len(p.get('requested',[]))} / {len(p.get('actually_injected',[]))} |")
    atomic_replace(directory/'report.md',('\n'.join(lines)+'\n').encode())
    print('\n'.join(lines))


if __name__=='__main__': asyncio.run(main())
