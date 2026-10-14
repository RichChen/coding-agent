import base64
import copy
import io
import tarfile

import pytest

from src.eval.a5_image_tree import (archive_manifest, canonical, sha, tree_hash,
                                   validate_delta, validate_entries, LIMIT)


def file_meta(data=b'x', mode=0o644):
    return dict(kind='file', mode=mode, size=len(data), sha256=sha(data))


def tree():
    return {'src': dict(kind='dir', mode=0o755), 'src/code.py': file_meta(),
            'docs': dict(kind='dir', mode=0o755), 'docs/source': file_meta(b'asset'),
            'docs/link': dict(kind='symlink', mode=0o777, target='source')}


def manifest():
    entries = tree()
    return dict(entries=entries, source_tree_hash=tree_hash(entries))


def delta():
    m = manifest(); candidate = copy.deepcopy(m['entries']); candidate['src/code.py'] = file_meta(b'new')
    return dict(schema='a5.typed-tree.delta.v1', base_tree_hash=m['source_tree_hash'],
                candidate_tree_hash=tree_hash(candidate), deleted=[],
                changed={'src/code.py': dict(metadata=file_meta(b'new'), content=base64.b64encode(b'new').decode())})


def test_link_and_executable_mode_are_bound_not_omitted():
    base = tree(); changed = copy.deepcopy(base)
    changed['src/code.py']['mode'] = 0o755
    assert tree_hash(changed) != tree_hash(base)
    changed = copy.deepcopy(base); changed['docs/link']['target'] = '../src/code.py'
    assert tree_hash(changed) != tree_hash(base)


@pytest.mark.parametrize('target', ['../../outside', '/outside', 'C:/outside', 'link', 'missing'])
def test_escaping_cyclic_and_dangling_links_rejected(target):
    entries = tree(); entries['docs/link']['target'] = target
    with pytest.raises(ValueError):
        validate_entries(entries)


def test_child_below_link_and_special_mode_rejected():
    entries = tree(); entries['docs/link/child'] = file_meta()
    with pytest.raises(ValueError, match='ancestor'):
        validate_entries(entries)
    entries = tree(); entries['src/code.py']['mode'] = 0o4755
    with pytest.raises(ValueError, match='mode'):
        validate_entries(entries)


def test_delta_binds_source_candidate_contents_and_allowlist():
    m, d = manifest(), delta()
    result = validate_delta(m, d, ['src/code.py'])
    assert result['src/code.py'] == file_meta(b'new')
    assert result['docs/link'] == m['entries']['docs/link']
    with pytest.raises(ValueError, match='unassigned'):
        validate_delta(m, d, [])
    for field in ('base_tree_hash', 'candidate_tree_hash'):
        wrong = {**d, field: '0' * 64}
        with pytest.raises(ValueError, match='hash mismatch'):
            validate_delta(m, wrong, ['src/code.py'])
    wrong = copy.deepcopy(d); wrong['changed']['src/code.py']['content'] = 'YWJj'
    with pytest.raises(ValueError, match='content mismatch'):
        validate_delta(m, wrong, ['src/code.py'])


def test_delta_mode_link_and_duplicate_deletion_rejected():
    m, d = manifest(), delta()
    d['changed']['src/code.py']['metadata']['mode'] = 0o755
    with pytest.raises(ValueError, match='mode'):
        validate_delta(m, d, ['src/code.py'])
    d = delta(); d['changed']['docs/link'] = d['changed'].pop('src/code.py')
    with pytest.raises(ValueError, match='type or mode'):
        validate_delta(m, d, ['docs/link'])
    d = delta(); d['deleted'] = ['docs/source', 'docs/source']
    with pytest.raises(ValueError, match='invalid delta changes'):
        validate_delta(m, d, ['src/code.py', 'docs/source'])


def test_delta_byte_limit_includes_base64_and_json():
    m, d = manifest(), delta()
    data = b'z' * (LIMIT * 3 // 4)
    d['changed']['src/code.py'] = dict(metadata=file_meta(data), content=base64.b64encode(data).decode())
    assert len(canonical(d)) > LIMIT
    with pytest.raises(ValueError, match='byte limit'):
        validate_delta(m, d, ['src/code.py'])


def test_archive_retains_safe_link_and_rejects_duplicate_and_hardlink(tmp_path):
    revision = 'a' * 40; prefix = 'repo-' + revision
    path = tmp_path / 'source.tar.gz'
    def write(extra=None):
        with tarfile.open(path, 'w:gz', pax_headers={'comment': revision}) as tar:
            root = tarfile.TarInfo(prefix); root.type = tarfile.DIRTYPE; root.mode = 0o755; tar.addfile(root)
            file = tarfile.TarInfo(prefix + '/code.py'); file.size = 1; file.mode = 0o755; tar.addfile(file, io.BytesIO(b'x'))
            link = tarfile.TarInfo(prefix + '/link'); link.type = tarfile.SYMTYPE; link.linkname = 'code.py'; link.mode = 0o777; tar.addfile(link)
            if extra:
                tar.addfile(extra)
    write(); m = archive_manifest(path, 'owner/repo', revision)
    assert m['file_count'] == 2 and m['total_bytes'] == 1
    assert m['entries']['link']['target'] == 'code.py'
    duplicate = tarfile.TarInfo(prefix + '/code.py')
    write(duplicate)
    with pytest.raises(ValueError, match='duplicate'):
        archive_manifest(path, 'owner/repo', revision)
    hardlink = tarfile.TarInfo(prefix + '/hard'); hardlink.type = tarfile.LNKTYPE; hardlink.linkname = prefix + '/code.py'
    write(hardlink)
    with pytest.raises(ValueError, match='unsupported archive'):
        archive_manifest(path, 'owner/repo', revision)
