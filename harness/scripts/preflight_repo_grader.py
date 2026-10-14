#!/usr/bin/env python3
"""No-model full-repository environment, baseline, positive and negative acceptance."""
import argparse
import asyncio
from dataclasses import asdict, replace
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.eval.contracts import canonical_hash
from src.eval.grader import decode_snapshot, save_json
from src.eval.repo_report import save_bundle, regenerate_report
from src.eval.repo_grader import RepositorySpec, RepositoryGrader, RUNNER_HASH
from src.runtime.session import source_fingerprint

ROOT=Path(__file__).resolve().parents[1]
TARGET='tests/test_config.py::test_config_from_file_toml'


def load(path): return json.loads(Path(path).read_text(encoding='utf-8'))


def negative_checks(results):
    """Validate each intended failure, including dependency failure loading conftest."""
    if len(results)!=5 or any(r['status']=='pass' for r in results): return False
    missing=results[3].get('evidence',{})
    receipt=missing.get('receipt') or {}
    execution=missing.get('execution',{})
    return (all(r['status']=='fail' and r['reason']=='protected_or_unassigned_path_changed' for r in results[:2]) and
        results[2]['reason']=='missing_or_incomplete_receipt' and
        execution.get('status')=='failed' and execution.get('exit_code')==receipt.get('exit_code') and
        receipt.get('exit_code') in (2,4) and
        'deliberately_missing_repo_dependency' in execution.get('stderr','') and
        results[4].get('evidence',{}).get('execution',{}).get('status')=='timed_out')


async def run(source,output,image,context):
    output.mkdir(parents=True,exist_ok=False)
    base=decode_snapshot(load(source/'public/base.json')); overlay=load(source/'private/overlay.json')
    known=decode_snapshot(load(source/'private/known-good.json'))
    grader=RepositoryGrader(context=context)
    specs=dict(task_id='pallets__flask-4992',base_hash=load(source/'source.json')['base_hash'],image=image,
        editable_paths=('src/flask/config.py',),test_paths=('tests',),python_paths=('src',),test_overlay=overlay)
    save_json(output/'manifest.json',dict(source=str(source),source_manifest_hash=canonical_hash(load(source/'source.json')),
        image=image,context=context,runner_hash=RUNNER_HASH,code_hash=source_fingerprint(ROOT),model_calls=0,
        assigned=['collection','baseline','known-good','tampered-test','fake-pytest','fake-pass','missing-dependency','timeout']))
    print('collecting complete tests directory',flush=True)
    collection=await grader.collect(base,image=image,test_paths=('tests',),python_paths=('src',),overlay=decode_snapshot(overlay))
    save_json(output/'collection.json',collection)
    if collection['status']!='ready':
        save_json(output/'readiness.json',dict(status='invalid_env',phase='collection',model_calls=0))
        print('collection invalid_env; evidence retained',flush=True); return False
    ids=tuple(collection['receipt']['collected'])
    if TARGET not in ids: raise ValueError('target regression missing from collection')
    spec=RepositorySpec(expected_nodeids=ids,**specs)
    save_json(output/'private-spec-initial.json',asdict(spec))
    print(f'frozen {len(ids)} identities; executing baseline',flush=True)
    baseline=await grader.evaluate(base,base,spec)
    save_json(output/'baseline.json',baseline)
    outcomes={c['nodeid']:c['outcome'] for c in baseline['cases']}
    if baseline['status']=='invalid_env' or outcomes.get(TARGET)!='failed':
        save_json(output/'readiness.json',dict(status='invalid_env',phase='baseline_defect',model_calls=0))
        print('baseline invalid or target defect not reproduced',flush=True); return False
    allowed={n:s for n,s in outcomes.items() if s in ('skipped','xfailed')}
    passed=tuple(n for n,s in outcomes.items() if s=='passed')
    spec=replace(spec,allowed_nonpass=allowed,baseline_passed=passed)
    save_json(output/'private-spec.json',asdict(spec))
    print(f'baseline: {baseline["passed"]}/{len(ids)}; {baseline["failed"]} not satisfied; calibrating known-good',flush=True)
    positive=await grader.evaluate(base,known,spec)
    save_json(output/'known-good.json',positive)
    print(f'known-good: {positive["status"]} {positive["passed"]}/{len(ids)}',flush=True)
    cases={
        'tampered-test':{**known,'tests/test_config.py':b'def test_fake(): pass\n'},
        'fake-pytest':{**known,'pytest.py':b'print("all tests passed")\n'},
        'fake-pass':{**base,'src/flask/config.py':b'import os\nprint("ALL TESTS PASSED", flush=True)\nos._exit(0)\n'},
        'missing-dependency':{**base,'src/flask/config.py':b'import deliberately_missing_repo_dependency\n'},
        'timeout':{**base,'src/flask/config.py':b'import time\ntime.sleep(60)\n'},
    }
    results=[dict(baseline,task_id='baseline'),dict(positive,task_id='known-good')]
    for name,candidate in cases.items():
        print('negative: '+name,flush=True)
        graded=await grader.evaluate(base,candidate,replace(spec,timeout_seconds=2) if name=='timeout' else spec)
        save_json(output/f'{name}.json',graded)
        results.append(dict(graded,task_id=name))
    # Module import must refer to candidate workspace, including after editable image install.
    imports=(positive.get('evidence',{}).get('receipt') or {}).get('workspace_imports',{})
    import_ok=imports.get('flask')=='/workspace/src/flask/__init__.py'
    negatives_ok=negative_checks(results[2:])
    clean=all(r.get('evidence',{}).get('cleanup_ok',True) for r in results)
    ready=positive['status']=='pass' and negatives_ok and clean and import_ok
    save_bundle(output/'evaluation',dict(assigned_task_ids=[r['task_id'] for r in results],
        model_calls=0,purpose='grader calibration; negative rejection is desired, not agent success rate',runner_hash=RUNNER_HASH),results)
    report=output/'evaluation/report.md'; before=report.read_bytes(); regenerate_report(report.parent)
    if before!=report.read_bytes(): raise ValueError('offline report not reproducible')
    readiness=dict(status='ready' if ready else 'not_ready',collected=len(ids),required=len(ids)-len(allowed),
        baseline_passed=baseline['passed'],baseline_failed_nodes=[n for n,s in outcomes.items() if s=='failed'],
        baseline_allowed_nonpass=allowed,known_good_status=positive['status'],known_good_passed=positive['passed'],
        regressions_preserved=positive.get('regression_passed'),regressions_assigned=len(passed),
        negative_checks_passed=negatives_ok,cleanup_verified=clean,candidate_import_verified=import_ok,
        offline_report_reproducible=True,model_calls=0)
    save_json(output/'readiness.json',readiness)
    print(json.dumps(readiness,ensure_ascii=False),flush=True)
    return ready


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-dir',required=True,type=Path); p.add_argument('--output-dir',required=True,type=Path)
    p.add_argument('--image',required=True); p.add_argument('--context',default='desktop-linux')
    args=p.parse_args()
    if not asyncio.run(run(args.source_dir.resolve(),args.output_dir.resolve(),args.image,args.context)):
        raise SystemExit(2)
