"""Fourteen dev tasks, three repeats each, under b0-v1. Real model calls."""
import asyncio
import json
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_swe_task import load_yaml, run_task

CAP = Decimal("38.000")


async def main():
    manifest = load_yaml(ROOT / "configs/sprint/dev-tasks.yaml")
    profile = ROOT / "configs/sprint/b0-v1.yaml"
    spent = Decimal("0.000")
    for task in manifest["tasks"]:
        for repeat in (1, 2, 3):
            out = ROOT / "runs/sprint3-b0" / task["id"] / f"r{repeat}"
            summary_path = out / "summary.json"
            if summary_path.is_file():
                row = json.loads(summary_path.read_text(encoding="utf-8"))
                spent += Decimal(str(row.get("cost_cny") or "0"))
                print(json.dumps({"skip": task["id"], "repeat": repeat, "spent": str(spent)}), flush=True)
                continue
            if spent >= CAP:
                print(json.dumps({"stop": "near_cap", "spent": str(spent)}), flush=True)
                return
            summary = await run_task(task, profile, out, mock=False)
            spent += Decimal(str(summary.get("cost_cny") or "0"))
            print(json.dumps({
                "task": task["id"], "repeat": repeat, "solved": summary.get("solved"),
                "cost_cny": summary.get("cost_cny"), "spent": str(spent),
                "stop_reason": summary.get("stop_reason"),
            }, ensure_ascii=False), flush=True)
    print(json.dumps({"done": True, "spent": str(spent)}), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
