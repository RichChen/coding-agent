"""Rerun the invalidated sklearn-11281 r2. One real model run."""
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.run_swe_task import load_yaml, run_task


async def main():
    manifest = load_yaml(ROOT / "configs/sprint/dev-tasks.yaml")
    task = next(item for item in manifest["tasks"] if item["id"] == "scikit-learn__scikit-learn-11281")
    out = ROOT / "runs/sprint4-b0-v2/scikit-learn__scikit-learn-11281/r2"
    summary = await run_task(task, ROOT / "configs/sprint/b0-v2.yaml", out, mock=False)
    print(json.dumps({
        "solved": summary.get("solved"),
        "status": summary.get("status"),
        "cost_cny": summary.get("cost_cny"),
        "model_calls": summary.get("model_calls"),
        "stop_reason": summary.get("stop_reason"),
        "answer_isolation_pass": summary.get("answer_isolation_pass"),
    }, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
