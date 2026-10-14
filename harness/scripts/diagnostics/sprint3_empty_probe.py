"""One empty-delta grade, printing extension-import diagnostics. No model calls."""
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_swe_task import grader_spec, load_yaml
from src.eval.image_grader import ImageGrader


async def main():
    task_id = sys.argv[1]
    manifest = load_yaml(ROOT / "configs/sprint/dev-tasks.yaml")
    task = next(item for item in manifest["tasks"] if item["id"] == task_id)
    spec = grader_spec(task)
    f2p = [node for node in spec.expected_nodeids if node not in spec.baseline_passed]
    result = await ImageGrader().evaluate(
        image=spec.image, delta={"changed": {}, "deleted": []}, test_overlay=spec.test_overlay,
        f2p=f2p[:1], p2p=list(spec.baseline_passed)[:1], django=False, timeout=180,
    )
    err = (result.get("collection_errors") or [""])[0]
    print(json.dumps({
        "collected": result.get("collected_count"),
        "exit": result.get("exit_code"),
        "f2p": result.get("f2p_passed"),
        "p2p": result.get("p2p_passed"),
        "error": err[:400] if isinstance(err, str) else str(err)[:400],
    }))


if __name__ == "__main__":
    asyncio.run(main())
