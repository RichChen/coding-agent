"""Offline whole-repository reports, keeping calibration distinct from agent runs."""
import json
from pathlib import Path

from src.eval.contracts import canonical_hash
from src.eval.grader import save_json
from src.tracing.artifacts import atomic_replace


def report_text(manifest, results):
    ids=manifest['assigned_task_ids']
    by_id={r['task_id']:r for r in results}
    if not ids or len(ids)!=len(set(ids)) or len(by_id)!=len(results) or set(by_id)-set(ids):
        raise ValueError('invalid assigned denominator or result identities')
    lines=['# Whole-repository evaluation', '', manifest.get('purpose',manifest.get('scope','')),
        '', f'Assigned: {len(ids)}. Missing and invalid results remain assigned.',
        'Model calls by this grader: 0. Calibration outcomes are not agent success rates.', '',
        '| Task | Status | Passed / frozen tests |', '| --- | --- | --- |']
    for task in ids:
        r=by_id.get(task,{})
        label=json.dumps(task,ensure_ascii=True).replace('|','\\|')
        lines.append(f"| {label} | {r.get('status','unverified')} | {r.get('passed',0)} / {r.get('collected','?')} |")
    return '\n'.join(lines)+'\n'


def save_bundle(directory, manifest, results):
    directory=Path(directory)
    manifest=dict(manifest,schema='repo.pytest.bundle.v1',results_hash=canonical_hash(results))
    report=report_text(manifest,results)
    directory.mkdir(parents=True,exist_ok=False)
    save_json(directory/'manifest.json',manifest)
    save_json(directory/'results.json',results)
    atomic_replace(directory/'report.md',report.encode())


def regenerate_report(directory):
    directory=Path(directory)
    manifest=json.loads((directory/'manifest.json').read_text(encoding='utf-8'))
    results=json.loads((directory/'results.json').read_text(encoding='utf-8'))
    if manifest.get('schema')!='repo.pytest.bundle.v1' or canonical_hash(results)!=manifest['results_hash']:
        raise ValueError('bundle schema or results hash mismatch')
    atomic_replace(directory/'report.md',report_text(manifest,results).encode())
