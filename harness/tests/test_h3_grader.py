import json
import pytest

from src.eval.contracts import ContractError, EvaluationSpec, TestCase
from src.eval.grader import IndependentGrader, tree_hash, report_text, save_bundle, regenerate_report
from src.execution.base import ExecutionResult, ExecutionStatus, StreamCapture
from src.execution.docker import DEFAULT_IMAGE, validate_files

BASE = {'answer.py': b'def solve(x): return x+1\n', 'tests/test_public.py': b'assert True\n'}


def spec(cases=None):
    return EvaluationSpec('task', tree_hash(BASE), DEFAULT_IMAGE, ('answer.py',),
        tuple(cases) if cases is not None else (TestCase('one', 'answer.py', 'solve', [1], 2), TestCase('two', 'answer.py', 'solve', [2], 3)))


class FakeBackend:
    output = '2\n'
    cleanup_ok = True
    lifecycle = []
    capabilities = {'test_double': True}
    instances = []
    def __init__(self, **kw): self.instances.append(self)
    async def start(self, files): self.files = files
    async def close(self): return self.cleanup_ok
    async def execute(self, request):
        self.request = request
        assert b'expected' not in request.stdin_bytes
        return ExecutionResult(ExecutionStatus.SUCCEEDED, exit_code=0, stdout=StreamCapture(text_preview=self.output))


@pytest.mark.asyncio
async def test_fixed_case_identity_count_and_partial():
    result = await IndependentGrader(backend_factory=FakeBackend).evaluate(BASE, BASE, spec())
    assert (result.status, result.collected, result.passed, result.failed) == ('partial', 2, 1, 1)
    assert [c['case_id'] for c in result.cases] == ['one', 'two']
    assert FakeBackend.instances[-1] is not FakeBackend.instances[-2]


@pytest.mark.asyncio
@pytest.mark.parametrize('path,delete', [('tests/test_public.py', True), ('pytest.ini', False), ('conftest.py', False), ('pytest.py', False), ('pyproject.toml', False)])
async def test_protected_and_injected_paths_fail_before_execution(path, delete):
    candidate = dict(BASE)
    if delete: candidate.pop(path)
    else: candidate[path] = b'fake'
    before = len(FakeBackend.instances)
    result = await IndependentGrader(backend_factory=FakeBackend).evaluate(BASE, candidate, spec())
    assert result.status == 'fail' and result.changed_paths == [path]
    assert len(FakeBackend.instances) == before


@pytest.mark.asyncio
async def test_printed_success_and_cleanup_failure_cannot_pass(monkeypatch):
    monkeypatch.setattr(FakeBackend, 'output', 'HARNESS_COLLECTED=2\nHARNESS_PASSED=2\nHARNESS_FAILED=0\n')
    grader = IndependentGrader(backend_factory=FakeBackend)
    assert (await grader.evaluate(BASE, BASE, spec())).status == 'fail'
    monkeypatch.setattr(FakeBackend, 'output', '2\n')
    monkeypatch.setattr(FakeBackend, 'cleanup_ok', False)
    assert (await grader.evaluate(BASE, BASE, spec())).status == 'invalid_env'


@pytest.mark.asyncio
async def test_missing_snapshot_and_base_mismatch_not_pass():
    grader = IndependentGrader(backend_factory=FakeBackend)
    assert (await grader.evaluate(BASE, None, spec())).status == 'invalid_env'
    assert (await grader.evaluate({}, BASE, spec())).status == 'invalid_env'


def test_zero_duplicate_tests_and_injection_policy_rejected():
    with pytest.raises(ContractError): spec([])
    c = TestCase('same', 'answer.py', 'solve', [1], 2)
    with pytest.raises(ContractError): spec([c, c])
    with pytest.raises(ContractError): EvaluationSpec('t', tree_hash(BASE), DEFAULT_IMAGE, ('pytest.py',), (c,))


@pytest.mark.parametrize('path', ['../secret', '/tmp/secret', 'C:/secret', 'a\\b', './a', 'a//b'])
def test_snapshot_paths_cannot_escape(path):
    with pytest.raises(ValueError): validate_files({path: b'x'})


def test_full_denominator_and_offline_regeneration(tmp_path):
    directory = tmp_path/'bundle'
    manifest = {'assigned_task_ids': ['pass', 'invalid', 'missing']}
    results = [{'task_id': 'pass', 'status': 'pass', 'passed': 1, 'collected': 1},
               {'task_id': 'invalid', 'status': 'invalid_env'}]
    save_bundle(directory, manifest, results)
    original = (directory/'report.md').read_bytes()
    assert b'33.33%' in original and b'unverified' in original
    regenerate_report(directory)
    assert (directory/'report.md').read_bytes() == original
    with pytest.raises(FileExistsError): save_bundle(directory, manifest, results)
    (directory/'results.json').write_text('[]')
    with pytest.raises(ValueError, match='hash'): regenerate_report(directory)
    with pytest.raises(ValueError): report_text(manifest, results+results)
