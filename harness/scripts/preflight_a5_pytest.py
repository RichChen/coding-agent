"""Real zero-model Docker preflight for the five size-eligible A5 pytest tasks.

The 19 source failures remain in every aggregate denominator. This is a host
calibration script, not a paid-build executor or replacement experiment runner.
"""
import argparse
import asyncio
import base64
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tarfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.execution.docker import DockerExecutionBackend, validate_files, image_is_pinned
from src.execution.base import ExecutionRequest, OutputQuotas
from src.eval.repo_grader import classify_receipt, PROTECTED_NAMES
from src.eval.grader import tree_hash

AGENT = ROOT.parent / 'coding-agent'
BASE_IMAGE = 'python@sha256:603879aeff06df23f0d392a19f7ce02aa85e14e6b4d25fd9647b116e0cb93467'
REQUIREMENTS_PATH = ROOT/'configs/a5/pytest-preflight-requirements.lock'
PINNED_PLUGIN_AUTOLOAD = False
RUNNER = (ROOT / 'scripts/a5_pytest_observer.py').read_text(encoding='utf-8')


def sha(data): return hashlib.sha256(data).hexdigest()
def load(path): return json.loads(path.read_text(encoding='utf-8'))
def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2); stream.write('\n')


def command(argv, output, cwd=None, timeout=600):
    started = time.monotonic()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.with_suffix('.stdout').open('xb') as stdout, output.with_suffix('.stderr').open('xb') as stderr:
        try:
            result = subprocess.run(argv, cwd=cwd, stdout=stdout, stderr=stderr, timeout=timeout)
            code = result.returncode
        except subprocess.TimeoutExpired:
            code = -1
    save(output.with_suffix('.json'), dict(argv=argv, cwd=str(cwd) if cwd else None, exit_code=code,
                                        elapsed_seconds=time.monotonic() - started))
    if code:
        raise RuntimeError('command failed: ' + str(output) + ' exit=' + str(code))
    return output.with_suffix('.stdout').read_bytes()


def read_archive(path):
    files = {}
    with tarfile.open(path, 'r:gz') as archive:
        for member in archive.getmembers():
            if member.isdir(): continue
            if not member.isfile(): raise ValueError('nonregular source unsupported')
            name = member.name.partition('/')[2]
            files[name] = archive.extractfile(member).read()
    return validate_files(files)


def materialize(files, directory):
    for name, data in validate_files(files).items():
        path = directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream: stream.write(data)


def patched(files, patch, directory):
    # Git processes patch data only. No checkout hooks or repository code run on host.
    materialize(files, directory)
    command(['git', 'init', '--quiet'], directory.parent / (directory.name + '-git-init'), cwd=directory)
    patch_path = directory.parent / (directory.name + '.patch')
    with patch_path.open('xb') as stream: stream.write(patch.encode('utf-8'))
    command(['git', 'apply', '--check', str(patch_path)], directory.parent / (directory.name + '-patch-check'), cwd=directory)
    command(['git', 'apply', str(patch_path)], directory.parent / (directory.name + '-patch-apply'), cwd=directory)
    result = {p.relative_to(directory).as_posix(): p.read_bytes() for p in directory.rglob('*')
              if p.is_file() and '.git' not in p.relative_to(directory).parts}
    return validate_files(result)


