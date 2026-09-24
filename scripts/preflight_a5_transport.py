"""Real zero-model image/live-base/delta transport smoke for all initial 24."""
import argparse
import asyncio
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.preflight_a5_pytest import command, load, save, sha
from scripts.prepare_a5_typed_tree import CANONICAL, CANONICAL_SHA, PROJECTION, PROJECTION_SHA, SOURCE
from src.eval.a5_image_tree import archive_manifest, canonical, LIMIT, validate_delta
from src.execution.a5_image_backend import A5ImageBackend

BASE = 'python@sha256:6e4a4eb8ce1238cb552dd44cc37f9187e448e9bfcf24262c5badfd69fee1bef0'


async def smoke(image, manifest, path, out):
    """Three independent isolated containers: export, reconstruct, reject."""
    results = []
    delta = None
    for case in ('export', 'roundtrip', 'unassigned_edit'):
        backend = A5ImageBackend(manifest=manifest, editable_paths=[path], image=image,
            memory_bytes=1024**3, workspace_bytes=256*1024**2, tmpfs_bytes=64*1024**2)
        result = {'case': case, 'passed': False}
        try:
            await backend.start()
            result['base_verified'] = backend.base_verified
            result['isolation'] = backend.last_inspect
            result['capabilities'] = backend.capabilities
            if case == 'export':
                await backend._ok('exec', backend.name, '/usr/local/bin/python', '-I', '-S', '-c',
                    'from pathlib import Path; p=Path("/workspace")/' + repr(path) + '; p.write_bytes(p.read_bytes()+b"\\n# a5 transport smoke\\n")')
                delta = await backend.export_delta()
                validate_delta(manifest, delta, [path])
                result.update(passed=True, delta_bytes=len(canonical(delta)), delta=delta)
            elif case == 'roundtrip':
                if delta is None:
                    raise ValueError('no prior candidate delta')
                result['candidate_tree_hash'] = await backend.apply_candidate(delta)
                result['passed'] = await backend.export_delta() == delta
            else:
                protected = next(n for n, m in manifest['entries'].items() if m['kind'] == 'file' and n != path)
                await backend._ok('exec', backend.name, '/usr/local/bin/python', '-I', '-S', '-c',
                    'from pathlib import Path; p=Path("/workspace")/' + repr(protected) + '; p.write_bytes(p.read_bytes()+b"tampered")')
                try:
                    await backend.export_delta()
                except Exception as exc:
                    result['rejection'] = str(exc)
                    result['passed'] = 'unassigned' in str(exc)
        except Exception as exc:
            result['error'] = type(exc).__name__ + ': ' + str(exc)
        finally:
            await backend.close()
            result.update(cleanup_verified=backend.cleanup_ok, lifecycle=backend.lifecycle)
            result['passed'] = result['passed'] and backend.cleanup_ok is True
            save(out / (case + '.json'), result)
        results.append(result)
    return all(r['passed'] for r in results)


