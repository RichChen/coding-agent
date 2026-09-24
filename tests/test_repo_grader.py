import copy
from dataclasses import replace
import pytest
from src.eval.contracts import ContractError
from src.eval.grader import tree_hash, encode_snapshot
from src.eval.repo_grader import RepositorySpec, RepositoryGrader, classify_receipt
from src.execution.docker import DEFAULT_IMAGE

BASE={'pkg/a.py':b'def f(): return 1\n','tests/test_a.py':b'assert True\n','pyproject.toml':b''}
IDS=('tests/test_a.py::test_one','tests/test_a.py::test_two')


def spec(**kwargs):
    return RepositorySpec(**dict(dict(task_id='repo',base_hash=tree_hash(BASE),image=DEFAULT_IMAGE,
        editable_paths=('pkg/a.py',),test_paths=('tests',),python_paths=('.',),expected_nodeids=IDS),**kwargs))


def receipt():
    return dict(schema='repo.pytest.receipt.v1',complete=True,exit_code=0,collected=list(IDS),collection_errors=[],
        reports=[dict(nodeid=node,when=phase,outcome='passed',wasxfail=None) for node in IDS for phase in ('setup','call','teardown')])


def test_fixed_collection_phases_and_exit_are_all_required():
    r=receipt(); assert classify_receipt(r,IDS)==({n:'passed' for n in IDS},None)
    mutations=[lambda x:x.update(collected=[]),lambda x:x.update(collected=[IDS[0]]),
        lambda x:x.update(collected=[IDS[0],IDS[0]]),lambda x:x['reports'].pop(),
        lambda x:x.update(complete=False),lambda x:x.update(exit_code=5),
        lambda x:x['reports'].append(x['reports'][0]),
        lambda x:x.update(collection_errors=[dict(nodeid='tests',detail='dependency missing')])]
    for mutate in mutations:
        r=receipt(); mutate(r); assert classify_receipt(r,IDS)[1]
    r=receipt(); r['reports'][1]['outcome']='failed'
    assert classify_receipt(r,IDS)[1]=='exit_outcome_mismatch'


@pytest.mark.parametrize('path',['tests/test_a.py','conftest.py','pkg/conftest.py','pytest.py','pyproject.toml','sitecustomize.py','x.pth','../escape'])
def test_protected_editable_paths_rejected(path):
    with pytest.raises((ContractError,ValueError)): spec(editable_paths=(path,))


def test_empty_duplicate_and_vacuous_skip_denominators_rejected():
    for kwargs in (dict(expected_nodeids=()),dict(expected_nodeids=(IDS[0],IDS[0])),dict(allowed_nonpass=dict.fromkeys(IDS,'skipped'))):
        with pytest.raises(ContractError): spec(**kwargs)
    with pytest.raises(ContractError): spec(test_overlay=encode_snapshot({'pkg/a.py':b'override'}))


@pytest.mark.asyncio
@pytest.mark.parametrize('path,delete',[('tests/test_a.py',True),('tests/test_a.py',False),('pytest.py',False),('conftest.py',False),('pyproject.toml',False)])
async def test_candidate_tampering_rejected_before_execution(path,delete):
    class NeverRun(RepositoryGrader):
        async def execute(self,*args,**kwargs): raise AssertionError('must not execute')
    candidate=dict(BASE)
    if delete: candidate.pop(path)
    else: candidate[path]=b'fake pass'
    result=await NeverRun().evaluate(BASE,candidate,spec())
    assert result['status']=='fail' and result['reason']=='protected_or_unassigned_path_changed'


class StubGrader(RepositoryGrader):
    def __init__(self,evidence): self.evidence=evidence
    async def execute(self,*args,**kwargs): return copy.deepcopy(self.evidence)


def evidence():
    return dict(status='executed',integrity_verified=True,cleanup_ok=True,receipt=receipt(),input_changes_during_tests=[],
        execution=dict(status='succeeded',exit_code=0,truncated=False,stdout='ALL TESTS PASSED'))


@pytest.mark.asyncio
async def test_missing_receipt_stdout_fake_pass_and_cleanups_never_pass():
    mutations=[lambda e:e.update(receipt=None),lambda e:e.update(cleanup_ok=False),
        lambda e:e.update(integrity_verified=False),lambda e:e.update(status='invalid_env'),
        lambda e:e['execution'].update(truncated=True),lambda e:e['execution'].update(status='timed_out'),
        lambda e:e.update(input_changes_during_tests=['tests/test_a.py'])]
    for mutate in mutations:
        e=evidence(); mutate(e)
        result=await StubGrader(e).evaluate(BASE,BASE,spec())
        assert result['status']!='pass' and result['collected']==2


