import io
import tarfile

import pytest

from scripts.preflight_a5_sources import inspect_archive, LIMIT
from scripts.preflight_a5_pytest import valid_execution


TASK = {'expected_repo': 'owner/repo', 'expected_base_commit': 'a' * 40}
PREFIX = 'repo-' + 'a' * 40


def archive(path, entries):
    with tarfile.open(path, 'w:gz') as target:
        for name, data in entries:
            info = tarfile.TarInfo(PREFIX + '/' + name)
            info.size = len(data)
            target.addfile(info, io.BytesIO(data))


def test_oversize_source_is_fully_hashed_not_trimmed(tmp_path):
    path = tmp_path / 'source.tar.gz'
    archive(path, [('source.py', b'x'), ('docs/large.bin', b'a' * LIMIT)])
    result = inspect_archive(path, TASK)
    assert result['within_runtime_limits'] is False
    assert result['file_count'] == 2 and result['total_bytes'] == LIMIT + 1
    assert result['excluded_upstream_paths'] == []
    assert {e['path'] for e in result['entries']} == {'source.py', 'docs/large.bin'}
    assert all(len(e['sha256']) == 64 for e in result['entries'])


def test_file_count_limit_keeps_all_entries(tmp_path):
    path = tmp_path / 'source.tar.gz'
    archive(path, [(f'{i}.txt', b'') for i in range(2049)])
    result = inspect_archive(path, TASK)
    assert not result['within_runtime_limits'] and result['file_count'] == 2049


def test_symlinks_are_recorded_and_never_silently_removed(tmp_path):
    path = tmp_path / 'source.tar.gz'
    with tarfile.open(path, 'w:gz') as target:
        info = tarfile.TarInfo(PREFIX + '/link')
        info.type = tarfile.SYMTYPE
        info.linkname = 'elsewhere'
        target.addfile(info)
    result = inspect_archive(path, TASK)
    assert not result['within_runtime_limits']
    assert result['nonregular_paths'] == ['link'] and result['source_tree_hash'] is None
    assert result['file_count'] == 1


def test_wrong_commit_and_duplicate_members_rejected(tmp_path):
    path = tmp_path / 'source.tar.gz'
    archive(path, [('source.py', b'a'), ('source.py', b'b')])
    with pytest.raises(ValueError, match='duplicate'):
        inspect_archive(path, TASK)
    with pytest.raises(ValueError, match='commit mismatch'):
        inspect_archive(path, {**TASK, 'expected_base_commit': 'b' * 40})


@pytest.mark.parametrize('change', [
    {'cleanup_verified': False}, {'changed_frozen_inputs': ['testing/test_source.py']},
    {'execution': {'status': 'timed_out', 'exit_code': 0}},
    {'execution': {'status': 'succeeded', 'exit_code': 0, 'truncated': True}},
    {'receipt': {'exit_code': 1}},
])
def test_execution_integrity_and_cleanup_are_required(change):
    evidence = dict(status='executed', integrity_verified=True, changed_frozen_inputs=[],
                    cleanup_verified=True, execution=dict(status='succeeded', exit_code=0, truncated=False),
                    receipt=dict(exit_code=0))
    assert valid_execution(evidence)
    assert not valid_execution({**evidence, **change})
