"""Pull commands, reads, and diagnosis out of a source run's events.jsonl.

Payloads may be inlined or stored as artifact_ref under run/session/artifacts.
Fields that cannot be read are skipped and the reason is kept on the result.
"""

from __future__ import annotations

import ast
import base64
import binascii
import json
import re
from pathlib import Path

from reposkill_agent.protocol.public import StrictModel

_COMMAND_KEEP = ("pytest", "runtests.py", "python -c", "python -m")
_CAUSE = re.compile(
    r"\b(because|caused|root cause|the (issue|bug|problem)|happens when|the reason|the fix)\b",
    re.IGNORECASE,
)
_NAV = re.compile(r"^(I['’]ll |Let me |Now let me |I will |No internet)", re.IGNORECASE)
_DEF_LINE = re.compile(r"^(?:async\s+def|def|class)\s+([A-Za-z_][A-Za-z0-9_]*)", re.MULTILINE)


class ReadSpan(StrictModel):
    path: str
    start: int | None = None
    end: int | None = None


class CodeSearch(StrictModel):
    pattern: str
    path: str = ""


class SourceExtraction(StrictModel):
    source_id: str
    events_found: bool
    skipped: tuple[str, ...] = ()
    reads: tuple[ReadSpan, ...] = ()
    searches: tuple[CodeSearch, ...] = ()
    edited_paths: tuple[str, ...] = ()
    commands: tuple[str, ...] = ()
    diagnosis: str = ""
    final_answer: str = ""
    changed_symbols: tuple[str, ...] = ()


def locate_events(source_dir: Path, layout: str | None = None) -> tuple[Path, Path]:
    """Return events.jsonl and the artifacts directory for one run layout.

    ``memory_pool`` keeps events under ``run/``. ``sprint`` keeps them beside
    ``session/``. When layout is omitted, exactly one of those files must exist.
    """
    memory_events = source_dir / "run" / "events.jsonl"
    sprint_events = source_dir / "events.jsonl"
    if layout == "memory_pool":
        return memory_events, memory_events.parent / "session" / "artifacts"
    if layout == "sprint":
        return sprint_events, source_dir / "session" / "artifacts"
    if layout is not None:
        raise ValueError("invalid_event_layout")
    found = [path for path in (memory_events, sprint_events) if path.is_file()]
    if len(found) > 1:
        raise ValueError("ambiguous_event_layout")
    if not found:
        return memory_events, memory_events.parent / "session" / "artifacts"
    events_path = found[0]
    if events_path == sprint_events:
        return sprint_events, source_dir / "session" / "artifacts"
    return memory_events, memory_events.parent / "session" / "artifacts"


def extract_source(source_dir: Path, source_id: str, layout: str | None = None) -> SourceExtraction:
    events_path, artifacts = locate_events(source_dir, layout)
    if not events_path.is_file():
        return SourceExtraction(source_id=source_id, events_found=False, skipped=("events_jsonl_missing",))
    skipped: list[str] = []
    reads: list[ReadSpan] = []
    searches: list[CodeSearch] = []
    edited: list[str] = []
    commands: list[str] = []
    edits: list[tuple[str, str, str]] = []
    assistant: list[str] = []
    for raw in events_path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        event = json.loads(raw)
        payload, reason = resolve_value(event.get("payload"), artifacts)
        if reason:
            skipped.append(reason)
            continue
        if not isinstance(payload, dict):
            continue
        kind = event.get("event_type")
        if kind == "tool.intent":
            _take_tool(payload, artifacts, reads, searches, edited, commands, edits, skipped)
        elif kind == "state.saved":
            _take_assistant(payload, artifacts, assistant, skipped)
    diagnosis, final = _diagnosis(assistant)
    symbols, symbol_skips = _changed_symbols(source_dir / "candidate-delta.json", edits)
    skipped.extend(symbol_skips)
    return SourceExtraction(
        source_id=source_id,
        events_found=True,
        skipped=tuple(dict.fromkeys(skipped)),
        reads=tuple(reads),
        searches=tuple(searches),
        edited_paths=tuple(dict.fromkeys(edited)),
        commands=tuple(commands),
        diagnosis=diagnosis,
        final_answer=final,
        changed_symbols=tuple(symbols),
    )


def resolve_value(value: object, artifacts: Path) -> tuple[object, str | None]:
    if not isinstance(value, dict) or "artifact_ref" not in value:
        return value, None
    if set(value) - {"artifact_ref"}:
        return value, None
    ref = value["artifact_ref"]
    if not isinstance(ref, dict):
        return None, "artifact_ref_malformed"
    relative = str(ref.get("path") or "")
    if not relative or Path(relative).is_absolute() or ".." in Path(relative).parts:
        return None, "artifact_ref_unsafe"
    path = artifacts / relative
    if not path.is_file():
        return None, "artifact_missing:" + relative[:16]
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None, "artifact_unreadable:" + relative[:16]


