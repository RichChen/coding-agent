#!/usr/bin/env python3
"""Run a public task in Docker, then privately grade its frozen candidate."""
import argparse
import asyncio
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.eval.contracts import PublicTask, EvaluationSpec, canonical_hash
from src.eval.h3_runner import run_h3
from src.harness.factory import build_agent, load_config


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--public-task', required=True)
    parser.add_argument('--private-spec', required=True, help='Outside public workspace')
    parser.add_argument('--workspace', required=True, help='Explicit public seed directory only')
    parser.add_argument('--output-dir', required=True, help='New evidence directory outside workspace')
    parser.add_argument('--config', default='configs/docker.yaml')
    args = parser.parse_args()
    workspace = Path(args.workspace).resolve(strict=True)
    private_path = Path(args.private_spec).resolve(strict=True)
    if private_path.is_relative_to(workspace): parser.error('private spec must be outside public seed')
    task = PublicTask.from_mapping(json.loads(Path(args.public_task).read_text(encoding='utf-8')))
    spec = EvaluationSpec.from_mapping(json.loads(private_path.read_text(encoding='utf-8')))
    config = load_config(args.config)
    agent = build_agent(config, workspace)
    try:
        result = await run_h3(agent, task, spec, Path(args.output_dir), config_hash=canonical_hash(config))
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        if not result.success: raise SystemExit(2)
    finally:
        await agent.llm.aclose()


if __name__ == '__main__':
    asyncio.run(main())
