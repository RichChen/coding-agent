#!/usr/bin/env python3
"""Grade fixed full-repository snapshots or regenerate a hash-checked report offline."""
import argparse
import asyncio
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.eval.contracts import canonical_hash
from src.eval.grader import decode_snapshot, save_json
from src.eval.repo_report import save_bundle, regenerate_report
from src.eval.repo_grader import RepositorySpec, RepositoryGrader, RUNNER_HASH


def load(path): return json.loads(Path(path).read_text(encoding='utf-8'))


async def grade(assignments,output,context):
    assignments=Path(assignments).resolve(); rows=load(assignments)
    ids=[r['task_id'] for r in rows]
    if not ids or len(set(ids))!=len(ids): raise ValueError('unique nonempty assignment ids required')
    output=Path(output).resolve(); output.mkdir(parents=True,exist_ok=False)
    results=[]
    save_json(output/'assigned.json',rows)
    for row in rows:
        spec=None
        try:
            spec=RepositorySpec.from_mapping(load(assignments.parent/row['spec']))
            if spec.task_id!=row['task_id']: raise ValueError('task identity mismatch')
            base=decode_snapshot(load(assignments.parent/row['base']))
            candidate=decode_snapshot(load(assignments.parent/row['candidate']))
            result=await RepositoryGrader(context=context).evaluate(base,candidate,spec)
        except Exception as exc:
            result=dict(task_id=row['task_id'],status='invalid_env',passed=0,
                collected=len(spec.expected_nodeids) if spec else 0,
                reason=type(exc).__name__+': '+str(exc)[:500])
            if spec: result['manifest']=spec.manifest()
        results.append(result)
        save_json(output/f'result-{len(results):03}.json',result)
        print(json.dumps({k:result.get(k) for k in ('task_id','status','passed','collected','reason')}),flush=True)
    save_bundle(output/'evaluation',dict(assigned_task_ids=ids,assignments_hash=canonical_hash(rows),runner_hash=RUNNER_HASH,
        model_calls=0,scope='complete repository / frozen pytest collection',context=context),results)
    return results


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--assignments'); mode.add_argument('--regenerate')
    parser.add_argument('--output-dir'); parser.add_argument('--context',default='desktop-linux')
    args=parser.parse_args()
    if args.regenerate: regenerate_report(args.regenerate)
    elif not args.output_dir: parser.error('--output-dir required')
    else:
        results=asyncio.run(grade(args.assignments,args.output_dir,args.context))
        if any(r['status']!='pass' for r in results): raise SystemExit(2)