def _take_tool(payload, artifacts, reads, searches, edited, commands, edits, skipped) -> None:
    name = str(payload.get("name") or "")
    arguments, reason = resolve_value(payload.get("arguments"), artifacts)
    if reason:
        skipped.append(reason)
        return
    if not isinstance(arguments, dict):
        return
    path = str(arguments.get("path") or "").replace("\\", "/")
    if name == "read_file" and path:
        start = arguments.get("offset") or arguments.get("start")
        limit = arguments.get("limit")
        start_n = int(start) if isinstance(start, int) and start > 0 else 1
        end_n = start_n + int(limit) - 1 if isinstance(limit, int) and limit > 0 else None
        span = ReadSpan(path=path, start=start_n, end=end_n)
        if span not in reads:
            reads.append(span)
    elif name in {"search_code", "search"} and arguments.get("pattern"):
        searches.append(CodeSearch(pattern=str(arguments["pattern"])[:120], path=path))
    elif name in {"search_replace", "edit_file", "write_file"} and path:
        if path not in edited:
            edited.append(path)
        search = str(arguments.get("search") or arguments.get("old_string") or "")
        replace = str(arguments.get("replace") or arguments.get("new_string") or "")
        if replace or search:
            edits.append((path, search, replace))
    elif name == "run_command":
        command = re.sub(r"\s+", " ", str(arguments.get("command") or "")).strip()
        if command and _keep_command(command) and command[:180] not in commands:
            commands.append(command[:180])


def _keep_command(command: str) -> bool:
    lowered = command.lower()
    if "runtests.py" in lowered or "python -c" in lowered or "python -m" in lowered:
        return True
    return bool(re.search(r"(^|[^\w])pytest([^\w]|$)", lowered))


def _take_assistant(payload, artifacts, assistant, skipped) -> None:
    messages, reason = resolve_value(payload.get("messages"), artifacts)
    if reason:
        skipped.append(reason)
        return
    if not isinstance(messages, list):
        return
    for message in messages:
        if not isinstance(message, dict) or message.get("role") != "assistant":
            continue
        content, content_reason = resolve_value(message.get("content"), artifacts)
        if content_reason:
            skipped.append(content_reason)
            continue
        text = content if isinstance(content, str) else ""
        text = text.strip()
        if text and text not in assistant:
            assistant.append(text)


def _sentences(text: str, limit: int = 3) -> str:
    parts = re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", text).strip())
    return " ".join(part for part in parts[:limit] if part).strip()[:500]


def _diagnosis(assistant: list[str]) -> tuple[str, str]:
    diagnosis = ""
    for text in assistant:
        if _NAV.match(text) and len(text) < 180:
            continue
        if _CAUSE.search(text) or len(text) >= 180:
            diagnosis = _sentences(text)
            break
    final = ""
    for text in reversed(assistant):
        if len(text) >= 40:
            final = _sentences(text)
            break
    return diagnosis, final


def _decode_changed(payload: object) -> tuple[str, str | None]:
    if isinstance(payload, dict):
        return str(payload.get("content") or ""), None
    if isinstance(payload, str):
        try:
            raw = base64.b64decode(payload, validate=True)
            return raw.decode("utf-8"), None
        except (binascii.Error, UnicodeError, ValueError):
            return "", "delta_base64_decode_failed"
    return "", "delta_changed_unrecognized"


def _changed_symbols(delta_path: Path, edits: list[tuple[str, str, str]]) -> tuple[list[str], list[str]]:
    changed: dict[str, str] = {}
    skipped: list[str] = []
    if delta_path.is_file():
        delta = json.loads(delta_path.read_text(encoding="utf-8"))
        for name, payload in (delta.get("changed") or {}).items():
            text, reason = _decode_changed(payload)
            if reason:
                skipped.append(reason + ":" + str(name))
                continue
            changed[str(name).replace("\\", "/")] = text
    found: list[str] = []
    by_path: dict[str, list[tuple[str, str]]] = {}
    for path, search, replace in edits:
        by_path.setdefault(path, []).append((search, replace))
    for path, content in changed.items():
        pairs = by_path.get(path, [])
        names = _symbols_in_file(content, pairs)
        for name in names:
            if name not in found:
                found.append(name)
    return found[:12], skipped


def _symbols_in_file(content: str, edits: list[tuple[str, str]]) -> list[str]:
    added = []
    for search, replace in edits:
        search_lines = set(search.splitlines())
        for line in replace.splitlines():
            stripped = line.strip()
            if stripped and stripped not in {item.strip() for item in search_lines} and len(stripped) > 8:
                added.append(stripped)
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return _regex_names("\n".join(added))
    parents: dict[ast.AST, ast.AST] = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    lines = content.splitlines()
    names: list[str] = []
    for snippet in added:
        line_no = _line_of(lines, snippet)
        if line_no is None:
            continue
        owner = _enclosing(tree, line_no)
        if owner is None:
            continue
        label = _qualname(owner, parents)
        if label not in names:
            names.append(label)
    if names:
        return names
    return _regex_names("\n".join(added))


def _line_of(lines: list[str], snippet: str) -> int | None:
    for index, line in enumerate(lines, start=1):
        if snippet in line:
            return index
    return None


def _enclosing(tree: ast.AST, line_no: int) -> ast.AST | None:
    best = None
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        end = getattr(node, "end_lineno", node.lineno) or node.lineno
        if node.lineno <= line_no <= end and (best is None or node.lineno >= best.lineno):
            best = node
    return best


def _qualname(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> str:
    parent = parents.get(node)
    if isinstance(parent, ast.ClassDef) and isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return parent.name + "." + node.name
    return node.name  # type: ignore[attr-defined]


def _regex_names(text: str) -> list[str]:
    return list(dict.fromkeys(_DEF_LINE.findall(text)))[:8]
