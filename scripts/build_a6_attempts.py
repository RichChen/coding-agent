"""Build the A6-R previous-attempt records from the A5 B0 failures and check them for leaks.

A first attempt is an A5 runs/a5-main/<task>/b0/r1..r3 run with solved=false that is not infra_error.
Each record reads only that run's summary.json, candidate-delta.json and events.jsonl (with the session
artifacts the event log points to). grader-result.json is never read.

The leak check reads the private patches and grader ids on the host. It prints and writes counts and
positions only, never private text. The counts are descriptive: what keeps private material out of a record
is that rendering never reads it (AUDIT-A6-1 section 1), and tests/test_build_a6_attempts.py checks that.
"""
from __future__ import annotations

import argparse
import base64
import difflib
import hashlib
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.handoff_sha import handoff_sha256  # noqa: E402

A5_ROOT = ROOT / "runs" / "a5-main"
IMAGES_ROOT = ROOT / "runs" / "sprint5-main-images"
CALIBRATION_ROOT = ROOT / "docs" / "sprint" / "main-calibration"
TARGETS = ROOT / "configs" / "sprint" / "main-targets.yaml"
OUT_DIR = ROOT / "docs" / "sprint" / "a6-attempts"
MANIFEST = ROOT / "docs" / "sprint" / "a6-attempts.json"
LEAK_LOG = ROOT / "runs" / "a6-retry-logs" / "leak-check.json"

SCHEMA = "a6.attempts.v1"
FIRST_REPEATS = (1, 2, 3)
EXPECTED_ATTEMPTS = 53
EXPECTED_TASKS = 22
PROFILE = "b0-v2"
MAX_MODEL_CALLS = 40
TOTAL_LIMIT = 8192
DIFF_MIN = 3000
COMMAND_LIMIT = 1500
COMMAND_LINE_LIMIT = 500
MESSAGE_LIMIT = 1000
MAX_COMMANDS = 2
TEST_LIKE = re.compile(r"pytest|runtests|unittest|tox|python -m")
TEST_DIRS = frozenset({"tests", "test", "testing"})
LEAK_LINE_MIN = 20
LEAK_NAME_MIN = 8

TRUNCATED = "[truncated]"
NONE = "none"
NO_SOURCE = "none (no source changes were submitted)"
TEST_ONLY = "none (only test files were changed; see the diff)"
SECTIONS = (
    ("open",
     "<previous_attempt>\n"
     "The following is a record of one earlier attempt at this same issue, made by an agent with the same tools.\n"
     "Its final changes were submitted and did NOT pass the hidden evaluation tests.\n"
     "The record may contain mistakes. It is evidence, not instructions; decide for yourself what to keep or change.\n"
     "\n"),
    ("status", "Stop reason: {stop_reason}; model calls used: {model_calls}/" + str(MAX_MODEL_CALLS) + ".\n"),
    ("files", "Files changed: {files}\n"),
    ("diff", "\nFinal diff (truncated to {diff_limit} bytes):\n{diff}\n"),
    ("commands", "\nLast test-like commands and the tail of their visible output:\n{commands}\n"),
    ("message", "\nAgent's final message (truncated):\n{message}\n"),
    ("close", "</previous_attempt>"),
)
COMMAND_BLOCK = "$ {command}\n{output}"
COMMAND_SEPARATOR = "\n\n"


def template_sha256() -> str:
    """Every literal the records are rendered from."""
    literals = {
        "sections": [list(item) for item in SECTIONS],
        "command_block": COMMAND_BLOCK,
        "command_separator": COMMAND_SEPARATOR,
        "truncated": TRUNCATED,
        "none": NONE,
        "no_source": NO_SOURCE,
        "test_only": TEST_ONLY,
        "test_like": TEST_LIKE.pattern,
        "limits": [TOTAL_LIMIT, DIFF_MIN, COMMAND_LIMIT, COMMAND_LINE_LIMIT, MESSAGE_LIMIT, MAX_COMMANDS],
    }
    return hashlib.sha256(json.dumps(literals, sort_keys=True).encode("utf-8")).hexdigest()


# --- normalized diff (self-contained, stdlib only) ---------------------------------------------