async def execute(files, image, directory, *, collect_only=False, timeout=600):
    directory.mkdir(parents=True, exist_ok=False)
    backend = DockerExecutionBackend(image=image, context='desktop-linux', memory_bytes=2*1024**3,
                                     workspace_bytes=256*1024**2, tmpfs_bytes=512*1024**2, network='none')
    evidence = dict(status='invalid_env', receipt=None, cleanup_verified=False, model_calls=0)
    try:
        await backend.start(files)
        evidence['isolation'] = backend.last_inspect
        generated = json.loads(await backend._ok('exec', backend.name, '/usr/local/bin/python', '-I', '-S', '-c',
            "from pathlib import Path; print(Path('/opt/a5-generated.json').read_text())", limit=1024*1024))
        additions = {n: base64.b64decode(b) for n, b in generated.items()}
        if set(additions) & set(files): raise ValueError('generated environment collides with source')
        combined = validate_files({**files, **additions})
        import_code = "import base64,json,pathlib,sys\nfor n,b in json.load(sys.stdin).items():\n p=pathlib.Path('/workspace')/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(base64.b64decode(b))"
        await backend._ok('exec', '-i', backend.name, '/usr/local/bin/python', '-I', '-S', '-c', import_code,
                          data=json.dumps(generated).encode())
        evidence['generated_environment_files'] = {n: sha(b) for n,b in additions.items()}
        probe = "import json,sys,importlib_metadata as m; print(json.dumps({'python':sys.version,'packages':{d.metadata['Name']:d.version for d in m.distributions()}}))"
        evidence['environment'] = json.loads(await backend._ok('exec', backend.name, '/usr/local/bin/python', '-I', '-B', '-c', probe))
        evidence['pip_freeze'] = (await backend._ok('exec', backend.name, 'cat', '/opt/grader-environment.txt')).decode()
        request = ExecutionRequest(argv=['/usr/local/bin/python', '-I', '-B', '-c', RUNNER],
            stdin_bytes=json.dumps(dict(collect_only=collect_only, pinned_plugin_autoload=PINNED_PLUGIN_AUTOLOAD)).encode(),
            env={'PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1', 'PYTHONPATH':'/workspace/src', 'PYTHONDONTWRITEBYTECODE':'1'},
            deadline_mono=time.monotonic()+timeout, artifact_dir=directory,
            quotas=OutputQuotas(memory_per_stream_bytes=2*1024**2, artifact_per_tool_bytes=16*1024**2))
        result = await backend.execute(request)
        evidence['execution'] = dict(status=result.status.value, exit_code=result.exit_code,
            error_kind=result.error_kind, truncated=result.truncated, stdout=result.stdout.text_preview,
            stderr=result.stderr.text_preview, duration_ms=result.duration_ms)
        if backend.active:
            try:
                evidence['receipt'] = json.loads(await backend._ok('exec', backend.name, '/usr/local/bin/python', '-I', '-S', '-c',
                    "from pathlib import Path;import sys;p=Path('/tmp/a5-receipt.json');assert p.is_file() and not p.is_symlink() and p.stat().st_size<=16777216;sys.stdout.buffer.write(p.read_bytes())", limit=16*1024**2))
            except Exception as exc: evidence['receipt_error'] = type(exc).__name__ + ': ' + str(exc)
            checker = "import hashlib,json,pathlib,sys\nr={}\nfor n in json.load(sys.stdin):\n p=pathlib.Path('/workspace')/n;r[n]=hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() and not p.is_symlink() else None\nprint(json.dumps(r))"
            actual = json.loads(await backend._ok('exec', '-i', backend.name, '/usr/local/bin/python', '-I', '-S', '-c', checker,
                                                 data=json.dumps(list(combined)).encode(), limit=1024*1024))
            evidence['changed_frozen_inputs'] = [n for n,b in combined.items() if actual.get(n) != sha(b)]
            evidence['integrity_verified'] = True
            evidence['status'] = 'executed'
    except Exception as exc:
        evidence['reason'] = type(exc).__name__ + ': ' + str(exc)
    finally:
        await backend.close()
        evidence.update(cleanup_verified=backend.cleanup_ok, lifecycle=backend.lifecycle,
                        capabilities=backend.capabilities)
    save(directory / 'evidence.json', evidence)
    return evidence


def valid_execution(evidence):
    e = evidence.get('execution', {})
    return (evidence.get('status') == 'executed' and evidence.get('integrity_verified') is True and
            evidence.get('changed_frozen_inputs') == [] and evidence.get('cleanup_verified') is True and
            e.get('status') in ('succeeded', 'failed') and not e.get('truncated') and
            e.get('exit_code') == (evidence.get('receipt') or {}).get('exit_code'))


