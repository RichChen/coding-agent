"""One B2 smoke run per dev task. Stop before the sprint-5 model spend reaches 9 CNY."""
import asyncio
import json
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.run_swe_task import load_yaml, run_task  # noqa: E402

RERUN = Decimal("0.478")
STOP_AT = Decimal("9")
CARDS = ROOT.parent / "coding-agent" / "benchmarks" / "a5" / "memory-cards-v4.jsonl"
OUT = ROOT / "runs" / "sprint5-b2-smoke"


def smoke_spent() -> Decimal:
    total = Decimal("0")
    if not OUT.exists():
        return total
    for path in OUT.glob("*/summary.json"):
        row = json.loads(path.read_text(encoding="utf-8"))
        total += Decimal(str(row.get("cost_cny") or "0"))
    return total


async def main():
    print("estimate_cny", "4.9", "already_cny", str(RERUN + smoke_spent()), flush=True)
    manifest = load_yaml(ROOT / "configs/sprint/dev-tasks.yaml")
    profile = ROOT / "configs/sprint/b0-v2.yaml"
    for task in manifest["tasks"]:
        destination = OUT / task["id"]
        if (destination / "summary.json").is_file():
            continue
        if RERUN + smoke_spent() >= STOP_AT:
            print("stop_before", task["id"], str(RERUN + smoke_spent()), flush=True)
            return
        summary = await run_task(task, profile, destination, mock=False, variant="B2", cards_path=CARDS)
        memory = summary.get("memory") or {}
        print(json.dumps({
            "task_id": summary.get("task_id"),
            "solved": summary.get("solved"),
            "status": summary.get("status"),
            "cost_cny": summary.get("cost_cny"),
            "cards_before": memory.get("cards_before"),
            "cards_after": memory.get("cards_after"),
            "injected": [item.get("id") for item in memory.get("injected") or []],
            "sprint5_cny": str(RERUN + smoke_spent()),
        }, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