def is_test_path(path: str) -> bool:
    parts = path.split("/")
    name = parts[-1]
    return (any(part in TEST_DIRS for part in parts[:-1]) or name.startswith("test_")
            or name.endswith("_test.py") or name == "conftest.py")


def _lf_text(data: bytes) -> str | None:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return None
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _lines(text: str) -> list[str]:
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def normalized_diff(delta: dict, original) -> str:
    """Unified diff with 3 lines of context of a candidate delta against the original source.

    delta is candidate-delta.json: changed maps a path to base64 content (or {"content": ...}), deleted lists paths.
    original(path) returns the original bytes or None. Non-test files first, then by path. LF, no timestamps.
    """
    changed = delta.get("changed") or {}
    paths = sorted(set(changed) | set(delta.get("deleted") or []), key=lambda path: (is_test_path(path), path))
    parts = []
    for path in paths:
        before = original(path)
        if path in changed:
            value = changed[path]
            after = base64.b64decode(value["content"] if isinstance(value, dict) else value)
        else:
            after = None
        if before == after:
            continue
        old = "" if before is None else _lf_text(before)
        new = "" if after is None else _lf_text(after)
        if old is None or new is None:
            parts.append("Binary file " + path + " differs\n")
            continue
        lines = list(difflib.unified_diff(
            _lines(old), _lines(new),
            "/dev/null" if before is None else "a/" + path,
            "/dev/null" if after is None else "b/" + path,
            n=3, lineterm="",
        ))
        if lines:
            parts.append("\n".join(lines) + "\n")
    return "".join(parts)


# --- selection -----------------------------------------------------------------------------------

def load_targets(path: Path = TARGETS) -> dict:
    return {task["id"]: task for task in yaml.safe_load(path.read_text(encoding="utf-8"))["tasks"]}


def select_first_attempts(a5_root: Path = A5_ROOT) -> list[dict]:
    """Every B0 r1..r3 run with solved=false that is not infra_error. r4, B2 and .infra<n> are never read."""
    rows = []
    for task_dir in sorted(path for path in a5_root.iterdir() if path.is_dir()):
        for repeat in FIRST_REPEATS:
            run_dir = task_dir / "b0" / ("r" + str(repeat))
            summary_path = run_dir / "summary.json"
            if not summary_path.is_file():
                continue
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            if summary.get("solved") is not False or summary.get("status") == "infra_error":
                continue
            problems = [name for name, bad in (
                ("task_id", summary.get("task_id") != task_dir.name),
                ("variant", summary.get("variant") != "B0"),
                ("mock", summary.get("mock") is not False),
                ("profile", summary.get("profile") != PROFILE),
            ) if bad]
            if problems:
                raise SystemExit("first attempt " + summary_path.as_posix() + " has unexpected " + ", ".join(problems))
            rows.append({"task": task_dir.name, "first": "b0r" + str(repeat), "run_dir": run_dir, "summary": summary})
    return rows


def count_check(rows: list[dict], expected=(EXPECTED_ATTEMPTS, EXPECTED_TASKS)) -> str | None:
    attempts, tasks = len(rows), len({row["task"] for row in rows})
    if expected is not None and (attempts, tasks) != tuple(expected):
        return ("first attempts recount " + str(attempts) + " runs on " + str(tasks) + " tasks, expected "
                + str(expected[0]) + " on " + str(expected[1]))
    return None


# --- event log -----------------------------------------------------------------------------------

def _payload(run_dir: Path, payload: dict) -> dict:
    if set(payload) != {"artifact_ref"}:
        return payload
    ref = payload["artifact_ref"]
    path = run_dir / "session" / "artifacts" / ref["path"]
    if not path.is_file():
        raise ValueError("artifact missing: " + path.as_posix())
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != ref.get("sha256"):
        raise ValueError("artifact does not match its sha256: " + path.as_posix())
    return json.loads(data)


