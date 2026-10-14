"""Retry bounded A5 runtime checks using retained, hash-bound full images/archives."""
import argparse
import ast
import asyncio
import json
import re
import shutil
import sys
import tarfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.preflight_a5_repo_baseline import (ROOT, CANONICAL, CANONICAL_SHA, load,
    save, sha, source_row_path, run_pytest, outcomes, image_build, dockerfile, patch_paths, SOURCE_ROOT)


def resolve_ids(family, expected, collected, test_paths, staging):
    """Exact runtime IDs or exact unittest shortDescription; never fuzzy IDs."""
    mapping = {}
    for label in expected:
        if family == 'django':
            match = re.fullmatch(r'(test\S+) \(([^()]+)\)', label)
            if match:
                candidates = [match[2] + '.' + match[1]]
            else:
                candidates = []
                for path in test_paths:
                    if not path.endswith('.py'):
                        continue
                    syntax = ast.parse((staging / 'baseline' / path).read_text(encoding='utf-8'))
                    module = path.removeprefix('tests/').removesuffix('.py').replace('/', '.')
                    for cls in syntax.body:
                        if not isinstance(cls, ast.ClassDef):
                            continue
                        for method in cls.body:
                            if not isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                continue
                            doc = ast.get_docstring(method)
                            if doc and doc.splitlines()[0] == label:
                                candidates.append(module + '.' + cls.name + '.' + method.name)
        elif family == 'sympy':
            candidates = [p + '::' + label for p in test_paths if '/tests/' in p and p.endswith('.py')]
        else:
            candidates = [label]
        candidates = [n for n in candidates if n in collected]
        if len(candidates) != 1:
            raise ValueError(f'expected exactly one collected identity for {label!r}: {candidates}')
        mapping[label] = candidates[0]
    if len(set(mapping.values())) != len(expected):
        raise ValueError('test identity mapping is not one-to-one')
    return mapping


def verify_python_only_delta(staging):
    """Compiled extensions can be reused only with identical native build inputs."""
    def inventory(path):
        with tarfile.open(path) as archive:
            return {m.name: (m.type, m.mode, m.linkname,
                    sha(archive.extractfile(m).read()) if m.isfile() else None) for m in archive}
    base = inventory(staging / 'baseline.tar.gz')
    gold = inventory(staging / 'known-good.tar.gz')
    changed = [n for n in base.keys() | gold.keys() if base.get(n) != gold.get(n)]
    if not changed or any(not n.endswith('.py') or n not in gold or n == 'setup.py' for n in changed):
        raise ValueError('cannot reuse native artifacts for this gold delta')
    return sorted(changed)


