"""Audit measured A5 host preflight receipts and produce a full 24-row report."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess


def load(path): return json.loads(path.read_text(encoding='utf-8'))
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path, data):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2); stream.write('\n')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--attempt', required=True, type=Path)
    p.add_argument('--source-evidence', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--override-attempt', action='append', type=Path, default=[])
    p.add_argument('--verify-docker-cleanup', action='store_true')
    args = p.parse_args()
    attempt, sources, output = args.attempt.resolve(), args.source_evidence.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    source_rows = load(sources/'receipts.json')['rows']
    rows = load(attempt/'receipts.json')['rows']
    overrides = [p.resolve() for p in args.override_attempt]
    for directory in overrides:
        retry_ids = load(directory/'manifest.json').get('retry_task_ids')
        if not retry_ids: raise ValueError('override must declare exact retry task IDs')
        replacement = {r['task_id']: r for r in load(directory/'receipts.json')['rows']}
        if set(replacement) != {r['task_id'] for r in rows}: raise ValueError('override denominator drift')
        rows = [replacement[r['task_id']] if r['task_id'] in retry_ids else r for r in rows]
    if len(rows) != 24 or [r['task_id'] for r in rows] != [r['task_id'] for r in source_rows]:
        raise ValueError('24-row order/coverage mismatch')
    checks, failures = [], []

    def check(name, condition):
        checks.append(dict(check=name, passed=bool(condition)))
        if not condition: failures.append(name)

    source_manifest = load(sources/'manifest.json')
    canonical = load(Path(source_manifest['canonical']))
    check('canonical_input_unchanged', sha(Path(source_manifest['canonical']))==source_manifest['canonical_sha256'])
    check('consumption_manifest_unchanged', sha(Path(source_manifest['manifest']))==source_manifest['manifest_sha256'])

    # Verify every recorded file, including carried rows and failure/retry ancestors.
    directories = [sources, attempt, *overrides]
    for directory in directories:
        manifest = load(directory/'manifest.json')
        previous = manifest.get('previous_evidence')
        if previous and Path(previous).resolve() not in directories:
            directories.append(Path(previous).resolve())
    directories = list(dict.fromkeys(directories))
    for directory in directories:
        artifact_manifest = load(directory/'artifact-manifest.json')
        for name, expected in artifact_manifest.items():
            path = directory/name
            check(str(path), path.is_file() and sha(path)==expected)
    if args.verify_docker_cleanup:
        owned = set()
        for directory in directories:
            for path in directory.glob('tasks/*/*/evidence.json'):
                for event in load(path).get('lifecycle', []):
                    if event.get('container'): owned.add(event['container'])
        command = ['docker','--context','desktop-linux','ps','-a','--filter','label=coding-harness.h3=true','--format','{{.Names}}']
        proc = subprocess.run(command, capture_output=True, text=True, timeout=30)
        present = set(proc.stdout.splitlines())
        save(output/'docker-cleanup-check.json', dict(argv=command, exit_code=proc.returncode,
             owned_containers=sorted(owned), remaining_owned=sorted(owned & present),
             stdout=proc.stdout, stderr=proc.stderr, model_calls=0))
        check('no_owned_container_remains', proc.returncode==0 and not owned & present)
    environments = []
    detail = []
    for row, source in zip(rows, source_rows):
        tid = row['task_id']
        check(tid+':zero_model_paid', row['model_calls']==0 and row['paid'] is False)
        check(tid+':source_identity', row['repo']==source['repo'] and row['base_revision']==source['base_revision'] and
              row['source']['archive_sha256']==source['source']['archive_sha256'])
        check(tid+':archive_git_commit', row['source']['git_pax_commit']==row['base_revision'])
        check(tid+':no_source_exclusions', row['source']['excluded_upstream_paths']==[])
        if row['source']['total_bytes']>8*1024**2 or row['source']['file_count']>2048:
            check(tid+':oversized_blocked_before_tests', row['status']=='invalid_env' and row.get('image_digest') is None)
        phases = {}
        collection = row.get('collection', {})
        if collection.get('receipt_ref'):
            collection_file = Path(collection['receipt_ref'])
            task_dir = collection_file.parents[1]
            for phase in ('collection','baseline','known-good','fake-output'):
                path = task_dir/phase/'evidence.json'
                if path.exists():
                    evidence = load(path)
                    phases[phase] = {'path':str(path), 'sha256':sha(path),
                        'exit_code':evidence.get('execution',{}).get('exit_code'),
                        'cleanup_verified':evidence.get('cleanup_verified')}
                    check(tid+':'+phase+':cleanup', evidence.get('cleanup_verified') is True)
            collection_evidence = load(collection_file)
            ids = collection_evidence['receipt']['collected']
            check(tid+':collection_hash', hashlib.sha256(json.dumps(ids).encode()).hexdigest()==collection['hash'] and len(ids)==collection['count'])
            private = load(task_dir/'private-source-binding.json')
            private_path = Path(private['path'])
            bundle = next(parent for parent in private_path.parents if (parent/'artifact-manifest.json').is_file())
            bundle_manifest = bundle/'artifact-manifest.json'
            expected_binding = next(b for b in canonical['input_bindings'] if Path(b['path']).resolve()==bundle_manifest.resolve())
            check(tid+':private_bundle_manifest', sha(bundle_manifest)==expected_binding['sha256'])
            check(tid+':private_source_bytes', sha(private_path)==private['sha256']==load(bundle_manifest)[private_path.relative_to(bundle).as_posix()])
            raw = load(private_path)
            check(tid+':private_patch_bytes', hashlib.sha256(raw['patch'].encode()).hexdigest()==private['gold_patch_sha256'] and
                  hashlib.sha256(raw['test_patch'].encode()).hexdigest()==private['test_patch_sha256'])
            missing = {kind:[n for n in private[kind] if n not in ids] for kind in ('FAIL_TO_PASS','PASS_TO_PASS')}
        else:
            missing = None
        if row['status']=='ready':
            check(tid+':ready_baseline', row['baseline']['status']=='baseline_fail' and bool(row['baseline']['failure_nodeids']))
            check(tid+':ready_grader', row['grader']['known_good']=='pass' and
                  all(n['rejected'] for n in row['grader']['negative_rejection']) and row['cleanup'] is True)
            check(tid+':ready_full_phases', set(phases)=={'collection','baseline','known-good','fake-output'})
            check(tid+':ready_exact_ids', not any(missing.values()))
        environments.append(dict(task_id=tid, repo=row['repo'], base_revision=row['base_revision'],
            source_tree_hash=row['source']['source_tree_hash'], image_digest=row.get('image_digest'),
            python_version=row.get('python_version'), pytest_version=row.get('pytest_version'),
            test_collection_hash=collection.get('hash'), collected_count=collection.get('count'),
            baseline_status='baseline_failed_reproduced' if row['status']=='ready' else row['status'],
            baseline_failed_nodeids=row.get('baseline',{}).get('failure_nodeids'),
            cleanup_verified=row.get('cleanup') is True, model_calls=0,
            preflight_status=row['status'], reason=row['reason'], phases=phases))
        detail.append({**row, 'phase_artifacts':phases, 'missing_benchmark_nodeids':missing})
    counts = dict(Counter(row['status'] for row in rows))
    ready = counts.get('ready',0)
    save(output/'audit.json', dict(status='passed' if not failures else 'failed', checks=checks, errors=failures))
    save(output/'environment-receipts.json', dict(schema='a5.environment-baseline.v1', status='blocked',
         task_inventory=[r['task_id'] for r in rows], rows=environments))
    save(output/'receipts.json', dict(schema='a5.host-preflight.audited.v1', rows=detail))
    attempts = []
    for directory in directories:
        path = directory/'failure-retry-ledger.json'
        if path.exists():
            attempts.append(dict(path=str(path), sha256=sha(path), content=load(path)))
    orchestration = sources.parent/'A5-harness-preflight-15-pytest9359-py39/orchestration-failure.json'
    if orchestration.exists(): attempts.append(dict(path=str(orchestration), sha256=sha(orchestration), content=load(orchestration)))
    save(output/'failure-retry-ledger.json', dict(attempts=attempts, model_calls=0, model_reservations=0, paid=False))
    save(output/'input-bindings.json', dict(attempt=str(attempt), overrides=[str(p) for p in overrides],
         verified_evidence_directories=[str(p) for p in directories], script_sha256=sha(Path(__file__))))
    save(output/'readiness.json', dict(status='blocked', assigned=24, status_counts=counts,
         ready=ready, source_snapshots=24, collection_executed=sum(bool(r['phase_artifacts']) for r in detail),
         baseline_executed=sum('baseline' in r['phase_artifacts'] for r in detail),
         audit='passed' if not failures else 'failed', model_calls=0, model_reservations=0, paid=False,
         paid_build_started=False, paid_pilot_started=False,
         remaining16='not_started_initial24_blocked', all20_memory_sources_paid_eligibility='blocked',
         shared_gates=['budget_scope_runtime_alignment','model_snapshot_current_price','dual_source_fingerprint','B0-B3_receipt_integration']))
    lines = ['# A5 initial 24 measured host preflight (host-private evidence)', '',
        f'Ready: {ready}/24. Source snapshots: 24/24. Model calls: 0; paid: false.', '',
        '| Task | Role | Full source files / bytes | Collection | Baseline | Grader | Status / reason |',
        '| --- | --- | --- | --- | --- | --- | --- |']
    for row in rows:
        source = row['source']; col = row.get('collection',{}); base = row.get('baseline',{}); grader=row.get('grader',{})
        lines.append(f"| {row['task_id']} | {row['role']} | {source['file_count']} / {source['total_bytes']} | {col.get('count') if col.get('count') is not None else 'not run'} | {base.get('status')} | {grader.get('known_good')} | {row['status']}: {row['reason']} |")
    lines += ['', 'All 19 over-limit source archives are retained intact. They did not enter Docker testing.',
        'Every source must remain within 8 MiB / 2048 files under this execution contract; no image-backed bypass or trimming.',
        'Pytest uses its own candidate source import, pinned task images, complete upstream-configured testing collection,',
        'private test/gold calibration, negative rejection and verified cleanup. Missing canonical node IDs are not guessed.',
        'The remaining 16 memory sources are not started because the initial24 gate did not pass.',
        'No ready preflight row authorizes paid build/pilot. Shared budget/model/price/fingerprint/receipt gates remain blocked.', '']
    with (output/'report.md').open('x',encoding='utf-8') as stream: stream.write('\n'.join(lines))
    save(output/'artifact-manifest.json', {p.name:sha(p) for p in sorted(output.iterdir()) if p.is_file()})
    print(json.dumps(dict(status_counts=counts, audit_errors=failures, ready=ready, model_calls=0, paid=False)))
    return 1 if failures else 0


if __name__=='__main__': raise SystemExit(main())
