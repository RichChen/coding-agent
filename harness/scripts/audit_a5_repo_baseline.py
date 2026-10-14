"""Audit the final initial24 environment/baseline denominator without waivers."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import subprocess

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.preflight_a5_repo_baseline import (ROOT, CANONICAL, CANONICAL_SHA, load, save, sha,
    outcomes, PREVIOUS_ROOT, TRANSPORT_ROOT)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, action='append', required=True)
    parser.add_argument('--image-audit', type=Path, action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve(); output.mkdir(parents=True, exist_ok=False)
    assert sha(CANONICAL.read_bytes()) == CANONICAL_SHA
    canonical = load(CANONICAL)
    assigned = canonical['target_tasks'] + canonical['preflight_history_candidates']
    selected = {}
    for root in args.input:
        for path in (root.resolve() / 'tasks').glob('*/receipt.json'):
            row = load(path); selected[row['task_id']] = (row, path)
    assert set(selected) == {t['canonical_id'] for t in assigned} and len(assigned) == 24
    images = {}
    for root in args.image_audit:
        for path in root.resolve().glob('*/*.json'):
            info = load(path)
            if info.get('kind') in ('baseline', 'known-good'):
                images[(info['task_id'], info['kind'], info['image'])] = (info, path)
    previous = {r['task_id']: r for r in load(PREVIOUS_ROOT / 'receipts.json')['rows']}
    transport = {r['task_id']: r for r in load(TRANSPORT_ROOT / 'receipts.json')['rows']}
    rows = []; checks = []; bound = {}

    def check(tid, name, passed):
        checks.append(dict(task_id=tid, check=name, passed=bool(passed)))
        return bool(passed)

    def bind(path):
        bound[str(path)] = sha(path.read_bytes())

    for task in assigned:
        tid = task['canonical_id']; row, path = selected[tid]; bind(path)
        identity = check(tid, 'canonical_identity', row['repo'] == task['expected_repo']
                         and row['base_revision'] == task['expected_base_commit'])
        source = check(tid, 'complete_source_archive_binding',
            row.get('source', {}).get('archive_sha256') == transport[tid]['archive_sha256']
            and transport[tid]['status'] == 'transport_ready')
        result = dict(task_id=tid, role='target' if task in canonical['target_tasks'] else 'history',
            repo=row['repo'], base_revision=row['base_revision'], source=row.get('source'),
            source_complete=source, selected_receipt_ref=str(path), selected_receipt_sha256=sha(path.read_bytes()),
            model_calls=0, paid=False, memory_build_eligible=False)
        if row.get('carried_previous_attempt'):
            prior = previous[tid]
            valid = check(tid, 'exact_audited_prior_carry', prior['status'] == 'ready'
                and prior['source']['archive_sha256'] == row['source']['archive_sha256']
                and prior.get('image_digest') == row.get('image_digest')
                and prior.get('collection') == row.get('collection')
                and prior.get('baseline') == row.get('baseline'))
            result.update(environment_ready=identity and source and valid,
                environment_baseline_ready=identity and source and valid, grader_ready=valid,
                status='baseline_ready' if valid and source and identity else 'audit_failed',
                carried_previous_attempt=True, previous_receipt_ref=str(PREVIOUS_ROOT / 'receipts.json'))
        else:
            tree_ok = True; image_refs = {}
            for kind, key in [('baseline', 'baseline_image_digest'), ('known-good', 'known_good_image_digest')]:
                record = images.get((tid, kind, row.get(key)))
                valid = bool(record and record[0]['status'] == 'verified' and record[0]['cleanup_verified'])
                tree_ok = check(tid, kind+'_complete_image_tree', valid) and tree_ok
                if record:
                    bind(record[1]); image_refs[kind] = str(record[1])
            cpath = Path(row['collection']['receipt_ref']); bind(cpath)
            c = load(cpath); col = c.get('receipt', {}); ids = col.get('collected', [])
            col_ok = check(tid, 'full_unique_collection', c.get('execution', {}).get('exit_code') == 0
                and col.get('complete') and ids and len(ids) == len(set(ids)) and not col.get('collection_errors')
                and len(ids) == row['collection']['count'] and sha(json.dumps(ids).encode()) == row['collection']['hash'])
            binding = row.get('exact_f2p_binding', {})
            private_path = Path(row['private_source_binding']['path']); bind(private_path)
            private = load(private_path); expected = private['FAIL_TO_PASS']
            if isinstance(expected, str): expected = json.loads(expected)
            selection_ok = check(tid, 'all_private_f2p_retained', set(binding) == set(expected)
                and len(binding) == len(expected) and len(set(binding.values())) == len(expected)
                and set(binding.values()) <= set(ids)
                and private['instance_id'] == tid and private['base_commit'] == task['expected_base_commit']
                and sha(private_path.read_bytes()) == row['private_source_binding']['sha256'])
            bpath=Path(row['baseline']['receipt_ref']); gpath=Path(row['grader']['receipt_ref'])
            bind(bpath); bind(gpath); b=load(bpath); g=load(gpath)
            bo=outcomes(b.get('receipt', {})); go=outcomes(g.get('receipt', {})); nodes=list(binding.values())
            baseline_ok = bool(nodes) and all(bo.get(n) == 'failed' for n in nodes) and b.get('execution', {}).get('exit_code') == 1
            good_ok = bool(nodes) and all(go.get(n) == 'passed' for n in nodes) and g.get('execution', {}).get('exit_code') == 0
            clean = check(tid, 'all_runtime_cleanup', all(e.get('cleanup_verified') is True for e in (c,b,g)))
            # A measured mismatch is valid audit evidence, but never a green gate.
            check(tid, 'reported_baseline_matches_measured_result', (row['status']=='baseline_ready') == (col_ok and baseline_ok and good_ok and clean))
            env_ok = identity and source and tree_ok and col_ok and clean
            ready = env_ok and selection_ok and baseline_ok and good_ok
            result.update(status='baseline_ready' if ready else 'baseline_mismatch' if env_ok and good_ok else 'invalid_env',
                environment_ready=env_ok, environment_baseline_ready=ready, grader_ready=False,
                collection_count=len(ids), all_f2p_fail=baseline_ok, known_good_pass=good_ok,
                expected_f2p_count=len(nodes), actual_baseline_failed=[n for n in nodes if bo.get(n)=='failed'],
                unexpected_baseline_passed=[n for n in nodes if bo.get(n)=='passed'],
                baseline_image_digest=row.get('baseline_image_digest'), known_good_image_digest=row.get('known_good_image_digest'),
                image_audit_refs=image_refs, baseline_receipt_ref=str(bpath), known_good_receipt_ref=str(gpath))
        rows.append(result)
    cleanup_argv = ['docker', '--context', 'desktop-linux', 'ps', '-aq', '--filter', 'label=coding-harness.h3=true']
    cleanup = subprocess.run(cleanup_argv, capture_output=True, text=True, timeout=30)
    check('initial24', 'no_owned_containers_remaining', cleanup.returncode == 0 and not cleanup.stdout.strip())
    save(output/'cleanup.json', dict(argv=cleanup_argv, exit_code=cleanup.returncode,
                                   containers=cleanup.stdout.splitlines(), stderr=cleanup.stderr))
    valid = all(c['passed'] for c in checks)
    counts = dict(Counter(r['status'] for r in rows))
    readiness = dict(schema='a5.initial24.environment-baseline-audit.v1', assigned=24, full_denominator=24,
        canonical_sha256=CANONICAL_SHA, created_at=datetime.now(timezone.utc).isoformat(), audit_passed=valid,
        status='baseline_ready' if valid and all(r['environment_baseline_ready'] for r in rows) else 'blocked',
        environment_ready=sum(r['environment_ready'] for r in rows),
        environment_baseline_ready=sum(r['environment_baseline_ready'] for r in rows),
        grader_ready=sum(r['grader_ready'] for r in rows), status_counts=counts,
        model_calls=0, paid=False, paid_build_started=False, paid_pilot_started=False, memory_build_eligible=False,
        remaining16_preflight='not_started', blocking_tasks=[r['task_id'] for r in rows if not r['environment_baseline_ready']])
    save(output/'receipts.json',dict(rows=rows))
    save(output/'audit.json',dict(checks=checks, passed=sum(c['passed'] for c in checks), assigned=len(checks)))
    save(output/'readiness.json',readiness)
    save(output/'artifact-bindings.json',bound)
    save(output/'implementation-fingerprint.json', {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in [
        ROOT/'scripts/preflight_a5_repo_baseline.py', ROOT/'scripts/recheck_a5_repo_baseline.py',
        ROOT/'scripts/a5_django_observer.py', ROOT/'scripts/audit_a5_baseline_images.py', Path(__file__),
        ROOT/'src/execution/docker.py', ROOT/'src/eval/a5_image_tree.py',
        ROOT/'docs/upgrade/A5-IMAGE-BACKED-CONTINUATION-CONTRACT.md',
        ROOT/'docs/upgrade/A5-REPO-BASELINE-RUNTIME-NOTES.md']})
    print(json.dumps(readiness,ensure_ascii=False),flush=True)


if __name__=='__main__': main()
