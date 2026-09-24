"""Whole-repository pytest grading, outside the agent loop and private by default.

Fixed collection identities and protected files defend ordinary grading errors
and test tampering. Same-process malicious Python can still subvert pytest;
receipts are evidence, not an unforgeable attestation.
"""
from __future__ import annotations
import asyncio
import base64
import hashlib
import json
import math
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path, PurePosixPath

from src.eval.contracts import ContractError, canonical_hash
from src.eval.grader import tree_hash
from src.execution.base import ExecutionRequest, ExecutionStatus, OutputQuotas
from src.execution.docker import DockerExecutionBackend, image_is_pinned, validate_files

RUNNER = Path(__file__).with_name('repo_pytest_runner.py').read_text(encoding='utf-8')
RUNNER_HASH = hashlib.sha256(RUNNER.encode()).hexdigest()
PROTECTED_NAMES = {'conftest.py','pytest.py','pytest.ini','pyproject.toml','setup.cfg','setup.py',
                   'tox.ini','sitecustomize.py','usercustomize.py','__init__.pth'}


def relative_path(value, *, dot=False):
    if dot and value == '.': return
    if not isinstance(value,str): raise ContractError('path must be a string')
    if value.startswith('-'): raise ContractError('option-like path rejected')
    validate_files({value:b''})


@dataclass(frozen=True)
class RepositorySpec:
    task_id: str
    base_hash: str
    image: str
    editable_paths: tuple[str,...]
    test_paths: tuple[str,...]
    python_paths: tuple[str,...]
    expected_nodeids: tuple[str,...]
    test_overlay: dict[str,str] = field(default_factory=dict)  # base64 private bytes
    allowed_nonpass: dict[str,str] = field(default_factory=dict)
    baseline_passed: tuple[str,...] = ()
    timeout_seconds: float = 300
    runner_hash: str = RUNNER_HASH

    def __post_init__(self):
        if not self.task_id or not image_is_pinned(self.image): raise ContractError('task and pinned image required')
        if len(self.base_hash)!=64 or any(c not in '0123456789abcdef' for c in self.base_hash): raise ContractError('base hash required')
        if self.runner_hash != RUNNER_HASH: raise ContractError('runner version mismatch')
        if not self.editable_paths or len(set(self.editable_paths))!=len(self.editable_paths): raise ContractError('unique editable paths required')
        if not self.test_paths or not self.python_paths: raise ContractError('explicit tests and import paths required')
        for p in (*self.editable_paths,*self.test_paths): relative_path(p)
        for p in self.python_paths: relative_path(p,dot=True)
        overlay=decode_overlay(self.test_overlay)
        if any(not any(p==t or p.startswith(t+'/') for t in self.test_paths) for p in overlay):
            raise ContractError('private overlay must stay inside declared tests')
        for p in self.editable_paths:
            parts=PurePosixPath(p).parts
            if (PurePosixPath(p).name in PROTECTED_NAMES or p.endswith('.pth') or
                any(part in ('tests','test','.oracle','.grader_private') for part in parts) or
                PurePosixPath(p).name.startswith('test_') or p in overlay or
                any(p==t or p.startswith(t+'/') for t in self.test_paths)):
                raise ContractError('test/config paths cannot be editable')
        if not 0<len(self.expected_nodeids)<=10000 or len(set(self.expected_nodeids))!=len(self.expected_nodeids):
            raise ContractError('nonempty unique frozen test identities required')
        if any(not isinstance(n,str) or not n or '\x00' in n for n in self.expected_nodeids): raise ContractError('invalid node id')
        if (set(self.allowed_nonpass)-set(self.expected_nodeids) or
            any(s not in ('skipped','xfailed') for s in self.allowed_nonpass.values())):
            raise ContractError('only explicitly frozen skip/xfail allowed')
        if set(self.allowed_nonpass)==set(self.expected_nodeids): raise ContractError('at least one required test')
        if set(self.baseline_passed)-set(self.expected_nodeids) or set(self.baseline_passed)&set(self.allowed_nonpass):
            raise ContractError('invalid baseline regression identities')
        if not math.isfinite(self.timeout_seconds) or not 0<self.timeout_seconds<=600: raise ContractError('invalid timeout')

    @classmethod
    def from_mapping(cls,raw):
        raw=dict(raw)
        for k in ('editable_paths','test_paths','python_paths','expected_nodeids','baseline_passed'):
            raw[k]=tuple(raw.get(k,()))
        return cls(**raw)

    def manifest(self):
        return dict(schema='repo.pytest.spec.v1',task_id=self.task_id,base_hash=self.base_hash,image=self.image,
            private_spec_hash=canonical_hash(asdict(self)),runner_hash=self.runner_hash,
            assigned_cases=len(self.expected_nodeids),required_cases=len(self.expected_nodeids)-len(self.allowed_nonpass),
            test_overlay_hash=tree_hash(decode_overlay(self.test_overlay)))


def decode_overlay(value):
    return validate_files({p:base64.b64decode(data,validate=True) for p,data in value.items()})


