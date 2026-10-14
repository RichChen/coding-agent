"""Prepare typed complete-tree manifests for A5 image-backed source bases."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.eval.a5_image_tree import archive_manifest

SOURCE = ROOT / 'docs/upgrade/evidence/A5-harness-preflight-12-host-sources'
AGENT = ROOT.parent / 'coding-agent'
CANONICAL = AGENT / 'configs/a5/canonical-handoff.json'
PROJECTION = AGENT / 'configs/a5/pilot20-harness-consumption-manifest.json'
CANONICAL_SHA = 'd18d9fa78da00230c30d62c61abce168b91812871d3435e14702aad7a761774c'
PROJECTION_SHA = '33ab6922caf6909888d672a8d97df49f305ed4cdabb8c402dfca4bca88cb0180'


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_new(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    output = args.output.resolve(); output.mkdir(parents=True, exist_ok=False)
    canonical_bytes, projection_bytes = CANONICAL.read_bytes(), PROJECTION.read_bytes()
    if sha(canonical_bytes) != CANONICAL_SHA or sha(projection_bytes) != PROJECTION_SHA:
        raise ValueError('canonical input drift')
    canonical, projection = json.loads(canonical_bytes), json.loads(projection_bytes)
    tasks = [{**t, 'role': 'target'} for t in canonical['target_tasks']]
    tasks += [{**t, 'role': 'preflight_history_candidate'} for t in canonical['preflight_history_candidates']]
    if [t['canonical_id'] for t in tasks] != projection['targets'] + projection['preflight_history_subset']:
        raise ValueError('canonical task order drift')
    rows = []
    for task in tasks:
        tid = task['canonical_id']; src = SOURCE / 'tasks' / tid
        out = output / 'tasks' / tid; out.mkdir(parents=True)
        receipt = json.loads((src / 'source-receipt.json').read_text(encoding='utf-8'))
        try:
            manifest = archive_manifest(src / 'source.tar.gz', receipt['repo'], receipt['base_revision'])
            if manifest['archive_sha256'] != receipt['source']['archive_sha256']:
                raise ValueError('archive receipt hash mismatch')
            manifest.update(task_id=tid, role=task['role'])
            write_new(out / 'typed-tree-manifest.json', manifest)
            row = {'task_id': tid, 'repo': receipt['repo'], 'base_revision': receipt['base_revision'],
                   'status': 'typed_tree_ready', 'source_archive_sha256': manifest['archive_sha256'],
                   'source_tree_hash': manifest['source_tree_hash'], 'file_count': manifest['file_count'],
                   'directory_count': manifest['directory_count'], 'total_bytes': manifest['total_bytes'],
                   'typed_manifest_ref': str(out / 'typed-tree-manifest.json'), 'model_calls': 0, 'paid': False}
        except Exception as exc:
            row = {'task_id': tid, 'repo': receipt.get('repo'), 'base_revision': receipt.get('base_revision'),
                   'status': 'invalid_env', 'reason': type(exc).__name__ + ': ' + str(exc), 'model_calls': 0, 'paid': False}
        write_new(out / 'typed-tree-receipt.json', row); rows.append(row)
    counts = {s: sum(r['status'] == s for r in rows) for s in sorted({r['status'] for r in rows})}
    write_new(output / 'manifest.json', {'schema': 'a5.typed-tree-preflight.v1', 'attempt': 22,
        'created_at': datetime.now(timezone.utc).isoformat(), 'canonical_sha256': CANONICAL_SHA,
        'projection_sha256': PROJECTION_SHA, 'assigned': len(rows), 'full_denominator': 24,
        'model_calls': 0, 'paid': False, 'status_counts': counts,
        'contract': 'docs/upgrade/A5-IMAGE-BACKED-CONTINUATION-CONTRACT.md'})
    write_new(output / 'receipts.json', {'schema': 'a5.typed-tree-preflight.receipts.v1', 'rows': rows})
    write_new(output / 'readiness.json', {'status': 'blocked', 'assigned': len(rows), 'full_denominator': 24,
        'status_counts': counts, 'typed_tree_ready': sum(r['status'] == 'typed_tree_ready' for r in rows),
        'baseline_grader_ready': 0, 'model_calls': 0, 'paid': False,
        'paid_build_started': False, 'paid_pilot_started': False,
        'next_gate': 'repo_specific_image_build_and_environment_baseline'})
    write_new(output / 'artifact-manifest.json', {p.relative_to(output).as_posix(): sha(p.read_bytes())
        for p in sorted(output.rglob('*')) if p.is_file()})
    print(json.dumps(counts, sort_keys=True))


if __name__ == '__main__':
    main()
