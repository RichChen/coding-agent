"""Normalized diff for A6-R.

The functions between the markers are copied verbatim from coding-harness
scripts/build_a6_attempts.py. tests/test_a6_diff.py compares their AST with the harness file.
"""

from __future__ import annotations

import base64
import difflib
import json
from pathlib import Path

# --- copied from coding-harness scripts/build_a6_attempts.py -------------------------------------

TEST_DIRS = frozenset({"tests", "test", "testing"})
TRUNCATED = "[truncated]"


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


def head(text: str, limit: int) -> tuple[str, bool]:
    data = text.encode("utf-8")
    if len(data) <= limit:
        return text, False
    marker = "\n" + TRUNCATED
    return data[: limit - len(marker.encode("utf-8"))].decode("utf-8", "ignore") + marker, True


def original_reader(root: Path):
    def read(path: str) -> bytes | None:
        file = root / path
        return file.read_bytes() if file.is_file() else None
    return read

# --- end of copy ---------------------------------------------------------------------------------

COPIED = ("TEST_DIRS", "TRUNCATED", "is_test_path", "_lf_text", "_lines", "normalized_diff", "head", "original_reader")


def diff_against(delta: dict, original_root: Path) -> str:
    return normalized_diff(delta, original_reader(Path(original_root)))


def load_delta(run_dir: Path) -> dict | None:
    path = Path(run_dir) / "candidate-delta.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
