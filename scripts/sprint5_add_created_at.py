"""Add repo and created_at from SWE-bench Verified onto the handoff. No model calls."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.handoff_sha import handoff_sha256


def main():
    from datasets import load_dataset
    rows = {row["instance_id"]: row for row in load_dataset("princeton-nlp/SWE-bench", split="test")}
    path = ROOT / "docs/sprint/memory-source-runs.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    document["schema"] = "sprint5.memory-source-runs.v2"
    missing = []
    for run in document["runs"]:
        row = rows.get(run["source_id"])
        if row is None:
            missing.append(run["source_id"])
            continue
        run["repo"] = row["repo"]
        run["created_at"] = str(row["created_at"])
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    print("missing", len(missing))
    print(handoff_sha256(path))


if __name__ == "__main__":
    main()
