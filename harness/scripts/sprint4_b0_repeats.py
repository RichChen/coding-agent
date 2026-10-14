"""Fourteen dev tasks, three repeats, b0-v2 clean images. Stops on isolation failure."""
import asyncio
import json
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_swe_task import load_yaml, run_task

CAP = Decimal("19.000")


async def main():
    manifest = load_yaml(ROOT / "configs/sprint/dev-tasks.yaml")
    profile = ROOT / "configs/sprint/b0-v2.yaml"
    spent = Decimal("0.000")
    for task in manifest["tasks"]:
        clean = json.loads((ROOT / "docs/sprint/clean-images" / (task["id"] + ".json")).read_text(encoding="utf-8"))
        if not clean.get("answer_isolation_pass"):
            print(json.dumps({"stop": "answer_isolation_failed", "task": task["id"]}), flush=True)
            return
        for repeat in (1, 2, 3):
            out = ROOT / "runs/sprint4-b0-v2" / task["id"] / f"r{repeat}"
            summary_path = out / "summary.json"
            if summary_path.is_file():
                row = json.loads(summary_path.read_text(encoding="utf-8"))
                spent += Decimal(str(row.get("cost_cny") or "0"))
                continue
            if spent >= CAP:
                print(json.dumps({"stop": "near_cap", "spent": str(spent)}), flush=True)
                return
            summary = await run_task(task, profile, out, mock=False)
            if summary.get("answer_isolation_pass") is False:
                print(json.dumps({"stop": "answer_isolation_failed", "task": task["id"]}), flush=True)
                return
            spent += Decimal(str(summary.get("cost_cny") or "0"))
            print(json.dumps({
                "task": task["id"], "repeat": repeat, "solved": summary.get("solved"),
                "cost_cny": summary.get("cost_cny"), "spent": str(spent),
                "stop_reason": summary.get("stop_reason"),
                "answer_isolation_pass": summary.get("answer_isolation_pass"),
            }, ensure_ascii=False), flush=True)
    print(json.dumps({"done": True, "spent": str(spent)}), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
