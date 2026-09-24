"""Audit A5 complete-source image-backed transport evidence."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--evidence', type=Path, required=True)
    args = ap.parse_args(); root = args.evidence.resolve()
    receipts = json.loads((root / 'receipts.json').read_text(encoding='utf-8'))['rows']
    checks = []; check = lambda name, ok, detail=None: checks.append({'check': name, 'passed': bool(ok), 'detail': detail})
    check('receipt_count_24', len(receipts) == 24, len(receipts))
    check('distinct_task_ids', len({r.get('task_id') for r in receipts}) == 24)
    check('all_transport_ready', all(r.get('status') == 'transport_ready' for r in receipts))
    check('all_typed_schema', all(r.get('source_tree_schema') == 'a5.typed-tree.v1' for r in receipts))
    check('all_archive_hashes', all(isinstance(r.get('archive_sha256'), str) and len(r['archive_sha256']) == 64 for r in receipts))
    check('all_tree_hashes', all(isinstance(r.get('source_tree_hash'), str) and len(r['source_tree_hash']) == 64 for r in receipts))
    check('all_no_model', all(r.get('model_calls') == 0 and r.get('paid') is False for r in receipts))
    for p in sorted(root.rglob('export.json')):
        row = json.loads(p.read_text(encoding='utf-8'))
        check(f'{p.parent.parent.name}:export', row.get('passed') is True and row.get('cleanup_verified') is True)
    for p in sorted(root.rglob('roundtrip.json')):
        row = json.loads(p.read_text(encoding='utf-8'))
        check(f'{p.parent.parent.name}:roundtrip', row.get('passed') is True and row.get('cleanup_verified') is True)
    for p in sorted(root.rglob('unassigned_edit.json')):
        row = json.loads(p.read_text(encoding='utf-8'))
        check(f'{p.parent.parent.name}:unassigned_rejection', row.get('passed') is True and row.get('cleanup_verified') is True)
    readiness = json.loads((root / 'readiness.json').read_text(encoding='utf-8'))
    check('paid_gate_stays_closed', readiness.get('memory_build_eligible') is False and readiness.get('paid') is False)
    output = {'schema': 'a5.transport-audit.v1', 'status': 'passed' if all(c['passed'] for c in checks) else 'failed',
              'checks': checks, 'passed_checks': sum(c['passed'] for c in checks), 'total_checks': len(checks),
              'model_calls': 0, 'paid': False, 'evidence': str(root)}
    (root / 'audit.json').write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': output['status'], 'passed_checks': output['passed_checks'], 'total_checks': output['total_checks']}))
    raise SystemExit(0 if output['status'] == 'passed' else 2)


if __name__ == '__main__':
    main()
