"""Grade a saved delta against one F2P and one P2P node. No model calls."""
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.regrade_saved_delta import normalize_delta
from scripts.run_swe_task import grader_spec, load_yaml
from src.eval.image_grader import ImageGrader


async def main():
    run_dir = Path(sys.argv[1])
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    manifest = load_yaml(ROOT / "configs/sprint/dev-tasks.yaml")
    task = next(item for item in manifest["tasks"] if item["id"] == summary["task_id"])
    spec = grader_spec(task)
    f2p = [node for node in spec.expected_nodeids if node not in spec.baseline_passed]
    delta = normalize_delta(json.loads((run_dir / "candidate-delta.json").read_text(encoding="utf-8")))
    result = await ImageGrader().evaluate(
        image=spec.image, delta=delta, test_overlay=spec.test_overlay,
        f2p=f2p[:1], p2p=list(spec.baseline_passed)[:1], timeout=180,
    )
    err = (result.get("collection_errors") or [""])[0]
    print(json.dumps({
        "collected": result.get("collected_count"),
        "exit": result.get("exit_code"),
        "f2p": result.get("f2p_passed"),
        "p2p": result.get("p2p_passed"),
        "nodes": result.get("debug_nodes"),
        "stat": result.get("debug_stat"),
        "reason": result.get("reason"),
        "error": (err if isinstance(err, str) else str(err))[:300],
    }, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