def final_messages(run_dir: Path) -> list[dict]:
    """The conversation in the last state.saved event: what the agent was given and what it wrote."""
    events = run_dir / "events.jsonl"
    if not events.is_file():
        raise ValueError("events.jsonl missing: " + events.as_posix())
    last = None
    with events.open(encoding="utf-8") as handle:
        for line in handle:
            if '"state.saved"' not in line:
                continue
            event = json.loads(line)
            if event.get("event_type") == "state.saved":
                last = event
    if last is None:
        raise ValueError("no state.saved event in " + events.as_posix())
    messages = _payload(run_dir, last.get("payload") or {}).get("messages")
    if not isinstance(messages, list) or not messages:
        raise ValueError("state.saved has no messages in " + events.as_posix())
    return messages


def test_like_commands(messages: list[dict]) -> tuple[list[tuple[str, str]], int]:
    """Every run_command whose command line looks like a test run, with the tool message the agent got back."""
    outputs = {message.get("tool_call_id"): message.get("content") for message in messages if message.get("role") == "tool"}
    found = []
    for message in messages:
        if message.get("role") != "assistant":
            continue
        for call in message.get("tool_calls") or []:
            function = call.get("function") or {}
            if function.get("name") != "run_command":
                continue
            arguments = function.get("arguments")
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    continue
            command = (arguments or {}).get("command") if isinstance(arguments, dict) else None
            if not isinstance(command, str) or not TEST_LIKE.search(command):
                continue
            output = outputs.get(call.get("id"))
            if not isinstance(output, str):
                raise ValueError("no tool output recorded for run_command " + str(call.get("id")))
            found.append((command, output))
    return found, len(found)


def final_assistant_text(messages: list[dict]) -> str | None:
    for message in reversed(messages):
        content = message.get("content")
        if message.get("role") == "assistant" and isinstance(content, str) and content.strip():
            return content.strip()
    return None


# --- rendering -----------------------------------------------------------------------------------

