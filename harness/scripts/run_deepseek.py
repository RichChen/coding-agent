#!/usr/bin/env python3
"""Paid, explicit opt-in end-to-end demo. Downloads a pinned public module slice."""
import argparse
import asyncio
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.eval.contracts import canonical_hash
from src.eval.deepseek_demo import prepare, usage_report, candidate_diff
from src.eval.grader import IndependentGrader, save_json
from src.eval.h3_runner import run_h3
from src.harness.factory import build_agent, load_config
from src.tracing.store import utc_now


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, help="New directory; never overwrites a previous attempt")
    parser.add_argument("--config", default="configs/deepseek.yaml")
    parser.add_argument("--source-dir", type=Path, help="Optional original source copy; hardcoded upstream SHA256 must match")
    parser.add_argument("--allow-paid", action="store_true", help="Required explicit API spending opt-in")
    args = parser.parse_args()
    if not args.allow_paid:
        parser.error("real API calls require --allow-paid")
    config = load_config(args.config)
    if not config["llm"]["api_key"]:
        parser.error("LLM_API_KEY is not configured")
    if config["llm"]["base_url"] != "https://api.deepseek.com/v1" or config["llm"]["model"] not in ("deepseek-flash", "deepseek-v4-pro"):
        parser.error("this demo requires the verified official DeepSeek endpoint/model")
    if config["llm"]["thinking"] != "disabled":
        parser.error("this demo requires explicit non-thinking mode")
    output = Path(args.output_dir).resolve()
    base, task, spec = await prepare(output, args.source_dir)
    grader = IndependentGrader(context=config["policy"]["command"]["docker_context"])
    baseline = await grader.evaluate(base, base, spec)
    save_json(output / "baseline-evaluation.json", baseline.to_dict())
    print(f"baseline: {baseline.status} {baseline.passed}/{baseline.collected}", flush=True)
    if baseline.status not in ("fail", "partial") or baseline.failed == 0:
        raise RuntimeError("baseline must reproduce the defect in a working grader before spending")
    # Persist only allowlisted nonsecret configuration and the effective config hash.
    save_json(output / "provider.json", dict(provider="DeepSeek", model=config["llm"]["model"],
              endpoint=config["llm"]["base_url"], thinking="disabled", streaming=config["tracing"]["llm_stream_events"],
              context=config["runtime"]["context"], max_output_tokens=config["llm"]["max_tokens"],
              started_at=utc_now(), config_hash=canonical_hash(config)))
    agent = build_agent(config, output / "seed")
    try:
        result = await run_h3(agent, task, spec, output / "run", config_hash=canonical_hash(config))
    finally:
        await agent.llm.aclose()
    run_path = output / "run" / "run-result.json"
    if run_path.exists():
        run = json.loads(run_path.read_text(encoding="utf-8"))
        usage = usage_report(run["llm_attempts"], config["llm"]["model"])
        save_json(output / "usage.json", usage)
        print(json.dumps(usage, ensure_ascii=False), flush=True)
    if agent.execution_backend.snapshot is not None:
        (output / "candidate.patch").write_text(candidate_diff(base, agent.execution_backend.snapshot), encoding="utf-8")
    save_json(output / "completion.json", dict(finished_at=utc_now(), evaluation_status=result.status))
    print(f"candidate: {result.status} {result.passed}/{result.collected}", flush=True)
    if not result.success:
        raise SystemExit(2)


if __name__ == "__main__":
    asyncio.run(main())