async def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--memory-sources', action='store_true',
                    help='run the remaining16 memory-source transport contract')
    ap.add_argument('--source-root', type=Path, default=SOURCE)
    args = ap.parse_args()
    if sha(CANONICAL.read_bytes()) != CANONICAL_SHA or sha(PROJECTION.read_bytes()) != PROJECTION_SHA:
        raise ValueError('canonical input drift')
    c = load(CANONICAL)
    projection = load(PROJECTION)
    if args.memory_sources:
        remaining = set(projection['remaining_memory_source_ids'])
        tasks = [{**t, 'role': 'memory_source'} for t in c['memory_build_source_pool']
                 if t['canonical_id'] in remaining]
        if len(tasks) != 16 or [t['canonical_id'] for t in tasks] != projection['remaining_memory_source_ids']:
            raise ValueError('remaining16 transport task mismatch')
    else:
        tasks = c['target_tasks'] + c['preflight_history_candidates']
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    contract = ROOT / 'docs/upgrade/A5-IMAGE-BACKED-CONTINUATION-CONTRACT.md'
    save(out / 'inputs.json', {'canonical_sha256': CANONICAL_SHA, 'projection_sha256': PROJECTION_SHA,
        'contract_sha256': sha(contract.read_bytes()), 'base_image': BASE, 'model_calls': 0, 'paid': False,
        'source_code': {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in
            (Path(__file__), ROOT/'src/eval/a5_image_tree.py', ROOT/'src/execution/a5_image_backend.py')},
        'assigned': [t['canonical_id'] for t in tasks]})
    rows = []
    for task in tasks:
        tid = task['canonical_id']; directory = out / 'tasks' / tid; directory.mkdir(parents=True)
        row = {'task_id': tid, 'repo': task['expected_repo'], 'base_revision': task['expected_base_commit'],
               'status': 'invalid_env', 'model_calls': 0, 'paid': False}
        try:
            archive = args.source_root.resolve() / 'tasks' / tid / 'source.tar.gz'
            old = load(archive.parent / 'source-receipt.json')['source']
            manifest = archive_manifest(archive, row['repo'], row['base_revision'])
            if (manifest['archive_sha256'] != old['archive_sha256'] or manifest['file_count'] != old['file_count'] or
                    manifest['total_bytes'] != old['total_bytes']):
                raise ValueError('retained archive drift')
            context = directory / 'build'; context.mkdir()
            shutil.copyfile(archive, context / 'source.tar.gz')
            save(context / 'a5-tree.json', manifest)
            shutil.copyfile(ROOT / 'src/eval/a5_image_tree.py', context / 'a5-tree.py')
            dockerfile = ('FROM ' + BASE + '\nCOPY source.tar.gz /opt/source.tar.gz\n'
                'COPY a5-tree.json /opt/a5-tree.json\nCOPY a5-tree.py /opt/a5-tree.py\n'
                'RUN python -I -S /opt/a5-tree.py extract\nWORKDIR /workspace\n')
            with (context / 'Dockerfile').open('x', encoding='utf-8') as f:
                f.write(dockerfile)
            tag = 'coding-harness-a5-transport:' + tid.replace('__', '-')
            print(tid + ': complete image build', flush=True)
            await asyncio.to_thread(command, ['docker', '--context', 'desktop-linux', 'build', '--progress=plain', '-t', tag, str(context)], directory / 'build-log')
            inspect = json.loads(await asyncio.to_thread(command, ['docker', '--context', 'desktop-linux', 'image', 'inspect', tag], directory / 'image-inspect'))[0]
            image = tag.split(':')[0] + '@' + inspect['Id']
            row.update(image_digest=image, source_tree_hash=manifest['source_tree_hash'],
                source_tree_schema=manifest['schema'], archive_sha256=manifest['archive_sha256'],
                archive_bytes=manifest['archive_bytes'], file_count=manifest['file_count'],
                total_bytes=manifest['total_bytes'], directory_count=manifest['directory_count'],
                transport_mode='image_backed_base_plus_delta')
            path = next(n for n, m in manifest['entries'].items() if m['kind'] == 'file' and n.endswith('.py') and
                        m['size'] < LIMIT // 2)
            print(tid + ': live full-base/delta roundtrip', flush=True)
            passed = await smoke(image, manifest, path, directory)
            row.update(status='transport_ready' if passed else 'invalid_env',
                reason='transport_only_not_environment_or_grader_ready' if passed else 'live_transport_failed')
        except Exception as exc:
            row['reason'] = type(exc).__name__ + ': ' + str(exc)
        save(directory / 'receipt.json', row); rows.append(row)
        print(tid + ': ' + row['status'], flush=True)
    save(out / 'receipts.json', {'rows': rows})
    save(out / 'readiness.json', {'status': 'blocked', 'assigned': len(tasks), 'transport_ready': sum(r['status']=='transport_ready' for r in rows),
        'model_calls': 0, 'paid': False, 'memory_build_eligible': False,
        'remaining_gates': ['initial24_repo_environment_baseline_grader', 'remaining16', 'model_price', 'ledger', 'dual_fingerprint', 'receipt_integration']})
    save(out / 'artifact-manifest.json', {p.relative_to(out).as_posix(): sha(p.read_bytes()) for p in sorted(out.rglob('*')) if p.is_file()})


if __name__ == '__main__':
    asyncio.run(main())
