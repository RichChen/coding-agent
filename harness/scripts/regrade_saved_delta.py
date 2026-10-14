"""Re-grade a saved candidate-delta.json with ImageGrader. No model calls. Does not overwrite grader-result.json."""
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_swe_task import grader_spec, load_yaml
from src.eval.image_grader import ImageGrader


def normalize_delta(raw: dict) -> dict:
    changed = {}
    for name, item in (raw.get("changed") or {}).items():
        changed[name] = item.get("content") if isinstance(item, dict) else item
    return {"changed": changed, "deleted": list(raw.get("deleted") or [])}


async def regrade(run_dir: Path, tasks_path: Path) -> dict:
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    manifest = load_yaml(tasks_path)
    task = next(item for item in manifest["tasks"] if item["id"] == summary["task_id"])
    spec = grader_spec(task)
    f2p = [node for node in spec.expected_nodeids if node not in spec.baseline_passed]
    delta = normalize_delta(json.loads((run_dir / "candidate-delta.json").read_text(encoding="utf-8")))
    result = await ImageGrader().evaluate(
        image=spec.image,
        delta=delta,
        test_overlay=spec.test_overlay,
        f2p=f2p,
        p2p=list(spec.baseline_passed),
        django=task.get("family") == "django",
        timeout=float(task.get("grader_timeout_seconds", 600)),
    )
    out = run_dir / "grader-result.regrade.json"
    out.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(json.dumps({
        "task_id": summary["task_id"],
        "solved": result.get("solved"),
        "status": result.get("status"),
        "f2p": [result.get("f2p_passed"), result.get("f2p_total")],
        "p2p": [result.get("p2p_passed"), result.get("p2p_total")],
        "collected_count": result.get("collected_count"),
        "exit_code": result.get("exit_code"),
        "runner_error": result.get("runner_error"),
        "collection_errors": (result.get("collection_errors") or [])[:2],
        "stderr_tail": (result.get("execution_stderr_tail") or "")[-500:],
    }, ensure_ascii=True), flush=True)
    return result


def main():
    tasks = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "configs/sprint/dev-tasks.yaml"
    asyncio.run(regrade(Path(sys.argv[1]), tasks if tasks.is_absolute() else ROOT / tasks))


if __name__ == "__main__":
    main()