async def task_preflight(row, source_root, output, dependency_image, previous=None):
    tid = row['task_id']; directory = output / 'tasks' / tid
    directory.mkdir(parents=True, exist_ok=False)
    row = {**row, 'source_attempt_ref': str(source_root / 'tasks' / tid / 'source-receipt.json'),
           'status': 'invalid_env', 'reason': 'environment_not_complete',
           'attempt': (previous or {}).get('attempt', 1) + 1,
           'environment_attempt': (previous or {}).get('environment_attempt', 0) + 1,
           'retries': (previous or {}).get('retries', -1) + 1, 'model_calls': 0, 'paid': False}
    try:
        archive = source_root / 'tasks' / tid / 'source.tar.gz'
        if sha(archive.read_bytes()) != row['source']['archive_sha256']:
            raise ValueError('source archive changed since source preflight')
        files = read_archive(archive)
        if row['role'] == 'target':
            private = AGENT / 'reports/upgrade/a5-pilot20-preparation-20260921-v4/private/tasks' / row['agent_task_id']
            source_row_path = private / 'source-row.json'
        else:
            c = load(AGENT / 'configs/a5/canonical-handoff.json')
            record = next(s for s in c['memory_build_source_pool'] if s['canonical_id'] == tid)
            source_row_path = AGENT / record['provenance']['source_row']['path']
        source = load(source_row_path)
        if source['repo'] != row['repo'] or source['base_commit'] != row['base_revision']:
            raise ValueError('private source identity mismatch')
        if PINNED_PLUGIN_AUTOLOAD and (tid != 'pytest-dev__pytest-5103' or source['version'] != '4.5'):
            raise ValueError('pinned autoload profile is only calibrated for historical pytest 4.5')
        f2p = json.loads(source['FAIL_TO_PASS']) if isinstance(source['FAIL_TO_PASS'],str) else source['FAIL_TO_PASS']
        p2p = json.loads(source['PASS_TO_PASS']) if isinstance(source['PASS_TO_PASS'],str) else source['PASS_TO_PASS']
        save(directory / 'private-source-binding.json', dict(path=str(source_row_path), sha256=sha(source_row_path.read_bytes()),
            test_patch_sha256=sha(source['test_patch'].encode()), gold_patch_sha256=sha(source['patch'].encode()),
            FAIL_TO_PASS=f2p, PASS_TO_PASS=p2p, version=source['version']))
        context = directory / 'build'
        materialize(files, context / 'base')
        with (context / 'requirements.lock').open('xb') as stream:
            stream.write(REQUIREMENTS_PATH.read_bytes())
        # Only public source enters image build. Private patches go to isolated
        # ephemeral grader workspaces after the image has been frozen.
        dockerfile = f'''FROM {BASE_IMAGE}
COPY requirements.lock /opt/requirements.lock
RUN python -m pip install --no-cache-dir --no-deps -r /opt/requirements.lock
RUN python -m pip check
COPY base /workspace
WORKDIR /workspace
RUN SETUPTOOLS_SCM_PRETEND_VERSION={source['version']}.0 python -m pip install --no-deps --no-build-isolation -e /workspace
RUN python -c "import base64,json,pathlib; r=pathlib.Path('/workspace'); paths=list((r/'src/pytest.egg-info').rglob('*'))+[r/'src/_pytest/_version.py']; pathlib.Path('/opt/a5-generated.json').write_text(json.dumps({{p.relative_to(r).as_posix():base64.b64encode(p.read_bytes()).decode() for p in paths if p.is_file()}}))"
RUN python -m pip freeze --all > /opt/grader-environment.txt
ENV PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
'''
        with (context / 'Dockerfile').open('x', encoding='utf-8') as stream: stream.write(dockerfile)
        tag = 'coding-harness-a5-pytest:' + tid.rsplit('-',1)[1] + '-' + output.name.split('-')[3]
        print(tid + ': building repo-specific image', flush=True)
        await asyncio.to_thread(command, ['docker','--context','desktop-linux','build','--progress=plain','-t',tag,str(context)], directory/'image-build')
        inspect = json.loads(await asyncio.to_thread(command, ['docker','--context','desktop-linux','image','inspect',tag], directory/'image-inspect'))[0]
        image = inspect['RepoDigests'][0] if inspect.get('RepoDigests') else tag.split(':')[0]+'@'+inspect['Id']
        row['image_digest'] = image
        save(directory/'image-binding.json', dict(image=image, image_id=inspect['Id'], base_image=BASE_IMAGE,
              dependency_image=dependency_image, dockerfile_sha256=sha(dockerfile.encode()), public_source_hash=tree_hash(files)))
        baseline = await asyncio.to_thread(patched, files, source['test_patch'], directory/'private-baseline')
        good = await asyncio.to_thread(patched, baseline, source['patch'], directory/'private-known-good')
        changes = sorted(n for n in baseline.keys() | good.keys() if baseline.get(n) != good.get(n))
        if not changes or any(n.startswith('testing/') or PurePosixPath(n).name in PROTECTED_NAMES for n in changes):
            row.update(status='grader_unavailable', reason='gold_changes_protected_or_no_source_paths'); return row
        save(directory/'snapshot-binding.json', dict(base=tree_hash(files), baseline=tree_hash(baseline),
             known_good=tree_hash(good), gold_editable_paths=changes))
        print(tid + ': full collection', flush=True)
        collection = await execute(baseline, image, directory/'collection', collect_only=True, timeout=180)
        receipt = collection.get('receipt') or {}; ids = receipt.get('collected', [])
        row['environment'] = collection.get('environment')
        row['python_version'] = (row['environment'] or {}).get('python')
        row['pytest_version'] = receipt.get('pytest_version')
        row['dependencies'] = collection.get('pip_freeze')
        row['collection'] = dict(status='invalid_env', count=len(ids), hash=sha(json.dumps(ids).encode()),
                                 nodeids=ids, errors=receipt.get('collection_errors'), receipt_ref=str(directory/'collection/evidence.json'))
        row['cleanup'] = collection.get('cleanup_verified')
        if not valid_execution(collection) or receipt.get('exit_code') != 0 or not receipt.get('complete') or not ids or len(ids) != len(set(ids)) or receipt.get('collection_errors'):
            row['reason'] = 'full_collection_failed'; return row
        row['collection']['status'] = 'ready'
        if not set(f2p + p2p) <= set(ids):
            row.update(status='grader_unavailable', reason='benchmark_nodeids_not_in_full_collection'); return row
        print(tid + f': baseline ({len(ids)} collected)', flush=True)
        base_run = await execute(baseline, image, directory/'baseline')
        outcomes, error = classify_receipt(base_run.get('receipt'), ids)
        row['baseline'] = dict(status='invalid_env', failure_nodeids=[n for n,v in outcomes.items() if v=='failed'],
                               receipt_ref=str(directory/'baseline/evidence.json'), classifier_error=error)
        row['cleanup'] = row['cleanup'] and base_run.get('cleanup_verified')
        if not valid_execution(base_run) or error:
            row['reason'] = 'baseline_execution_invalid'; return row
        reproduced = all(outcomes.get(n)=='failed' for n in f2p)
        row['baseline'].update(status='baseline_fail' if reproduced else 'baseline_pass', outcomes=outcomes,
            skipped=[n for n,v in outcomes.items() if v=='skipped'], xfailed=[n for n,v in outcomes.items() if v=='xfailed'])
        print(tid + ': known-good calibration', flush=True)
        positive = await execute(good, image, directory/'known-good')
        good_outcomes, good_error = classify_receipt(positive.get('receipt'), ids)
        allowed = {n:v for n,v in outcomes.items() if v in ('skipped','xfailed') and n not in f2p+p2p}
        good_ok = valid_execution(positive) and not good_error and all(v=='passed' or allowed.get(n)==v for n,v in good_outcomes.items())
        good_ok = good_ok and all(good_outcomes.get(n)=='passed' for n in f2p+p2p)
        negatives = [dict(case='tampered_test',status='rejected_before_execution',path='testing/conftest.py'),
                     dict(case='tampered_config',status='rejected_before_execution',path='tox.ini')]
        for negative in negatives:
            candidate = {**good, negative['path']: b'print("ALL TESTS PASSED")\n'}
            delta = {n for n in baseline.keys() | candidate.keys() if baseline.get(n) != candidate.get(n)}
            negative['rejected'] = bool(delta - set(changes))
        fake = {**good, changes[0]: b'import os\nprint("ALL TESTS PASSED",flush=True)\nos._exit(0)\n'}
        print(tid + ': negative fake-output calibration', flush=True)
        fake_result = await execute(fake, image, directory/'fake-output', timeout=180)
        _, fake_error = classify_receipt(fake_result.get('receipt'), ids)
        negatives.append(dict(case='fake_stdout', rejected=not valid_execution(fake_result) or bool(fake_error), classifier_error=fake_error))
        save(directory/'negative-checks.json', negatives)
        row['cleanup'] = row['cleanup'] and positive.get('cleanup_verified') and fake_result.get('cleanup_verified')
        row['grader'] = dict(status='ready' if good_ok and all(n['rejected'] for n in negatives) else 'invalid_env',
            known_good='pass' if good_ok else 'fail', known_good_failed_nodeids=[n for n,v in good_outcomes.items() if v=='failed'],
            known_good_classifier_error=good_error, negative_rejection=negatives)
        row['status'] = 'ready' if reproduced and good_ok and all(n['rejected'] for n in negatives) and row['cleanup'] else ('baseline_pass' if not reproduced else 'invalid_env')
        row['reason'] = 'all_preflight_checks_passed' if row['status']=='ready' else 'baseline_or_known_good_or_negative_gate_failed'
    except Exception as exc:
        row['reason'] = 'environment_or_grader_preparation_failed'
        row['error'] = type(exc).__name__ + ': ' + str(exc)
    finally:
        save(directory/'receipt.json', row)
        print(tid + ': ' + row['status'] + ' / ' + row['reason'], flush=True)
    return row


