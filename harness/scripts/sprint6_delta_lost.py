#!/usr/bin/env python3
"""6D D2: describe each B0 delta_lost run by replaying its edit calls on the original tree. No model calls.

Categories: empty_edit (every edit has search == replace), reverted (edits changed the file and a later
edit restored it), other.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EDITS = ("search_replace", "edit_file", "write_file")
WRITES = re.compile(r"(?:>|\btee\b|\bsed -i\b|\bgit (?:checkout|restore|stash|apply|reset)\b|\bpatch\b|\bcp\b|\bmv\b|\brm\b)")
HARMLESS = re.compile(r"\d?>&\d|\d?>\s*/dev/null|>>?\s*/tmp/\S+")


def describe(run: Path) -> dict:
    task_id = run.parent.parent.name
    events = [json.loads(line) for line in (run / "events.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    original_root = ROOT / "runs" / "sprint5-main-images" / task_id / "staging" / "original"
    files, states, names, identical, commands = {}, [], {}, 0, []
    for event in events:
        if event["event_type"] != "tool.intent":
            continue
        name, args = event["payload"]["name"], event["payload"]["arguments"]
        if name == "run_command" and WRITES.search(HARMLESS.sub("", args.get("command", ""))):
            commands.append(args["command"][:200])
        if name not in EDITS:
            continue
        path = args["path"]
        if path not in files:
            files[path] = (original_root / path).read_text(encoding="utf-8", newline="") if (original_root / path).is_file() else ""
            names.setdefault((path, hashlib.sha256(files[path].encode()).hexdigest()), "O")
        if name == "write_file":
            old, new = files[path], args.get("content", "")
        else:
            old, new = args.get("search", args.get("old_string")), args.get("replace", args.get("new_string"))
            identical += int(old == new)
        if name == "write_file":
            files[path] = new
        elif files[path].count(old) == 1:
            files[path] = files[path].replace(old, new, 1)
        key = (path, hashlib.sha256(files[path].encode()).hexdigest())
        names.setdefault(key, chr(ord("A") + len(names) - 1))
        states.append(names[key])
    unchanged = all(text == ((original_root / path).read_text(encoding="utf-8", newline="") if (original_root / path).is_file() else "")
                    for path, text in files.items())
    if states and identical == len(states):
        category = "empty_edit"
    elif unchanged and any(state != "O" for state in states):
        category = "reverted"
    else:
        category = "other"
    summary = json.loads((run / "summary.json").read_text(encoding="utf-8"))
    return {
        "run": task_id + "/b0/" + run.name,
        "category": category,
        "edits": len(states),
        "search_equals_replace": identical,
        "states": "O->" + "->".join(states),
        "final_equals_original": unchanged,
        "workspace_write_commands": commands,
        "stop_reason": summary.get("stop_reason"),
        "model_calls": summary.get("model_calls"),
    }


def main():
    root = ROOT / "runs" / "a5-main"
    rows = []
    for path in sorted(root.glob("*/b0/r[123]/summary.json")):
        if json.loads(path.read_text(encoding="utf-8")).get("status") == "delta_lost":
            rows.append(describe(path.parent))
    print(json.dumps(rows, indent=2))
    if any(row["category"] == "other" for row in rows):
        sys.exit(1)


if __name__ == "__main__":
    main()
