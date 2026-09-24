#!/usr/bin/env python3
"""One context-policy summary demo; no main model, tools, grader or performance claim.

Defaults to fixture (no key/network). LLM mode requires an explicit model, USD
ceiling, conservative price table/version and --allow-paid. Never overwrites runs.
"""
import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.demo_h4 import transcript
from src.config.schema import HarnessConfig
from src.eval.grader import save_json
from src.harness.factory import build_agent, load_config
from src.runtime.loop import AgentRunResult, FailureReason
from src.runtime.session import RunSession, compatibility, plain, source_fingerprint, runtime_fingerprint
from src.runtime.summary import summary_totals
from src.runtime.window import ContextWindowError, view_hash
from src.tracing.artifacts import atomic_replace


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output-dir', required=True)
    p.add_argument('--provider', choices=['fixture', 'llm'], default='fixture')
    p.add_argument('--config', help='Existing host LLM config; credentials loaded only by host factory')
    p.add_argument('--model', help='Explicit selected model; no implicit config model in paid mode')
    p.add_argument('--allow-paid', action='store_true')
    p.add_argument('--max-cost-usd', type=float)
    p.add_argument('--prompt-per-1k', type=float)
    p.add_argument('--completion-per-1k', type=float)
    p.add_argument('--price-version')
    return p


async def run_demo(args):
    paid = args.provider == 'llm'
    if paid and (not args.allow_paid or not args.config or not args.model or not args.price_version
                 or any(v is None for v in (args.max_cost_usd, args.prompt_per_1k, args.completion_per_1k))):
        raise ValueError('LLM mode requires --allow-paid --config --model --max-cost-usd '
                         '--prompt-per-1k --completion-per-1k --price-version')
    if paid:
        config = load_config(args.config)
        if not config['llm']['api_key']:
            raise ValueError('host LLM credentials unavailable')
        config['llm']['model'] = args.model
        if config['llm'].get('thinking') != 'disabled':
            raise ValueError('demo requires explicit thinking=disabled in the host config')
    else:
        config = dict(llm=dict(base_url='https://offline.invalid', api_key='', model='no-model'))
    config['llm']['max_tokens'] = 256  # Reserved next-view output; no main request is sent.
    config['runtime'] = dict(max_steps=1, total_timeout_seconds=60, step_timeout_seconds=60,
        context=dict(strategy='summary', max_tokens=6000, keep_recent_tool_results=1,
                     summary_provider=args.provider, summary_failure='reject', summary_max_calls=1,
                     summary_price_version=args.price_version or 'no_model_call'),
        budget=dict(max_model_calls=1, max_tokens=131072,
            max_cost_usd=args.max_cost_usd if paid else None,
            price_table=dict(prompt_per_1k=args.prompt_per_1k, completion_per_1k=args.completion_per_1k)
                if paid else None))
    config['tools'] = dict(enabled=[])
    config['policy'] = {}
    config['retry'] = dict(max_retries=0)
    config['tracing'] = {}
    config = HarnessConfig.model_validate(config).model_dump()
    directory = Path(args.output_dir).resolve()
    # Build and validate all budgets before creating evidence or issuing a request.
    agent = build_agent(config, directory/'public-workspace')
    directory.mkdir(parents=True, exist_ok=False)
    agent.sandbox.workspace_root.mkdir(exist_ok=False)
    raw = transcript()
    save_json(directory/'raw-messages.json', raw)
    code = source_fingerprint(Path(__file__).resolve().parents[1])
    manifest = dict(schema_version='r2-lite-1', demo='one-summary-context-policy-only',
        provider=args.provider, model=args.model if paid else None, paid_authorized=paid,
        raw_message_hash=view_hash(raw), code_hash=code, context_policy=agent.hooks.fingerprint(),
        budget=config['runtime']['budget'], total_timeout_seconds=60,
        main_model_calls=0, tool_calls=0, private_evaluation=False,
        limitation='Synthetic public transcript; no coding-agent success-rate evidence')
    save_json(directory/'manifest.json', manifest)
    expected = compatibility(workspace=agent.sandbox.workspace_root, code_id=code,
        config=manifest, backend='context-only-no-tools')
    events = []
    started = time.monotonic()
    try:
        with RunSession.create(directory/'session', task_id='true-summary-demo', expected=expected,
                               timeout_seconds=60) as session:
            agent.session = session
            agent.deadline.set_run(60)
            agent.deadline.begin_step(60)
            session.append('runtime.bound', dict(hash=runtime_fingerprint(agent)))
            session.save_loop(dict(messages=raw, step_number=0))
            error = None
            try:
                view = await agent._model_view(raw, [], raw[1]['content'], 'true-summary-demo', 0, events)
                save_json(directory/'view.json', view)
            except Exception as exc:
                # Classification only: provider exceptions may contain credentials.
                error = exc.kind if isinstance(exc, ContextWindowError) else type(exc).__name__
            summary = summary_totals(agent.hooks.state)
            succeeded = error is None and bool(agent.hooks.state['summaries'])
            result = AgentRunResult(task_id='true-summary-demo', success=succeeded,
                failure_reason=FailureReason.NONE if succeeded else FailureReason.CONTEXT_INVALID,
                termination_kind='context_view_ready' if succeeded else error or 'no_summary_generated',
                total_elapsed_ms=(time.monotonic()-started)*1000,
                total_tokens=summary['known_total_tokens'], model_budget=agent.model_ledger.snapshot(),
                context_events=events, summary=summary)
            session.finish(result)
            session.store.export_jsonl(directory/'events.jsonl')
            save_json(directory/'run-result.json', plain(result))
            save_json(directory/'summary-state.json', agent.hooks.state)
        replay = RunSession.replay(directory/'session')
        save_json(directory/'replay.json', dict(raw_message_hash=view_hash(replay.messages),
            summary_state=replay.plugin_state.get('h4'), budget=replay.budget,
            replay_external_calls=0, terminal=replay.terminal))
        report = '\n'.join(['# R2-lite summary mechanism demo', '',
            f"Provider: {args.provider}; status: {result.termination_kind}",
            f"Summary model calls: {summary['model_calls']}; main model calls: 0; tools: 0",
            f"Known tokens: {summary['known_total_tokens']}; unknown usage calls: {summary['unknown_usage_calls']}",
            f"Estimated USD: {summary['estimated_cost_usd']}; budget commitment USD: {summary['cost_committed_usd']}",
            '', 'Source: raw-messages.json / session state.saved; records: summary-state.json / events.jsonl.',
            'Price-table estimates are not an account bill. Missing usage/cost remains unknown.',
            'Fixture success is not real LLM evidence. LLM success only verifies a context-policy function,',
            'not semantic faithfulness or improved coding-agent task success.', ''])
        atomic_replace(directory/'report.md', report.encode())
        print(report)
        return 0 if succeeded else 1
    finally:
        await agent.llm.aclose()


if __name__ == '__main__':
    args = parser().parse_args()
    try:
        raise SystemExit(asyncio.run(run_demo(args)))
    except ValueError as exc:
        parser().error(str(exc))
