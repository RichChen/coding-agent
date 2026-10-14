import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.sprint2_calibrate import gold_delta, spec_ids
from src.eval.image_grader import ImageGrader


async def main():
    task = Path(sys.argv[1])
    receipt, family, f2p, p2p, overlay = spec_ids(task)
    paths = receipt["private_source_binding"].get("gold_patch_paths") or []
    result = await ImageGrader().evaluate(
        image=receipt["baseline_image_digest"],
        delta=gold_delta(task, paths),
        test_overlay=overlay,
        f2p=f2p,
        p2p=p2p[:3],
        django=family == "django",
        timeout=300,
    )
    print(json.dumps({
        "f2p": [case for case in result["cases"] if case["nodeid"] in f2p],
        "p2p_sample": [case for case in result["cases"] if case["nodeid"] in p2p[:3]],
        "reason": result.get("reason"),
        "status": result.get("status"),
    }, ensure_ascii=True))


if __name__ == "__main__":
    asyncio.run(main())
