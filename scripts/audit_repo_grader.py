#!/usr/bin/env python3
"""Offline evidence audit and public handoff, without executing candidate code."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.prepare_repo_grader import extract, REV
from scripts.preflight_repo_grader import negative_checks, TARGET
from src.eval.contracts import canonical_hash
from src.eval.grader import decode_snapshot, encode_snapshot, save_json, tree_hash
from src.eval.repo_grader import RepositorySpec, RUNNER_HASH, classify_receipt
from src.eval.repo_report import report_text
from src.runtime.session import source_fingerprint

ROOT=Path(__file__).resolve().parents[1]


def load(path): return json.loads(path.read_text(encoding='utf-8'))
def sha(data): return hashlib.sha256(data).hexdigest()


def audit(source, validation, previous, output):
    checks={}
    def check(name,condition):
        checks[name]=bool(condition)
        if not condition: raise ValueError('audit failed: '+name)

    source,validation,previous,output=map(lambda p:Path(p).resolve(),(source,validation,previous,output))
    if output.exists(): raise ValueError('audit output must be new')
    manifest=load(source/'source.json')
    base=decode_snapshot(load(source/'public/base.json'))
    overlay=decode_snapshot(load(source/'private/overlay.json'))
    known=decode_snapshot(load(source/'private/known-good.json'))
    archive=(source/'flask-base.tar.gz').read_bytes()
    check('fixed_full_archive',sha(archive)==manifest['archive_sha256'] and extract(archive)==base and manifest['revision']==REV)
    check('complete_source_manifest',len(base)==manifest['files']==250 and sum(map(len,base.values()))==manifest['bytes'] and
        tree_hash(base)==manifest['base_hash'] and not manifest['excluded_upstream_paths'] and
        {n:sha(b) for n,b in base.items()}==manifest['original_file_hashes'])
    check('public_private_separation',set(p.name for p in (source/'public').iterdir())=={'base.json','task.json'} and
        not any('.oracle' in n or '.grader_private' in n for n in base) and
        base['src/flask/config.py']!=known['src/flask/config.py'])
    check('complete_private_overlay',set(overlay)=={'tests/test_config.py','tests/static/config.toml'} and
        tree_hash(overlay)==manifest['overlay_hash'])
    check('known_good_only_allowed_change',tree_hash(known)==manifest['known_good_hash'] and
        [n for n in base.keys()|known.keys() if base.get(n)!=known.get(n)]==['src/flask/config.py'])
    prep=load(source/'preparation.json')
    check('frozen_build_inputs',sha((source/'build/Dockerfile').read_bytes())==prep['dockerfile_sha256'] and
        sha((source/'build/requirements.lock').read_bytes())==prep['requirements_sha256'] and
        {p.relative_to(source/'build/base').as_posix():p.read_bytes() for p in (source/'build/base').rglob('*') if p.is_file()}==base)
    run=load(validation/'manifest.json'); readiness=load(validation/'readiness.json')
    spec=RepositorySpec.from_mapping(load(validation/'private-spec.json'))
    initial=RepositorySpec.from_mapping(load(validation/'private-spec-initial.json'))
    collection=load(validation/'collection.json')
    ids=collection['receipt']['collected']
    check('unchanged_full_denominator',len(ids)==484 and len(set(ids))==484 and
        ids==load(previous/'collection.json')['receipt']['collected'] and tuple(ids)==spec.expected_nodeids==initial.expected_nodeids)
    check('spec_and_execution_frozen',run['runner_hash']==RUNNER_HASH==spec.runner_hash and
        run['image']==spec.image and run['source_manifest_hash']==canonical_hash(manifest) and
        spec.base_hash==manifest['base_hash'] and decode_snapshot(spec.test_overlay)==overlay)
    check('implementation_unchanged_since_preflight',run['code_hash']==source_fingerprint(ROOT))
    baseline=load(validation/'baseline.json'); positive=load(validation/'known-good.json')
    before,error=classify_receipt(baseline['evidence']['receipt'],ids)
    after,error2=classify_receipt(positive['evidence']['receipt'],ids)
    check('independent_receipt_validation',error is None and error2 is None)
    check('baseline_defect_and_all_regressions',baseline['manifest']['private_spec_hash']==initial.manifest()['private_spec_hash'] and
        [n for n,v in before.items() if v=='failed']==[TARGET] and
        set(spec.baseline_passed)=={n for n,v in before.items() if v=='passed'} and len(spec.baseline_passed)==481)
    check('explicit_unchanged_skips',spec.allowed_nonpass=={n:v for n,v in before.items() if v in ('skipped','xfailed')} and
        len(spec.allowed_nonpass)==2 and all(after[n]==v=='skipped' for n,v in spec.allowed_nonpass.items()))
    check('known_good_full_success',positive['status']=='pass' and positive['passed']==482 and
        positive['regression_passed']==positive['regression_assigned']==481 and after[TARGET]=='passed' and
        all(v=='passed' or spec.allowed_nonpass.get(n)==v for n,v in after.items()) and
        positive['manifest']['private_spec_hash']==spec.manifest()['private_spec_hash'] and
        positive['manifest']['candidate_hash']==manifest['known_good_hash'])
    names=['tampered-test','fake-pytest','fake-pass','missing-dependency','timeout']
    negatives=[load(validation/(n+'.json')) for n in names]
    check('all_intended_negative_rejections',negative_checks(negatives) and all(r['collected']==484 for r in negatives))
    check('full_assigned_preflight',run['assigned']==['collection','baseline','known-good',*names] and run['model_calls']==0)
    evidence=[collection]+[r['evidence'] for r in [baseline,positive,*negatives] if 'evidence' in r]
    check('container_cleanup_and_image',all(e['cleanup_ok'] and e['lifecycle'][-1]['event']=='destroyed' and
        e['lifecycle'][0]['image_id']==spec.image.split('@')[1] for e in evidence))
    check('resource_and_network_boundaries',all(e['capabilities']['network_default']=='none' and
        not e['capabilities']['host_mounts'] and not e['capabilities']['privileged'] and
        e['capabilities']['memory_limit_bytes']==1073741824 and e['capabilities']['pids_limit']==128 and
        e['capabilities']['workspace_transfer_limit']==8388608 for e in evidence))
    requirements=dict(line.split('==') for line in (source/'build/requirements.lock').read_text().splitlines() if line)
    check('recorded_pinned_dependencies',all(all(e['environment']['packages'].get(n)==v for n,v in requirements.items()) and
        e['environment']['python'].startswith('3.11.') and 'Werkzeug==2.2.2' in e['pip_freeze'] for e in evidence))
    check('candidate_import_not_image_base',positive['evidence']['receipt']['workspace_imports']['flask']=='/workspace/src/flask/__init__.py')
    bundle=load(validation/'evaluation/manifest.json'); results=load(validation/'evaluation/results.json')
    check('offline_report_and_results',canonical_hash(results)==bundle['results_hash'] and
        (validation/'evaluation/report.md').read_text(encoding='utf-8')==report_text(bundle,results) and
        [r['task_id'] for r in results]==['baseline','known-good',*names])
    check('final_readiness_matches_evidence',readiness['status']=='ready' and readiness['collected']==484 and
        readiness['required']==482 and readiness['negative_checks_passed'] and readiness['model_calls']==0)
    inventory=load(source/'fixture-inventory.json')
    check('all_twelve_environments_accounted',len(inventory)==12 and sum(r['decision']=='blocked_transfer_quota' for r in inventory)==8)
    for row in inventory:
        row['grader_readiness']='ready' if row['task_id']=='swebench_pallets__flask-4992' else row['decision']
        if row['grader_readiness']=='ready':
            row['full_source_files']=len(base); row['full_source_bytes']=sum(map(len,base.values()))
    implementation=sorted((ROOT/'src').rglob('*.py'))+[ROOT/'pyproject.toml']
    implementation += [ROOT/'scripts'/name for name in ('prepare_repo_grader.py','preflight_repo_grader.py','run_repo_grader.py','audit_repo_grader.py')]
    implementation += [ROOT/'tests/test_repo_grader.py']
    code={p.relative_to(ROOT).as_posix():p.read_bytes() for p in implementation}
    output.mkdir(parents=True)
    save_json(output/'implementation.json',encode_snapshot(code))
    save_json(output/'readiness-inventory.json',inventory)
    save_json(output/'audit.json',dict(status='ready',checks=checks,source=str(source),validation=str(validation),
        implementation_hash=tree_hash(code),code_hash=source_fingerprint(ROOT),model_calls=0,
        evidence_sha256={str(p.relative_to(validation)):sha(p.read_bytes()) for p in validation.rglob('*') if p.is_file()}))
    save_json(output/'public-handoff.json',dict(task_id=spec.task_id,status='ready',image=spec.image,
        docker_context=run['context'],base_hash=spec.base_hash,base_revision=REV,
        public_base=str(source/'public/base.json'),public_task=str(source/'public/task.json'),
        editable_paths=list(spec.editable_paths),source_scope='complete upstream repository',
        transfer_limit_bytes=8388608,max_files=2048,model_calls=0,
        lifecycle='Freeze candidate after agent stop and cleanup; evaluate privately in a fresh container.',
        fingerprint_policy='Freeze pilot source fingerprint after concurrent code changes stabilize.'))
    print(json.dumps(dict(status='ready',checks_passed=len(checks),ready_environments=1,assigned_environments=12,model_calls=0)))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for option in ('source-dir','validation-dir','previous-validation-dir','output-dir'): p.add_argument('--'+option,required=True)
    a=p.parse_args(); audit(a.source_dir,a.validation_dir,a.previous_validation_dir,a.output_dir)