@pytest.mark.asyncio
async def test_required_skip_not_pass_allowed_baseline_skip_explicit():
    e=evidence(); e['receipt']['reports'][1]['outcome']='skipped'
    result=await StubGrader(e).evaluate(BASE,BASE,spec())
    assert result['status']=='partial' and result['passed']==1 and result['failed']==1
    result=await StubGrader(e).evaluate(BASE,BASE,spec(allowed_nonpass={IDS[0]:'skipped'},baseline_passed=(IDS[1],)))
    assert result['status']=='pass' and result['passed']==1 and result['skipped']==1
    assert result['regression_passed']==result['regression_assigned']==1


@pytest.mark.asyncio
async def test_wrong_base_missing_candidate_and_exact_success():
    grader=StubGrader(evidence())
    assert (await grader.evaluate(BASE,None,spec()))['status']=='invalid_env'
    assert (await grader.evaluate({},BASE,spec()))['status']=='invalid_env'
    result=await grader.evaluate(BASE,BASE,spec())
    assert result['status']=='pass' and result['passed']==2


def test_option_paths_non_test_overlay_and_malformed_receipt_rejected():
    with pytest.raises(ContractError): spec(test_paths=('--ignore=tests',))
    with pytest.raises(ContractError): spec(test_overlay=encode_snapshot({'pkg/other.py':b'x'}))
    for changes in ({'reports':None},{'reports':[None]},{'collected':[{}]},
                    {'exit_code':False},{'collection_errors':None}):
        r=receipt(); r.update(changes)
        assert classify_receipt(r,IDS)[1]


@pytest.mark.asyncio
async def test_collection_requires_process_success_and_verified_inputs():
    assert (await StubGrader(evidence()).collect(BASE,image=spec().image,test_paths=('tests',),python_paths=('.',)))['status']=='ready'
    for changes in ({'status':'failed','exit_code':1},{'status':'timed_out','exit_code':0}):
        e=evidence(); e['execution'].update(changes)
        result=await StubGrader(e).collect(BASE,image=spec().image,test_paths=('tests',),python_paths=('.',))
        assert result['status']=='invalid_env'


def test_full_archive_and_private_test_resources_are_complete():
    from pathlib import Path
    from scripts.prepare_repo_grader import extract
    from src.eval.grader import decode_snapshot
    import json
    directory=Path(__file__).resolve().parents[1]/'docs/upgrade/evidence/full-repo-grader/attempt-02'
    base=extract((directory/'flask-base.tar.gz').read_bytes())
    assert base==decode_snapshot(json.loads((directory/'public/base.json').read_text()))
    assert len(base)==250 and any(p.startswith('docs/') for p in base) and any(p.startswith('examples/') for p in base)
    overlay=decode_snapshot(json.loads((directory/'private/overlay.json').read_text()))
    assert set(overlay)=={'tests/test_config.py','tests/static/config.toml'}
    assert b'config.toml' in overlay['tests/test_config.py'] and overlay['tests/static/config.toml']


def test_dependency_negative_accepts_conftest_failure_but_not_unrelated_error():
    from scripts.preflight_repo_grader import negative_checks
    rows=[dict(status='fail',reason='protected_or_unassigned_path_changed') for _ in range(2)]
    rows += [dict(status='invalid_env',reason='missing_or_incomplete_receipt'),
        dict(status='invalid_env',evidence=dict(receipt=dict(exit_code=4,collection_errors=[]),
            execution=dict(status='failed',exit_code=4,stderr='ModuleNotFoundError: deliberately_missing_repo_dependency'))),
        dict(status='invalid_env',evidence=dict(execution=dict(status='timed_out')))]
    assert negative_checks(rows)
    rows[3]['evidence']['execution']['stderr']='unrelated dependency failure'
    assert not negative_checks(rows)


def test_report_preserves_assignments_and_detects_modified_results(tmp_path):
    import json
    from src.eval.repo_report import save_bundle, regenerate_report
    root=tmp_path/'bundle'
    save_bundle(root,dict(assigned_task_ids=['present','missing']),[dict(task_id='present',status='pass',passed=1,collected=1)])
    before=(root/'report.md').read_bytes()
    regenerate_report(root)
    assert (root/'report.md').read_bytes()==before
    assert b'missing' in before and b'unverified' in before and b'success rate:' not in before
    (root/'results.json').write_text(json.dumps([]))
    with pytest.raises(ValueError,match='hash mismatch'): regenerate_report(root)


@pytest.mark.asyncio
async def test_cli_missing_candidate_retains_frozen_test_denominator(tmp_path):
    from dataclasses import asdict
    from scripts.run_repo_grader import grade
    from src.eval.grader import save_json
    save_json(tmp_path/'spec.json',asdict(spec()))
    save_json(tmp_path/'base.json',encode_snapshot(BASE))
    save_json(tmp_path/'assigned.json',[dict(task_id='repo',spec='spec.json',base='base.json',candidate='missing.json')])
    results=await grade(tmp_path/'assigned.json',tmp_path/'output','unused')
    assert len(results)==1 and results[0]['status']=='invalid_env' and results[0]['collected']==2
