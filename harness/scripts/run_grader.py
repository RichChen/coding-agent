#!/usr/bin/env python3
"""Grade frozen candidates, or regenerate a report without running any code."""
import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.eval.contracts import EvaluationSpec, canonical_hash
from src.eval.grader import IndependentGrader, EvaluationResult, decode_snapshot, regenerate_report, save_bundle
from src.runtime.session import source_fingerprint


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--assignments', help='JSON array: task_id, spec, base, candidate (snapshot JSON paths)')
    group.add_argument('--regenerate', help='Existing H3 bundle directory; offline only')
    parser.add_argument('--output-dir')
    parser.add_argument('--context', default='desktop-linux')
    args = parser.parse_args()
    if args.regenerate:
        regenerate_report(args.regenerate)
        return
    if not args.output_dir: parser.error('--assignments requires a new --output-dir')
    path = Path(args.assignments).resolve()
    assigned = json.loads(path.read_text(encoding='utf-8'))
    ids = [a['task_id'] for a in assigned]
    if not ids or len(set(ids)) != len(ids): parser.error('unique nonempty assigned task list required')
    results = []
    def load(name):
        return json.loads((path.parent/name).read_text(encoding='utf-8'))
    for item in assigned:
        try:
            spec = EvaluationSpec.from_mapping(load(item['spec']))
            if spec.task_id != item['task_id']: raise ValueError('task identity mismatch')
            result = await IndependentGrader(context=args.context).evaluate(
                decode_snapshot(load(item['base'])), decode_snapshot(load(item['candidate'])), spec)
        except Exception as exc:
            result = EvaluationResult(item['task_id'], reason=str(exc)[:1000])
        results.append(result)
    save_bundle(args.output_dir, dict(assigned_task_ids=ids, assignments_hash=canonical_hash(assigned),
        code_hash=source_fingerprint(Path(__file__).resolve().parent.parent), context=args.context), results)
    print(json.dumps([r.to_dict() for r in results], ensure_ascii=False, indent=2))
    if not all(r.success for r in results): raise SystemExit(2)


if __name__ == '__main__':
    asyncio.run(main())
