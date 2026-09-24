import base64
import json
from decimal import Decimal
from pathlib import Path

import pytest

from src.eval.a5_receipts import import_receipt, validate_receipt
from src.eval.a5_snapshot import apply_delta, build_manifest, chunk_bytes, make_delta, tree_hash, verify_archive
from src.policy.cny_budget import A5BudgetPlan, CnyBudgetError, CnyBudgetLedger, PriceSnapshot
from src.runtime.session import source_fingerprint
from scripts.a5_preflight import run as run_a5_preflight


def price(verified=True):
    return PriceSnapshot('DeepSeek', 'deepseek-flash', 'snapshot-20260921', 'CNY',
        Decimal('0.010'), Decimal('2.000'), Decimal('8.000'), 'https://provider/pricing', '2026-09-21', verified)


def test_large_manifest_is_complete_and_chunked_without_cropping():
    files = {'src/a.py': b'a' * 5_000_000, 'src/b.py': b'b' * 5_000_000}
    archive = b'archive' * 2_000_000
    manifest = build_manifest(files, task_id='t', repo='r', base_revision='rev', archive=archive)
    assert manifest.transport_mode == 'image_backed_base_plus_delta'
    assert manifest.file_count == 2 and manifest.total_bytes == 10_000_000
    assert sum(c['size'] for c in manifest.chunks) == len(archive)
    assert manifest.source_tree_hash == tree_hash(files)


def test_delta_roundtrip_and_unassigned_or_base_drift_rejected():
    base = {'src/a.py': b'a', 'README': b'r'}
    candidate = {'src/a.py': b'changed', 'README': b'r'}
    delta = make_delta(base, candidate, allowed_paths=('src/a.py',))
    assert apply_delta(base, delta, allowed_paths=('src/a.py',)) == candidate
    with pytest.raises(ValueError, match='allowlist'):
        make_delta(base, {'README': b'changed', 'src/a.py': b'a'}, allowed_paths=('src/a.py',))
    with pytest.raises(ValueError, match='base tree'):
        apply_delta({'src/a.py': b'wrong', 'README': b'r'}, delta, allowed_paths=('src/a.py',))


def test_image_backed_manifest_accepts_oversized_source_file_but_archive_chunks_are_strict():
    files = {'vendor/large.dat': b'x' * (8 * 1024 * 1024 + 1)}
    archive = b'archive-payload'
    manifest = build_manifest(files, task_id='t', repo='r', base_revision='rev', archive=archive)
    assert manifest.transport_mode == 'image_backed_base_plus_delta'
    assert verify_archive(manifest, archive) == [archive]
    tampered = list(manifest.chunks)
    tampered[0] = dict(tampered[0], index=99)
    broken = manifest.__class__(manifest.task_id, manifest.repo, manifest.base_revision,
        manifest.source_tree_hash, manifest.file_count, manifest.total_bytes, manifest.files,
        manifest.archive_sha256, manifest.archive_bytes, tuple(tampered), manifest.transport_mode)
    with pytest.raises(ValueError, match='chunk mismatch'):
        verify_archive(broken, archive)


def test_cny_ledger_fails_closed_and_unknown_keeps_reserve():
    with pytest.raises(CnyBudgetError): CnyBudgetLedger(price(False))
    ledger = CnyBudgetLedger(price())
    res = ledger.reserve(phase='build', operation_id='build-1', component='repair', prompt_tokens=48_000, max_output_tokens=12_000)
    before = ledger.cost_committed
    row = ledger.settle(res.reservation_id, None)
    assert row['status'] == 'unknown_keeps_reserve' and ledger.cost_committed == before
    assert ledger.snapshot()['currency'] == 'CNY'
    for index in range(1, 20):
        ledger.reserve(phase='build', operation_id=f'build-{index+1}', component='repair', prompt_tokens=48_000, max_output_tokens=12_000)
    with pytest.raises(CnyBudgetError):
        ledger.reserve(phase='build', operation_id='too-many', component='repair', prompt_tokens=48_000, max_output_tokens=12_000)