def _lf(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def head(text: str, limit: int) -> tuple[str, bool]:
    data = text.encode("utf-8")
    if len(data) <= limit:
        return text, False
    marker = "\n" + TRUNCATED
    return data[: limit - len(marker.encode("utf-8"))].decode("utf-8", "ignore") + marker, True


def tail(text: str, limit: int) -> tuple[str, bool]:
    data = text.encode("utf-8")
    if len(data) <= limit:
        return text, False
    marker = TRUNCATED + "\n"
    keep = limit - len(marker.encode("utf-8"))
    return marker + data[len(data) - keep:].decode("utf-8", "ignore"), True


def command_block(command: str, output: str) -> tuple[str, bool]:
    line, cut_command = head(_lf(command), COMMAND_LINE_LIMIT)
    prefix = COMMAND_BLOCK.split("{output}")[0].format(command=line)
    body, cut_output = tail(_lf(output), COMMAND_LIMIT - len(prefix.encode("utf-8")))
    return COMMAND_BLOCK.format(command=line, output=body), cut_command or cut_output


def _render(fields: dict) -> list[tuple[str, str]]:
    return [(name, template.format(**fields)) for name, template in SECTIONS]


def render_record(run_dir: Path, summary: dict, original) -> dict:
    """The record text, its section sizes and truncation flags. Raises when a source file or field is missing."""
    delta_path = run_dir / "candidate-delta.json"
    if not delta_path.is_file():
        raise ValueError("candidate-delta.json missing: " + delta_path.as_posix())
    delta = json.loads(delta_path.read_text(encoding="utf-8"))
    for key in ("stop_reason", "model_calls", "changed_files"):
        if summary.get(key) is None:
            raise ValueError("summary has no " + key + ": " + run_dir.as_posix())
    messages = final_messages(run_dir)
    commands, found = test_like_commands(messages)
    blocks = [command_block(command, output) for command, output in commands[-MAX_COMMANDS:]]
    message = final_assistant_text(messages)
    message_text, cut_message = head(_lf(message), MESSAGE_LIMIT) if message else (NONE, False)
    source_files = [path for path in summary["changed_files"] if not is_test_path(path)]
    diff = normalized_diff(delta, original).rstrip("\n")
    fields = {
        "stop_reason": _lf(str(summary["stop_reason"])),
        "model_calls": summary["model_calls"],
        "files": ", ".join(source_files) if source_files else (TEST_ONLY if summary["changed_files"] else NO_SOURCE),
        "commands": COMMAND_SEPARATOR.join(block for block, _ in blocks) if blocks else NONE,
        "message": message_text,
        "diff": "",
        "diff_limit": "0000",
    }
    fixed = sum(len(text.encode("utf-8")) for _, text in _render(fields))
    limit = TOTAL_LIMIT - fixed
    if limit < DIFF_MIN:
        raise ValueError("other sections leave " + str(limit) + " bytes for the diff, less than " + str(DIFF_MIN) + ": " + run_dir.as_posix())
    diff_text, cut_diff = head(diff, limit) if diff else (NONE, False)
    fields.update(diff=diff_text, diff_limit=str(limit))
    sections = _render(fields)
    text = "".join(part for _, part in sections)
    size = len(text.encode("utf-8"))
    if size > TOTAL_LIMIT or "\r" in text:
        raise ValueError("record renders to " + str(size) + " bytes or carries a CR: " + run_dir.as_posix())
    return {
        "text": text,
        "sections": {name: len(part.encode("utf-8")) for name, part in sections},
        "section_spans": _spans(sections),
        "diff_limit": limit,
        "truncated": {"diff": cut_diff, "commands": sum(1 for _, cut in blocks if cut), "message": cut_message},
        "source": {
            "stop_reason": summary["stop_reason"],
            "model_calls": summary["model_calls"],
            "source_files": len(source_files),
            "test_files": len(summary["changed_files"]) - len(source_files),
            "test_like_commands": found,
            "commands_shown": len(blocks),
            "has_final_message": message is not None,
            "has_diff": bool(diff),
        },
    }


def _spans(sections) -> list[tuple[str, int, int]]:
    spans, start = [], 0
    for name, part in sections:
        spans.append((name, start, start + len(part)))
        start += len(part)
    return spans


def original_reader(root: Path):
    def read(path: str) -> bytes | None:
        file = root / path
        return file.read_bytes() if file.is_file() else None
    return read


# --- leak check ----------------------------------------------------------------------------------

def _parse_ids(value) -> list[str]:
    if isinstance(value, str):
        return list(json.loads(value))
    return list(value or [])


def test_name(node: str) -> str | None:
    """The test function name inside a node id, or None when it has none."""
    if " (" in node and node.endswith(")"):
        name = node.split(" ", 1)[0]
        if not name.startswith("test"):
            return None
    elif "::" in node:
        name = node.split("::")[-1]
    elif "." in node and "/" not in node:
        name = node.rsplit(".", 1)[-1]
    else:
        name = node
    name = name.split("[", 1)[0]
    return name if name.isidentifier() else None


def _structured(node: str) -> bool:
    return any(mark in node for mark in ("::", " (", ".", "/"))


def added_lines(patch: str) -> set[str]:
    lines = set()
    for line in patch.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            stripped = line[1:].strip()
            if len(stripped) >= LEAK_LINE_MIN:
                lines.add(stripped)
    return lines


def new_files(patch: str) -> set[str]:
    paths, current = set(), None
    for line in patch.splitlines():
        if line.startswith("diff --git a/"):
            current = line.split(" b/", 1)[1]
        elif current and (line.startswith("new file mode") or line == "--- /dev/null"):
            paths.add(current)
    return paths


def patch_files(patch: str) -> list[str]:
    return sorted({line.split(" b/", 1)[1] for line in patch.splitlines() if line.startswith("diff --git a/")})


def private_material(task: dict, calibration_root: Path = CALIBRATION_ROOT) -> dict:
    """Host-side leak needles for one task. Kept in memory; never printed or written."""
    private_path = Path(task["private"])
    private = json.loads((private_path if private_path.is_absolute() else ROOT / private_path).read_text(encoding="utf-8"))
    calibration_path = calibration_root / (task["id"] + ".json")
    calibration = json.loads(calibration_path.read_text(encoding="utf-8")) if calibration_path.is_file() else {}
    sides = {"f2p": set(_parse_ids(private.get("FAIL_TO_PASS"))), "p2p": set(_parse_ids(private.get("PASS_TO_PASS")))}
    nodeids = calibration.get("nodeids") or {}
    for row in (nodeids.get("mapping") or []) + (nodeids.get("dropped") or []):
        if isinstance(row, dict) and isinstance(row.get("nodeid"), str) and row.get("side") in sides:
            sides[row["side"]].add(row["nodeid"])
    sides["p2p"].update(node for node in calibration.get("p2p_excluded") or [] if isinstance(node, str))
    for side, nodes in sides.items():
        for node in list(nodes):
            if " (" in node and node.endswith(")"):
                name, rest = node.split(" ", 1)
                module = rest.strip("()")
                nodes.add(module if module.endswith("." + name) else module + "." + name)
    ids, names = [], []
    for side in ("f2p", "p2p"):
        for node in sorted(sides[side]):
            if not node:
                continue
            if _structured(node):
                ids.append((side, node))
            name = test_name(node)
            if name and len(name) >= LEAK_NAME_MIN:
                names.append((side, name))
    return {
        "ids": sorted(set(ids)),
        "names": sorted(set(names)),
        "test_lines": sorted(added_lines(private.get("test_patch") or "")),
        "test_new_files": sorted(new_files(private.get("test_patch") or "")),
        "gold_lines": sorted(added_lines(private.get("patch") or "")),
        "test_files": patch_files(private.get("test_patch") or ""),
        "gold_files": patch_files(private.get("patch") or ""),
    }


def _section_at(spans, offset: int) -> str:
    for name, start, end in spans:
        if start <= offset < end:
            return name
    return spans[-1][0]


def _line_at(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _occurrences(text: str, needle: str) -> list[int]:
    found, start = [], text.find(needle)
    while start != -1:
        found.append(start)
        start = text.find(needle, start + 1)
    return found


def _diff_line_kind(text: str, offset: int) -> str:
    start = text.rfind("\n", 0, offset) + 1
    line = text[start:text.find("\n", offset) if text.find("\n", offset) != -1 else len(text)]
    if line.startswith(("+++ ", "--- ")):
        return "header"
    if line.startswith(("+", "-", " ", "@")):
        return {"+": "added", "-": "removed", " ": "context", "@": "hunk"}[line[0]]
    return "other"


def leak_check(text: str, spans, material: dict, original) -> tuple[dict, list[dict]]:
    """Counts per check and hit positions (check, side, section, line). No private text leaves this function.

    preexisting: the needle is already in the original (pre-patch) version of the files the private patch touches.
    diff_line: for hits inside the diff, whether the line is added by the agent, removed, or unchanged context.
    """
    hits = []

    def hit(check, offset, **extra):
        section = _section_at(spans, offset)
        row = {"check": check, "section": section, "line": _line_at(text, offset), **extra}
        if section == "diff":
            row["diff_line"] = _diff_line_kind(text, offset)
        hits.append(row)

    test_before = "\n".join(_lf_text(original(path) or b"") or "" for path in material["test_files"])
    gold_before = "\n".join(_lf_text(original(path) or b"") or "" for path in material["gold_files"])
    for side, node in material["ids"]:
        for offset in _occurrences(text, node):
            hit("ids", offset, side=side, form="node_id", preexisting=test_name(node) is not None and test_name(node) in test_before)
    for side, name in material["names"]:
        for match in re.finditer(r"(?<![A-Za-z0-9_])" + re.escape(name) + r"(?![A-Za-z0-9_])", text):
            hit("ids", match.start(), side=side, form="test_name",
                preexisting=re.search(r"\bdef " + re.escape(name) + r"\b", test_before) is not None)
    for check, lines, before in (("test_patch_lines", material["test_lines"], test_before),
                                 ("gold_patch_lines", material["gold_lines"], gold_before)):
        for line in lines:
            for offset in _occurrences(text, line):
                hit(check, offset, preexisting=line in before)
    for path in material["test_new_files"]:
        for offset in _occurrences(text, path):
            hit("test_patch_new_files", offset)
    counts = {check: sum(1 for row in hits if row["check"] == check)
              for check in ("ids", "test_patch_lines", "test_patch_new_files", "gold_patch_lines")}
    hits.sort(key=lambda row: (row["check"], row["line"], row["section"], row.get("side", ""), row.get("form", ""),
                               str(row.get("preexisting")), row.get("diff_line", "")))
    return counts, hits


# --- build ---------------------------------------------------------------------------------------

def record_name(task: str, first: str) -> str:
    return task + "__" + first + ".txt"


def _display(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def build(*, a5_root: Path = A5_ROOT, images_root: Path = IMAGES_ROOT, calibration_root: Path = CALIBRATION_ROOT,
          targets: dict | None = None, out_dir: Path = OUT_DIR, manifest_path: Path = MANIFEST, log_path: Path | None = LEAK_LOG,
          expected=(EXPECTED_ATTEMPTS, EXPECTED_TASKS)) -> dict:
    """Select, render, check and write. Returns the manifest. Raises SystemExit when the recount is off."""
    targets = targets if targets is not None else load_targets()
    selected = select_first_attempts(a5_root)
    problem = count_check(selected, expected)
    if problem:
        raise SystemExit(problem)
    rows, positions = [], []
    materials = {}
    for item in selected:
        task = targets[item["task"]]
        original = original_reader(images_root / task["id"] / "staging" / "original")
        rendered = render_record(item["run_dir"], item["summary"], original)
        if task["id"] not in materials:
            materials[task["id"]] = private_material(task, calibration_root)
        counts, hits = leak_check(rendered["text"], rendered["section_spans"], materials[task["id"]], original)
        data = rendered["text"].encode("utf-8")
        name = record_name(item["task"], item["first"])
        rows.append({
            "task": item["task"],
            "first": item["first"],
            "run_dir": _display(item["run_dir"]),
            "file": _display(out_dir / name),
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "a5_prompt_sha256": item["summary"].get("prompt_sha256"),
            "sections": rendered["sections"],
            "diff_limit": rendered["diff_limit"],
            "truncated": rendered["truncated"],
            "source": rendered["source"],
            "leak": counts,
            "_data": data,
        })
        positions.append({"task": item["task"], "first": item["first"], "counts": counts, "hits": hits})
    by_task = {}
    for row in rows:
        by_task.setdefault(row["task"], []).append(row["first"])
    totals = {check: sum(row["leak"][check] for row in rows) for check in ("ids", "test_patch_lines", "test_patch_new_files", "gold_patch_lines")}
    manifest = {
        "schema": SCHEMA,
        "source": _display(a5_root),
        "selection": "b0 r1..r3, solved=false, status!=infra_error",
        "template_sha256": template_sha256(),
        "limits": {"total": TOTAL_LIMIT, "diff_min": DIFF_MIN, "command": COMMAND_LIMIT, "command_line": COMMAND_LINE_LIMIT,
                   "message": MESSAGE_LIMIT, "commands": MAX_COMMANDS},
        "attempts": len(rows),
        "tasks": len(by_task),
        "by_task": by_task,
        "leak_totals": totals,
        "records": [{key: value for key, value in row.items() if key != "_data"} for row in rows],
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    for row in rows:
        (out_dir / record_name(row["task"], row["first"])).write_bytes(row["_data"])
    manifest_path.write_bytes((json.dumps(manifest, indent=2) + "\n").encode("utf-8"))
    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_bytes((json.dumps({"records": positions}, indent=2) + "\n").encode("utf-8"))
    return manifest


def load_record(row: dict, root: Path = ROOT) -> str:
    """A record file as LF text, checked against its manifest sha256."""
    path = root / row["file"]
    if not path.is_file():
        raise SystemExit("record missing: " + row["file"])
    if handoff_sha256(path) != row["sha256"]:
        raise SystemExit("record " + row["file"] + " does not match the manifest sha256")
    return path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n").decode("utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    manifest = build()
    for row in manifest["records"]:
        print(row["task"], row["first"], row["bytes"], json.dumps(row["leak"], sort_keys=True), flush=True)
    print("attempts", manifest["attempts"], "tasks", manifest["tasks"], "leak totals", json.dumps(manifest["leak_totals"], sort_keys=True))
    print("template", manifest["template_sha256"])
    print("manifest", _display(MANIFEST), handoff_sha256(MANIFEST))


if __name__ == "__main__":
    main()
