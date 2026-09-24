"""Regression tests for calibration defects discovered in real A5 smoke runs."""
import io
import tarfile
import pytest

from scripts.preflight_a5_repo_baseline import apply_patch_tree, outcomes
from scripts.recheck_a5_repo_baseline import resolve_ids


def test_known_good_keeps_the_identical_private_test_patch(tmp_path):
    revision = 'a' * 40
    archive = tmp_path / 'source.tar.gz'
    with tarfile.open(archive, 'w:gz', pax_headers={'comment': revision}) as stream:
        root = tarfile.TarInfo('repo-' + revision)
        root.type = tarfile.DIRTYPE
        root.mode = 0o755
        stream.addfile(root)
        data = b'value = 0\n'
        member = tarfile.TarInfo(root.name + '/module.py')
        member.mode = 0o644
        member.size = len(data)
        stream.addfile(member, io.BytesIO(data))
    test_patch = ('diff --git a/test_new.py b/test_new.py\nnew file mode 100644\n'
                  '--- /dev/null\n+++ b/test_new.py\n@@ -0,0 +1,2 @@\n'
                  '+from module import value\n+assert value == 1\n')
    gold_patch = ('diff --git a/module.py b/module.py\n--- a/module.py\n'
                  '+++ b/module.py\n@@ -1 +1 @@\n-value = 0\n+value = 1\n')
    out = tmp_path / 'staging'
    out.mkdir()
    apply_patch_tree(archive, 'owner/repo', revision, test_patch, gold_patch, out)
    with tarfile.open(out / 'baseline.tar.gz') as baseline, tarfile.open(out / 'known-good.tar.gz') as gold:
        assert baseline.extractfile('test_new.py').read() == gold.extractfile('test_new.py').read()
        assert baseline.extractfile('module.py').read() == b'value = 0\n'
        assert gold.extractfile('module.py').read() == b'value = 1\n'


def test_setup_failure_and_missing_call_cannot_prove_a_defect():
    rows = [dict(nodeid='broken_env', when='setup', outcome='failed'),
            dict(nodeid='real_defect', when='call', outcome='failed'),
            dict(nodeid='no_call', when='setup', outcome='passed')]
    assert outcomes({'reports': rows}) == dict(broken_env='error', real_defect='failed', no_call='incomplete')


def test_sympy_labels_bind_across_all_patched_files_without_guessing(tmp_path):
    paths = ['sympy/codegen/tests/test_cnodes.py', 'sympy/core/tests/test_basic.py']
    ids = [paths[0]+'::test_sizeof', paths[1]+'::test_atoms']
    assert list(resolve_ids('sympy', ['test_sizeof', 'test_atoms'], ids, paths, tmp_path).values()) == ids
    with pytest.raises(ValueError, match='exactly one'):
        resolve_ids('pytest-dev', ['test_file.py::test_parameter[True'],
                    ['test_file.py::test_parameter[True, reason="example"]'], [], tmp_path)


def test_django_description_requires_exact_unique_collected_method(tmp_path):
    path = tmp_path / 'baseline/tests/commands/test_cases.py'
    path.parent.mkdir(parents=True)
    path.write_text('class CommandTests:\n    def test_parser(self):\n        """Parser forwards kwargs."""\n        pass\n')
    node = 'commands.test_cases.CommandTests.test_parser'
    assert resolve_ids('django', ['Parser forwards kwargs.'], [node],
                       ['tests/commands/test_cases.py'], tmp_path) == {'Parser forwards kwargs.': node}
    with pytest.raises(ValueError, match='exactly one'):
        resolve_ids('django', ['Parser forwards kwargs'], [node], ['tests/commands/test_cases.py'], tmp_path)
