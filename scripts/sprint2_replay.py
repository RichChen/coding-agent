"""Replay recorded edit tool calls onto the base tree and grade them. No model calls."""
import asyncio
import base64
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.sprint2_calibrate import spec_ids
from src.eval.image_grader import ImageGrader

EDIT = {"search_replace", "edit_file", "write_file"}


def apply_events(events: list[dict], files: dict[str, bytes]) -> list[str]:
    changed = []
    for event in events:
        if event.get("event_type") != "tool.intent":
            continue
        payload = event.get("payload") or {}
        name = payload.get("name")
        if name not in EDIT:
            continue
        args = payload.get("arguments") or {}
        path = args.get("path")
        if not isinstance(path, str):
            continue
        current = files.get(path, b"").decode("utf-8", "replace")
        if name == "write_file":
            updated = args.get("content") or ""
        elif name == "search_replace":
            old, new = args.get("search"), args.get("replace")
            if not isinstance(old, str) or old not in current:
                continue
            updated = current.replace(old, new if isinstance(new, str) else "", 1)
        else:
            old, new = args.get("old_string"), args.get("new_string")
            if not isinstance(old, str) or old not in current:
                continue
            updated = current.replace(old, new if isinstance(new, str) else "", 1)
        files[path] = updated.encode("utf-8")
        changed.append(path)
    return changed


async def main():
    task_id = sys.argv[1]
    events_path = Path(sys.argv[2])
    task_dir = Path(sys.argv[3])
    events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    files = {}
    original = task_dir / "staging/original"
    for path in original.rglob("*"):
        if path.is_file() and not path.is_symlink() and ".git" not in path.parts:
            files[path.relative_to(original).as_posix()] = path.read_bytes()
    changed = apply_events(events, files)
    receipt, family, f2p, p2p, overlay = spec_ids(task_dir)
    delta = {"changed": {name: base64.b64encode(files[name]).decode("ascii") for name in sorted(set(changed)) if name in files}, "deleted": []}
    result = await ImageGrader().evaluate(
        image=receipt["baseline_image_digest"], delta=delta, test_overlay=overlay,
        f2p=f2p, p2p=p2p, django=family == "django", timeout=600,
    )
    print(json.dumps({
        "id": task_id,
        "changed": sorted(set(changed)),
        "solved": result.get("solved"),
        "f2p_passed": result.get("f2p_passed"),
        "f2p_total": result.get("f2p_total"),
        "p2p_passed": result.get("p2p_passed"),
        "p2p_total": result.get("p2p_total"),
        "reason": result.get("reason"),
        "status": result.get("status"),
    }), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
