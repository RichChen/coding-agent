import asyncio
import base64
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.run_a5_real import base_and_overlay, injection_refs, load_events, sha_bytes
from src.eval.repo_grader import RepositoryGrader


async def main():
    base, spec = base_and_overlay()
    root = Path(".tmp-a5-canary-real-20260924-v7")
    for directory in root.iterdir():
        delta_path = directory / "candidate-delta.json"
        if not delta_path.is_file():
            continue
        delta = json.loads(delta_path.read_text())
        candidate = dict(base)
        for name in delta.get("deleted", []):
            candidate.pop(name, None)
        for name, change in delta.get("changed", {}).items():
            candidate[name] = base64.b64decode(change["content"])
        result = await RepositoryGrader(context="desktop-linux").evaluate(base, candidate, spec)
        (directory / "grader-result.json").write_text(json.dumps(result, indent=2))
        receipt_path = directory / "receipt.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["injection_receipt_refs"] = injection_refs(load_events(directory / "events.jsonl"))
        receipt["grader_receipt_ref"] = sha_bytes((directory / "grader-result.json").read_bytes())
        receipt["grader_status"] = result["status"]
        receipt["failure_reason"] = result["reason"] or ("grader_" + result["status"] if result["status"] != "pass" else None)
        receipt_path.write_text(json.dumps(receipt, indent=2))
        print(directory.name, result["status"], result["passed"], result["failed"], result["reason"])


if __name__ == "__main__":
    asyncio.run(main())