def classify_receipt(receipt, expected):
    """Never infer a test from a printed count or from a zero exit code alone."""
    if not isinstance(receipt,dict) or receipt.get('schema')!='repo.pytest.receipt.v1' or receipt.get('complete') is not True:
        return {},'missing_or_incomplete_receipt'
    collected=receipt.get('collected',[])
    if not isinstance(collected,list) or not collected or any(not isinstance(n,str) for n in collected):
        return {},'invalid_collection'
    if len(set(collected))!=len(collected) or set(collected)!=set(expected):
        return {},'test_identity_or_count_mismatch'
    if receipt.get('collection_errors')!=[] or type(receipt.get('exit_code')) is not int or receipt['exit_code'] not in (0,1): return {},'collection_or_runner_error'
    by_id={n:{} for n in expected}
    reports=receipt.get('reports')
    if not isinstance(reports,list): return {},'invalid_reports'
    for report in reports:
        if not isinstance(report,dict): return {},'invalid_report'
        node,phase=report.get('nodeid'),report.get('when')
        if not isinstance(node,str) or not isinstance(phase,str): return {},'invalid_report_identity'
        if node not in by_id or phase not in ('setup','call','teardown') or phase in by_id[node]:
            return {},'invalid_or_duplicate_report'
        if report.get('outcome') not in ('passed','failed','skipped'): return {},'invalid_outcome'
        by_id[node][phase]=report
    outcomes={}
    for node,phases in by_id.items():
        if 'setup' not in phases or 'teardown' not in phases: return {},'incomplete_test_phases'
        if any(r['outcome']=='failed' for r in phases.values()): outcomes[node]='failed'
        elif any(r.get('wasxfail') is not None for r in phases.values()):
            outcomes[node]='xfailed' if any(r['outcome']=='skipped' for r in phases.values()) else 'xpassed'
        elif any(r['outcome']=='skipped' for r in phases.values()): outcomes[node]='skipped'
        elif set(phases)=={'setup','call','teardown'}: outcomes[node]='passed'
        else: return {},'missing_call_report'
    failed=any(v=='failed' for v in outcomes.values())
    if (failed and receipt['exit_code']!=1) or (not failed and receipt['exit_code']!=0): return {},'exit_outcome_mismatch'
    return outcomes,None