async def check(task, prior_root, output, rebuild, test_files=False):
    tid = task['canonical_id']
    prior_file = prior_root / 'tasks' / tid / 'receipt.json'
    row = load(prior_file)
    out = output / 'tasks' / tid
    out.mkdir(parents=True)
    row = {**row, 'attempt': output.name, 'status': 'invalid_env',
           'previous_receipt_ref': str(prior_file), 'previous_receipt_sha256': sha(prior_file.read_bytes())}
    try:
        private_file = source_row_path(task)
        private = load(private_file)
        staging = prior_file.parent / 'staging'
        if 'private_source_binding' not in row:
            for label, key in [('test', 'test_patch'), ('gold', 'patch')]:
                if sha(private[key].encode()) != load(staging / (label+'-binding.json'))['patch_sha256']:
                    raise ValueError('staging patch binding mismatch')
            row['private_source_binding'] = dict(path=str(private_file), sha256=sha(private_file.read_bytes()),
                test_patch_sha256=sha(private['test_patch'].encode()), gold_patch_sha256=sha(private['patch'].encode()),
                test_patch_paths=patch_paths(private['test_patch']), gold_patch_paths=patch_paths(private['patch']))
            row['source'] = load(SOURCE_ROOT / 'tasks' / tid / 'source-receipt.json')['source']
        if sha(private_file.read_bytes()) != row['private_source_binding']['sha256']:
            raise ValueError('private source drift')
        family = task['expected_repo'].split('/')[0]
        if rebuild:
            built_baseline_tag = None
            for kind in ('baseline', 'known-good'):
                context = out / (kind + '-image')
                context.mkdir()
                archive = staging / (kind + '.tar.gz')
                shutil.copy2(archive, context / archive.name)
                base_tag = 'coding-harness-a5-transport:' + tid.replace('__', '-')
                tag = 'coding-harness-a5-recheck:' + tid.replace('__', '-') + '-' + kind
                if kind == 'known-good' and family == 'scikit-learn':
                    row['native_artifact_reuse'] = dict(changed_source_paths=verify_python_only_delta(staging),
                        baseline_image=row['baseline_image_digest'], non_python_tree_unchanged=True)
                    recipe = (f'FROM {built_baseline_tag}\nCOPY {archive.name} /opt/{archive.name}\n'
                              f'RUN tar -xzpf /opt/{archive.name} -C /opt/repo\n')
                else:
                    recipe = dockerfile(base_tag, family, private['version'], archive.name)
                (context / 'Dockerfile').write_text(recipe, encoding='utf-8')
                digest, info = await asyncio.to_thread(image_build, context, tag, out / (kind + '-image-build.log'))
                row['baseline_image_digest' if kind == 'baseline' else 'known_good_image_digest'] = digest
                row['baseline_image_id' if kind == 'baseline' else 'known_good_image_id'] = info['Id']
                if kind == 'baseline': built_baseline_tag = tag
        django = family == 'django'
        native_sympy = family == 'sympy' and private['version'] == '1.6'
        base_image, good_image = row['baseline_image_digest'], row['known_good_image_digest']
        args = [] if django else ['--collect-only', '-q',
            {'sympy': 'sympy', 'scikit-learn': 'sklearn', 'sphinx-doc': 'tests', 'pytest-dev': 'testing'}[family]]
        collection = await run_pytest(base_image, args, out / 'collection', timeout=1800,
                                     django=django, collect_only=django, sympy_native_helpers=native_sympy)
        col = collection.get('receipt', {}); ids = col.get('collected', [])
        col_ok = (collection.get('execution', {}).get('exit_code') == 0 and col.get('complete')
                  and bool(ids) and len(ids) == len(set(ids)) and not col.get('collection_errors'))
        row['collection'] = dict(status='ready' if col_ok else 'invalid_env', count=len(ids), nodeids=ids,
            hash=sha(json.dumps(ids).encode()), receipt_ref=str(out / 'collection/evidence.json'))
        expected = private['FAIL_TO_PASS']
        if isinstance(expected, str): expected = json.loads(expected)
        mapping = resolve_ids(family, expected, ids, row['private_source_binding']['test_patch_paths'], staging)
        selected = list(mapping.values())
        row['exact_f2p_binding'] = mapping
        execution_ids = sorted({n.split('::')[0] for n in selected}) if test_files and not django else selected
        args = execution_ids if django else ['-q', '--tb=short', *execution_ids]
        row['execution_scope'] = dict(mode='complete_test_files' if test_files else 'selected_f2p', args=args)
        base = await run_pytest(base_image, args, out / 'baseline', django=django, sympy_native_helpers=native_sympy)
        good = await run_pytest(good_image, args, out / 'known-good', django=django, sympy_native_helpers=native_sympy)
        b, g = outcomes(base.get('receipt', {})), outcomes(good.get('receipt', {}))
        base_ok = bool(selected) and all(b.get(n) == 'failed' for n in selected)
        good_ok = all(g.get(n) == 'passed' for n in selected) and good.get('execution', {}).get('exit_code') == 0
        clean = all(x.get('cleanup_verified') is True for x in (collection, base, good))
        row.update(baseline=dict(status='baseline_fail' if base_ok else 'baseline_mismatch', outcomes=b,
                    failure_nodeids=[n for n in selected if b.get(n) == 'failed'],
                    unexpected_pass=[n for n in selected if b.get(n) == 'passed'],
                    receipt_ref=str(out / 'baseline/evidence.json')),
            grader=dict(status='pending_full_repo_grader', known_good='pass' if good_ok else 'fail',
                        known_good_outcomes=g, receipt_ref=str(out / 'known-good/evidence.json')),
            cleanup_verified=clean, environment_ready=bool(col_ok and clean),
            python_version=col.get('python'), pytest_version=col.get('pytest_version'))
        row['status'] = ('baseline_ready' if base_ok and good_ok and col_ok and clean
                         else 'baseline_mismatch' if col_ok and clean and good_ok else 'invalid_env')
        row['reason'] = row['status']
        row.pop('error', None)
    except Exception as exc:
        row.update(error=type(exc).__name__ + ': ' + str(exc), reason='preflight_recheck_failed')
    save(out / 'receipt.json', row)
    print(json.dumps(dict(task_id=tid, status=row['status'], error=row.get('error'))), flush=True)
    return row


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--only-task', action='append', required=True)
    parser.add_argument('--rebuild', action='store_true')
    parser.add_argument('--jobs', type=int, default=1)
    parser.add_argument('--test-files', action='store_true')
    args = parser.parse_args()
    args.input = args.input.resolve(); args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=False)
    if sha(CANONICAL.read_bytes()) != CANONICAL_SHA:
        raise ValueError('canonical drift')
    for p in [Path(__file__), ROOT / 'scripts/preflight_a5_repo_baseline.py', ROOT / 'scripts/a5_django_observer.py']:
        shutil.copy2(p, args.output / p.name)
    canonical = load(CANONICAL)
    tasks = {t['canonical_id']: t for t in canonical['target_tasks'] + canonical['preflight_history_candidates']}
    semaphore = asyncio.Semaphore(args.jobs)
    async def one(tid):
        async with semaphore:
            return await check(tasks[tid], args.input, args.output, args.rebuild, args.test_files)
    rows = await asyncio.gather(*(one(tid) for tid in args.only_task))
    save(args.output / 'receipts.json', dict(rows=rows, full_denominator=24, model_calls=0, paid=False,
                                          memory_build_eligible=False))


if __name__ == '__main__':
    asyncio.run(main())
