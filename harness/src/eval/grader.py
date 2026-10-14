"""Host-owned black-box grading; no candidate-controlled discovery or verdicts.

Each fixed case gets a fresh container and only its input; expected values stay
on the host. This is not an arbitrary pytest/JUnit adapter.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from src.eval.contracts import EvaluationSpec, canonical_hash
from src.execution.base import ExecutionRequest, ExecutionStatus, OutputQuotas
from src.execution.docker import DockerExecutionBackend, validate_files
from src.tracing.artifacts import atomic_replace


RUNNER = '''import importlib.util,json,sys
sys.dont_write_bytecode=True
p=json.load(sys.stdin)
s=importlib.util.spec_from_file_location("candidate", "/workspace/"+p["module_path"])
m=importlib.util.module_from_spec(s)
s.loader.exec_module(m)
value=getattr(m,p["function"])(*p["args"])
print(json.dumps(value,sort_keys=True,ensure_ascii=True,separators=(",",":"),allow_nan=False))
'''


def tree_hash(files):
    validate_files(files)
    return canonical_hash({k: hashlib.sha256(v).hexdigest() for k, v in files.items()})


def encode_snapshot(files):
    return {k: base64.b64encode(v).decode('ascii') for k, v in validate_files(files).items()}


def decode_snapshot(value):
    return validate_files({k: base64.b64decode(v, validate=True) for k, v in value.items()})


@dataclass
class EvaluationResult:
    task_id: str
    status: str = "invalid_env"
    collected: int = 0
    passed: int = 0
    failed: int = 0
    duration_ms: float = 0.0
    reason: str | None = None
    manifest: dict = field(default_factory=dict)
    cases: list = field(default_factory=list)
    changed_paths: list = field(default_factory=list)

    @property
    def success(self):
        return self.status == "pass"

    def to_dict(self):
        return asdict(self)


class IndependentGrader:
    def __init__(self, *, context="desktop-linux", backend_factory=DockerExecutionBackend):
        self.context, self.backend_factory = context, backend_factory

    async def evaluate(self, base: dict[str, bytes], candidate: dict[str, bytes] | None,
                       spec: EvaluationSpec) -> EvaluationResult:
        spec = EvaluationSpec.from_mapping(asdict(spec))
        started = time.monotonic()
        result = EvaluationResult(spec.task_id, collected=len(spec.cases), manifest=spec.manifest())
        result.manifest['runner_hash'] = hashlib.sha256(RUNNER.encode()).hexdigest()
        try:
            base = dict(validate_files(base))
            if tree_hash(base) != spec.base_hash:
                raise ValueError("base hash differs from frozen specification")
            if candidate is None:
                raise ValueError("no candidate snapshot from terminated agent")
            candidate = dict(validate_files(candidate))
            result.manifest['candidate_hash'] = tree_hash(candidate)
            result.changed_paths = sorted(k for k in base.keys() | candidate.keys() if base.get(k) != candidate.get(k))
            forbidden = set(result.changed_paths) - set(spec.editable_paths)
            if forbidden:
                result.status, result.reason = 'fail', 'protected or unassigned paths changed: ' + ', '.join(sorted(forbidden))
                return result
            rebuilt = dict(base)
            for name in spec.editable_paths:
                if name in candidate: rebuilt[name] = candidate[name]
                else: rebuilt.pop(name, None)
            for case in spec.cases:
                backend = self.backend_factory(image=spec.image, context=self.context)
                record = dict(case_id=case.case_id, status='invalid_env')
                try:
                    await backend.start(rebuilt)
                    execution = await backend.execute(ExecutionRequest(
                        argv=['/usr/local/bin/python', '-I', '-S', '-c', RUNNER], env={},
                        stdin_bytes=json.dumps(dict(module_path=case.module_path, function=case.function, args=case.args)).encode(),
                        deadline_mono=time.monotonic()+spec.timeout_seconds,
                        quotas=OutputQuotas(memory_per_stream_bytes=65536, artifact_per_tool_bytes=0)))
                    expected = json.dumps(case.expected, sort_keys=True, ensure_ascii=True, separators=(',', ':'), allow_nan=False)+'\n'
                    passed = (execution.status == ExecutionStatus.SUCCEEDED and not execution.truncated
                              and execution.stdout.text_preview == expected)
                    record.update(status='pass' if passed else 'fail', execution=execution.status.value,
                                  exit_code=execution.exit_code, error_kind=execution.error_kind,
                                  stdout=execution.stdout.text_preview, stderr=execution.stderr.text_preview,
                                  bytes_seen=execution.bytes_seen, truncated=execution.truncated)
                except Exception as exc:
                    record['error'] = str(exc)[:1000]
                finally:
                    cleanup = asyncio.create_task(backend.close())
                    try:
                        await asyncio.shield(cleanup)
                    except asyncio.CancelledError:
                        await cleanup
                        raise
                    record.update(cleanup_ok=backend.cleanup_ok, lifecycle=backend.lifecycle, capabilities=backend.capabilities)
                    if not backend.cleanup_ok:
                        record.update(status='invalid_env', error='cleanup_failed')
                result.cases.append(record)
                if record['status'] == 'invalid_env':
                    result.reason = record.get('error', 'grader unavailable')
                    break
            result.passed = sum(c['status'] == 'pass' for c in result.cases)
            result.failed = sum(c['status'] == 'fail' for c in result.cases)
            if len(result.cases) != result.collected or any(c['status'] == 'invalid_env' for c in result.cases):
                result.status = 'invalid_env'
            else:
                result.status = 'pass' if result.passed == result.collected else ('partial' if result.passed else 'fail')
        except (ValueError, TypeError) as exc:
            result.reason = str(exc)
        finally:
            result.duration_ms = (time.monotonic()-started)*1000
        return result


def save_json(path, value):
    atomic_replace(Path(path), json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False).encode('utf-8'))


def report_text(manifest, results):
    assigned = manifest['assigned_task_ids']
    if not assigned or len(set(assigned)) != len(assigned):
        raise ValueError('nonempty unique assigned denominator required')
    by_id = {r['task_id']: r for r in results}
    if len(by_id) != len(results) or set(by_id) - set(assigned):
        raise ValueError('duplicate or unassigned evaluation results')
    passed = sum(by_id.get(t, {}).get('status') == 'pass' for t in assigned)
    rows = ['# H3 evaluation', '', f'Assigned: {len(assigned)}; passed: {passed}; success rate: {passed/len(assigned):.2%}.',
            'Environment failures and missing results remain in the denominator.', '',
            '| Task | Status | Passed / assigned cases |', '| --- | --- | --- |']
    for task in assigned:
        r = by_id.get(task, {})
        safe_task = json.dumps(task, ensure_ascii=True).replace('|', '\\|')
        rows.append(f"| {safe_task} | {r.get('status', 'unverified')} | {r.get('passed', 0)} / {r.get('collected', '?')} |")
    rows.extend(['', 'Model tokens/cost: unknown unless separately recorded; no model self-report is used for grading.', ''])
    return '\n'.join(rows)


def save_bundle(directory, manifest, results):
    directory = Path(directory)
    results = [r.to_dict() if isinstance(r, EvaluationResult) else r for r in results]
    manifest = dict(manifest, schema='h3.bundle.v1', results_hash=canonical_hash(results))
    report = report_text(manifest, results)
    directory.mkdir(parents=True, exist_ok=False)
    save_json(directory/'manifest.json', manifest)
    save_json(directory/'results.json', results)
    atomic_replace(directory/'report.md', report.encode('utf-8'))


def regenerate_report(directory):
    directory = Path(directory)
    manifest = json.loads((directory/'manifest.json').read_text(encoding='utf-8'))
    results = json.loads((directory/'results.json').read_text(encoding='utf-8'))
    if canonical_hash(results) != manifest['results_hash']:
        raise ValueError('results hash mismatch')
    atomic_replace(directory/'report.md', report_text(manifest, results).encode('utf-8'))