class RepositoryGrader:
    def __init__(self,*,context='desktop-linux',backend_factory=DockerExecutionBackend):
        self.context,self.backend_factory=context,backend_factory

    async def execute(self,files,*,image,test_paths,python_paths,collect_only=False,timeout=300):
        files=validate_files(files)
        for p in test_paths: relative_path(p)
        for p in python_paths: relative_path(p,dot=True)
        backend=self.backend_factory(image=image,context=self.context,memory_bytes=1024*1024*1024,
            workspace_bytes=128*1024*1024,tmpfs_bytes=64*1024*1024,network='none')
        result=dict(status='invalid_env',receipt=None,cleanup_ok=False,runner_hash=RUNNER_HASH)
        try:
            await backend.start(files)
            probe = ('import json,sys;\n'
                     'try:\n import importlib.metadata as m\n'
                     'except ImportError:\n import importlib_metadata as m\n'
                     'print(json.dumps({"python":sys.version,"packages":{d.metadata["Name"]:d.version for d in m.distributions()}}))')
            environment=await backend._ok('exec',backend.name,'/usr/local/bin/python','-I','-B','-c',probe,limit=256*1024)
            result['environment']=json.loads(environment)
            frozen=await backend._ok('exec',backend.name,'/usr/local/bin/python','-I','-S','-c',
                "from pathlib import Path; print(Path('/opt/grader-environment.txt').read_text())",limit=256*1024)
            result['pip_freeze']=frozen.decode('utf-8')
            request=ExecutionRequest(argv=['/usr/local/bin/python','-I','-B','-c',RUNNER],
                stdin_bytes=json.dumps(dict(test_paths=list(test_paths),python_paths=list(python_paths),collect_only=collect_only)).encode(),
                env={'PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1','PYTHONDONTWRITEBYTECODE':'1'},
                deadline_mono=time.monotonic()+timeout,
                quotas=OutputQuotas(memory_per_stream_bytes=512*1024,artifact_per_tool_bytes=0))
            execution=await backend.execute(request)
            result['execution']=dict(status=execution.status.value,exit_code=execution.exit_code,error_kind=execution.error_kind,
                stdout=execution.stdout.text_preview,stderr=execution.stderr.text_preview,truncated=execution.truncated,
                elapsed_ms=execution.duration_ms)
            if backend.active and execution.status in (ExecutionStatus.SUCCEEDED,ExecutionStatus.FAILED):
                retrieve = "from pathlib import Path; import sys; p=Path('/tmp/grader-receipt.json'); assert p.is_file() and not p.is_symlink() and p.stat().st_size<=2097152; sys.stdout.buffer.write(p.read_bytes())"
                try:
                    encoded=await backend._ok('exec',backend.name,'/usr/local/bin/python','-I','-S','-c',retrieve,limit=2*1024*1024)
                    result['receipt']=json.loads(encoded)
                except Exception: result['receipt_error']='missing_or_invalid_receipt'
                # Independent Python process reads the frozen inputs after test execution.
                checker="import hashlib,json,pathlib,sys; out={};\nfor n in json.load(sys.stdin):\n p=pathlib.Path('/workspace')/n; out[n]=hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() and not p.is_symlink() else None\nprint(json.dumps(out))"
                actual=json.loads(await backend._ok('exec','-i',backend.name,'/usr/local/bin/python','-I','-S','-c',checker,
                    data=json.dumps(list(files)).encode(),limit=1024*1024))
                result['input_changes_during_tests']=[n for n,v in files.items() if actual.get(n)!=hashlib.sha256(v).hexdigest()]
                result['integrity_verified']=True
                result['status']='executed'
        except Exception as exc:
            result['error_kind']=type(exc).__name__
            result['reason']=str(exc)[:1000]
        finally:
            cleanup=asyncio.create_task(backend.close())
            try: await asyncio.shield(cleanup)
            except asyncio.CancelledError:
                await cleanup
                raise
            result.update(cleanup_ok=backend.cleanup_ok,capabilities=backend.capabilities,lifecycle=backend.lifecycle)
        return result

    async def collect(self,base,*,image,test_paths,python_paths,overlay=None):
        files={**validate_files(base),**validate_files(overlay or {})}
        result=await self.execute(files,image=image,test_paths=test_paths,python_paths=python_paths,collect_only=True,timeout=120)
        receipt=result.get('receipt') or {}
        ids=receipt.get('collected',[])
        execution=result.get('execution') or {}
        ready=(result.get('status')=='executed' and result.get('integrity_verified') is True and
            execution.get('status')=='succeeded' and execution.get('exit_code')==0 and
            result['cleanup_ok'] and receipt.get('schema')=='repo.pytest.receipt.v1' and
            receipt.get('complete') is True and receipt.get('exit_code')==0 and ids and
            len(ids)==len(set(ids)) and not receipt.get('collection_errors') and
            not result.get('input_changes_during_tests') and not (result.get('execution') or {}).get('truncated'))
        result['status']='ready' if ready else 'invalid_env'
        return result

    async def evaluate(self,base,candidate,spec:RepositorySpec):
        started=time.monotonic()
        spec=RepositorySpec.from_mapping(asdict(spec))
        result=dict(task_id=spec.task_id,status='invalid_env',collected=len(spec.expected_nodeids),passed=0,failed=0,
            skipped=0,manifest=spec.manifest(),cases=[],changed_paths=[],reason=None)
        try:
            base=validate_files(base)
            if tree_hash(base)!=spec.base_hash: raise ValueError('base hash mismatch')
            if candidate is None: raise ValueError('candidate snapshot missing')
            candidate=validate_files(candidate)
            changed=sorted(n for n in base.keys()|candidate.keys() if base.get(n)!=candidate.get(n))
            result['changed_paths']=changed
            result['manifest']['candidate_hash']=tree_hash(candidate)
            if set(changed)-set(spec.editable_paths):
                result.update(status='fail',reason='protected_or_unassigned_path_changed')
                return result
            files={**candidate,**decode_overlay(spec.test_overlay)}
            evidence=await self.execute(files,image=spec.image,test_paths=spec.test_paths,python_paths=spec.python_paths,timeout=spec.timeout_seconds)
            result['evidence']=evidence
            if not evidence['cleanup_ok']: result['reason']='cleanup_failed'; return result
            execution=evidence.get('execution') or {}
            if execution.get('status') not in ('succeeded','failed'):
                result['reason']=execution.get('error_kind') or evidence.get('error_kind') or 'execution_unavailable'; return result
            if evidence.get('status')!='executed' or evidence.get('integrity_verified') is not True:
                result['reason']='input_integrity_check_unavailable'; return result
            if execution.get('truncated'): result['reason']='output_truncated'; return result
            if evidence.get('input_changes_during_tests'):
                result.update(status='fail',reason='frozen_input_changed_during_tests'); return result
            outcomes,error=classify_receipt(evidence.get('receipt'),spec.expected_nodeids)
            if error: result['reason']=error; return result
            if execution.get('exit_code')!=evidence['receipt']['exit_code']:
                result['reason']='process_receipt_exit_mismatch'; return result
            for node in spec.expected_nodeids:
                status=outcomes[node]
                satisfied=status=='passed' or spec.allowed_nonpass.get(node)==status
                result['cases'].append(dict(nodeid=node,outcome=status,required=node not in spec.allowed_nonpass,satisfied=satisfied))
            result['passed']=sum(v=='passed' for v in outcomes.values())
            result['skipped']=sum(v in ('skipped','xfailed') for v in outcomes.values())
            result['failed']=sum(not c['satisfied'] for c in result['cases'])
            result['regression_passed']=sum(outcomes[n]=='passed' for n in spec.baseline_passed)
            result['regression_assigned']=len(spec.baseline_passed)
            result['status']='pass' if not result['failed'] else ('partial' if result['passed'] else 'fail')
        except (ValueError,TypeError) as exc: result['reason']=str(exc)[:1000]
        finally: result['duration_ms']=(time.monotonic()-started)*1000
        return result