async def main():
    global BASE_IMAGE, REQUIREMENTS_PATH, PINNED_PLUGIN_AUTOLOAD
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-evidence', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--previous-evidence', type=Path)
    parser.add_argument('--only-task', action='append')
    parser.add_argument('--base-image', default=BASE_IMAGE)
    parser.add_argument('--requirements', type=Path, default=REQUIREMENTS_PATH)
    parser.add_argument('--pinned-plugin-autoload', action='store_true')
    args = parser.parse_args()
    if not image_is_pinned(args.base_image): raise ValueError('base image digest required')
    BASE_IMAGE = args.base_image
    REQUIREMENTS_PATH = args.requirements.resolve()
    PINNED_PLUGIN_AUTOLOAD = args.pinned_plugin_autoload
    source_root, output = args.source_evidence.resolve(), args.output.resolve()
    for filename, expected in [('canonical-handoff.json','d18d9fa78da00230c30d62c61abce168b91812871d3435e14702aad7a761774c'),
                               ('pilot20-harness-consumption-manifest.json','33ab6922caf6909888d672a8d97df49f305ed4cdabb8c402dfca4bca88cb0180')]:
        if sha((AGENT/'configs/a5'/filename).read_bytes()) != expected:
            raise ValueError('canonical input drift')
    rows = load(source_root/'receipts.json')['rows']
    canonical = load(AGENT/'configs/a5/canonical-handoff.json')
    if len(rows)!=24 or [r['task_id'] for r in rows] != [r['canonical_id'] for r in canonical['target_tasks']+canonical['preflight_history_candidates']]:
        raise ValueError('24 exact canonical rows required')
    previous = {r['task_id']:r for r in load(args.previous_evidence/'receipts.json')['rows']} if args.previous_evidence else {}
    if args.only_task and (set(args.only_task)-{r['task_id'] for r in rows} or len(previous)!=24):
        raise ValueError('targeted retry requires exact IDs and a full prior 24-row receipt')
    output.mkdir(parents=True, exist_ok=False)
    for src, name in [(Path(__file__),'preflight-script.py'), (ROOT/'scripts/a5_pytest_observer.py','observer.py'),
                      (REQUIREMENTS_PATH,'requirements.lock')]:
        with (output/name).open('xb') as stream: stream.write(src.read_bytes())
    save(output/'manifest.json', dict(source_evidence=str(source_root), source_receipts_sha256=sha((source_root/'receipts.json').read_bytes()),
        base_image=BASE_IMAGE, assigned=[r['task_id'] for r in rows], model_calls=0, paid=False,
        runner_sha256=sha(RUNNER.encode()), script_sha256=sha(Path(__file__).read_bytes()),
        previous_evidence=str(args.previous_evidence.resolve()) if args.previous_evidence else None,
        retry_task_ids=args.only_task, requirements_path=str(REQUIREMENTS_PATH), requirements_sha256=sha(REQUIREMENTS_PATH.read_bytes()),
        pinned_plugin_autoload=PINNED_PLUGIN_AUTOLOAD))
    deps = output/'dependency-build'; deps.mkdir()
    requirements = REQUIREMENTS_PATH.read_bytes()
    with (deps/'requirements.lock').open('xb') as stream: stream.write(requirements)
    with (deps/'Dockerfile').open('x',encoding='utf-8') as stream:
        stream.write(f'FROM {BASE_IMAGE}\nCOPY requirements.lock /opt/requirements.lock\nRUN python -m pip install --no-cache-dir --no-deps -r /opt/requirements.lock\nRUN python -m pip check\n')
    tag = 'coding-harness-a5-pytest-deps:preflight-' + output.name.split('-')[3]
    dependency_failure = None
    try:
        print('building pinned pytest-specific dependencies',flush=True)
        await asyncio.to_thread(command, ['docker','--context','desktop-linux','build','--progress=plain','-t',tag,str(deps)], output/'dependencies-build')
        inspect = json.loads(await asyncio.to_thread(command, ['docker','--context','desktop-linux','image','inspect',tag], output/'dependencies-inspect'))[0]
        image = inspect['RepoDigests'][0] if inspect.get('RepoDigests') else tag.split(':')[0]+'@'+inspect['Id']
    except Exception as exc:
        dependency_failure = str(exc)
    result = []
    semaphore = asyncio.Semaphore(2)
    async def run(row):
        if args.only_task and row['task_id'] not in args.only_task:
            return {**previous[row['task_id']], 'carried_previous_attempt': True,
                    'previous_receipt_ref': str(args.previous_evidence.resolve()/'receipts.json')}
        if row['status'] != 'blocked':
            return {**row, 'carried_source_failure': True, 'source_attempt_ref': str(source_root/'tasks'/row['task_id']/'source-receipt.json')}
        if dependency_failure:
            return {**row, 'status':'invalid_env', 'reason':'pytest_dependency_image_build_failed', 'error':dependency_failure}
        async with semaphore:
            return await task_preflight(row, source_root, output, image, previous.get(row['task_id']))
    result = await asyncio.gather(*(run(row) for row in rows))
    save(output/'receipts.json', dict(schema='a5.host-preflight.receipts.v1', rows=result))
    save(output/'failure-retry-ledger.json', dict(entries=[{k:r.get(k) for k in ('task_id','status','reason','attempt','retries','source_attempt_ref')} for r in result],
        model_calls=0, model_reservations=0, paid=False))
    counts = {s:sum(r['status']==s for r in result) for s in sorted({r['status'] for r in result})}
    save(output/'readiness.json', dict(status='ready' if counts.get('ready')==24 else 'blocked', assigned=24,
        status_counts=counts, environment_ready=sum(r['status']=='ready' for r in result),
        baseline_runs=sum(r.get('baseline',{}).get('receipt_ref') is not None for r in result), model_calls=0,
        paid=False, paid_build_started=False, paid_pilot_started=False, model_reservations=0,
        remaining16_gate='not_started_initial24_not_passed', budget_scope_gate='blocked_pending_separate_runtime_alignment'))
    save(output/'artifact-manifest.json', {p.relative_to(output).as_posix():sha(p.read_bytes()) for p in sorted(output.rglob('*')) if p.is_file()})
    print(json.dumps(counts),flush=True)


if __name__=='__main__': asyncio.run(main())