def test_receipt_requires_binding_and_does_not_claim_following():
    receipt = {
        'schema': 'a5.receipt.v1', 'task_id': 't', 'phase': 'pilot', 'variant': 'B1', 'repeat': 1,
        'operation_id': 'op', 'source_snapshot_hash': 'a' * 64, 'model_binding_hash': 'b' * 64, 'source_fingerprint': 'c' * 64,
        'model_attempts': [{'attempt_id': 'a1', 'component': 'repair'}],
        'injections': [{'candidate_hash': 'd' * 64, 'source_hash': 'a' * 64, 'evidence_ref': 'e'}],
        'grader': {'status': 'pass'}, 'ledger': {'schema': 'a5.cny.ledger.v1'},
    }
    assert validate_receipt(receipt, expected_model_binding='b' * 64, expected_source_fingerprint='c' * 64).valid
    assert import_receipt(receipt)['following_claim'] == 'not_inferred_from_injection'
    receipt['model_binding_hash'] = 'drift'
    assert not validate_receipt(receipt, expected_model_binding='e' * 64).valid
    receipt['model_binding_hash'] = 'b' * 64
    receipt['source_fingerprint'] = 'short'
    assert not validate_receipt(receipt).valid


def test_a5_manifest_exact_20_plus_4_and_240_schedule():
    data = json.loads(open('configs/a5/pilot20-harness-manifest.json', encoding='utf-8').read())
    assert len(data['targets']) == 20 and len(data['historical_pool']) == 4
    assert not set(data['targets']) & set(data['historical_pool'])
    assert data['planned_task_runs'] == 20 * 4 * 3


def test_a5_preflight_blocks_pending_inputs_without_paid_side_effects():
    result = run_a5_preflight(Path('configs/a5/pilot20-harness-manifest.json'))
    assert result['status'] == 'blocked'
    assert result['model_calls'] == 0
    assert result['paid_build_started'] is False
    assert result['paid_pilot_started'] is False
    assert 'model_snapshot_and_current_price_missing' in result['errors']
    assert '24_environment_baseline_receipts_missing' in result['errors']
    assert 'dual_source_fingerprint_not_refrozen' in result['errors']


def test_a5_environment_template_names_all_24_tasks_without_claiming_baseline():
    result = run_a5_preflight(
        Path('configs/a5/pilot20-harness-manifest.json'),
        environments=Path('configs/a5/environment-preflight.template.json'),
    )
    assert result['status'] == 'blocked'
    assert result['environment_rows'] == 0
    assert 'environment_row_count' in result['errors']
    assert result['model_calls'] == 0


def test_a5_preflight_rejects_duplicate_or_unproved_environment_rows():
    manifest_path = Path('configs/a5/pilot20-harness-manifest.json')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    tasks = manifest['targets'] + manifest['historical_pool']
    rows = [{
        'task_id': task, 'repo': task.split('__')[0], 'base_revision': 'rev',
        'source_tree_hash': 'a' * 64, 'image_digest': 'python@sha256:' + 'b' * 64,
        'python_version': '3.11', 'pytest_version': '8', 'test_collection_hash': 'c' * 64,
        'collected_count': 1, 'baseline_status': 'not_started', 'baseline_failed_nodeids': [],
        'cleanup_verified': False, 'model_calls': 0,
    } for task in tasks]
    rows[-1]['task_id'] = rows[0]['task_id']
    env_path = Path('configs/a5/.a5-test-env.json')
    try:
        env_path.write_text(json.dumps({'schema': 'a5.environment-baseline.v1', 'rows': rows}), encoding='utf-8')
        result = run_a5_preflight(manifest_path, environments=env_path)
    finally:
        env_path.unlink(missing_ok=True)
    assert result['status'] == 'blocked'
    assert 'environment_not_baselined' in result['errors']
    assert 'baseline_failure_evidence_missing' in result['errors']
    assert 'environment_task_coverage' in result['errors']
