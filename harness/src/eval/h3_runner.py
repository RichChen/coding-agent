"""Public-only agent boundary followed by an independent, private evaluation."""
from pathlib import Path
import json
import platform
import subprocess
import sys

from src.eval.contracts import PublicTask, EvaluationSpec, canonical_hash
from src.eval.grader import (IndependentGrader, EvaluationResult, encode_snapshot,
                             tree_hash, save_json, save_bundle)
from src.execution.docker import read_workspace
from src.runtime.session import RunSession, compatibility, plain, source_fingerprint


async def run_h3(agent, task: PublicTask, spec: EvaluationSpec, output_dir: Path, *, config_hash: str):
    task = PublicTask.from_mapping(task.agent_payload())
    backend = agent.execution_backend
    if backend is None or task.workspace_profile != 'docker_linux':
        raise ValueError('H3 requires docker_linux for every tool')
    if task.task_id != spec.task_id:
        raise ValueError('public/private task identity mismatch')
    configured_budget = {k: getattr(agent.budget, k) for k in ('max_steps', 'total_timeout_seconds', 'step_timeout_seconds')}
    configured_budget.update({k: getattr(agent.model_ledger, k, None) for k in ('max_model_calls', 'max_tokens', 'max_cost_usd')})
    if any(k not in configured_budget or configured_budget[k] != v for k, v in task.budget.items()):
        raise ValueError('public budget must agree with enforced configuration')
    base = read_workspace(agent.sandbox.workspace_root)
    if tree_hash(base) != spec.base_hash:
        raise ValueError('public seed differs from frozen evaluation base')
    output_dir = Path(output_dir).resolve()
    seed_dir = Path(agent.sandbox.workspace_root).resolve()
    if output_dir.is_relative_to(seed_dir) or seed_dir.is_relative_to(output_dir):
        raise ValueError('run evidence must be outside the public seed')
    output_dir.mkdir(parents=True, exist_ok=False)
    backend.seed_files = base
    agent.public_repo_revision = task.base_revision or spec.base_hash
    save_json(output_dir/'public-task.json', task.agent_payload())
    save_json(output_dir/'base.json', encode_snapshot(base))
    repository = Path(__file__).resolve().parents[2]
    code_id = source_fingerprint(repository)
    try:
        head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=repository, capture_output=True, text=True, timeout=3)
        commit = head.stdout.strip() if head.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        commit = None
    manifest = dict(assigned_task_ids=[task.task_id], public_task_hash=canonical_hash(task.agent_payload()),
                    config_hash=config_hash, code_hash=code_id, base_hash=spec.base_hash,
                    private_spec_hash=spec.manifest()['private_spec_hash'], model=agent.llm.model,
                    context=backend.context, agent_capabilities=backend.capabilities, enforced_budget=configured_budget,
                    python=sys.version, host_platform=platform.platform(), git_commit=commit,
                    code_hash_includes_uncommitted_source=True)
    from src.runtime.window import WindowPolicyHooks
    if isinstance(agent.hooks, WindowPolicyHooks):
        manifest['context_policy'] = agent.hooks.fingerprint()
    save_json(output_dir/'manifest.json', manifest)
    expected = compatibility(workspace=seed_dir, code_id=code_id, config={'hash': config_hash}, backend=backend.capabilities)
    try:
        with RunSession.create(output_dir/'session', task_id=task.task_id, expected=expected,
                               timeout_seconds=agent.budget.total_timeout_seconds) as session:
            run = await session.run(agent, json.dumps(task.agent_payload(), ensure_ascii=False))
            save_json(output_dir/'run-result.json', plain(run))
            session.store.export_jsonl(output_dir/'events.jsonl')
            # Terminal is journaled only after cleanup and candidate capture complete.
            if backend.cleanup_ok and backend.snapshot is not None:
                save_json(output_dir/'candidate.json', encode_snapshot(backend.snapshot))
                evaluation = await IndependentGrader(context=backend.context).evaluate(base, backend.snapshot, spec)
            else:
                evaluation = EvaluationResult(task.task_id, collected=len(spec.cases), reason='agent cleanup/snapshot unavailable')
    except Exception as exc:
        evaluation = EvaluationResult(task.task_id, collected=len(spec.cases), reason=str(exc)[:1000])
    save_json(output_dir/'evaluation-result.json', evaluation.to_dict())
    save_bundle(output_dir/'evaluation', manifest, [evaluation])
    return evaluation
