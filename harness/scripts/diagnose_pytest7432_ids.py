"""Produce an exact, non-mutating pytest-7432 node-id discrepancy report."""
import json
from pathlib import Path


def main():
    root = Path('docs/upgrade/evidence/A5-harness-preflight-14-host-pytest/tasks/pytest-dev__pytest-7432')
    private = json.loads((root / 'private-source-binding.json').read_text(encoding='utf-8'))
    receipt = json.loads((root / 'collection/evidence.json').read_text(encoding='utf-8'))['receipt']
    expected = list(dict.fromkeys(private['FAIL_TO_PASS'] + private['PASS_TO_PASS']))
    actual = receipt['collected']
    missing = [node for node in expected if node not in actual]
    report = {'schema': 'a5.pytest-nodeid-diagnosis.v1', 'task_id': 'pytest-dev__pytest-7432',
              'expected_count': len(expected), 'collection_count': len(actual), 'missing_exact_ids': missing,
              'actual_candidates_by_test_name': {node: [candidate for candidate in actual
                  if candidate.split('[', 1)[0] == node.split('[', 1)[0]]
                  for node in missing},
              'resolution': 'blocked_exact_contract_mismatch_no_fuzzy_mapping_or_spec_mutation',
              'model_calls': 0, 'paid': False}
    out = Path('docs/upgrade/evidence/A5-harness-preflight-19-final-audit/pytest-7432-nodeid-diagnosis.json')
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'missing_exact_ids': len(missing), 'output': str(out)}))


if __name__ == '__main__':
    main()
