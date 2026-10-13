"""Normalized diff for A6-R. Must match harness scripts/build_a6_attempts.py byte for byte.

The rules are written out in docs/sprint/A6-R-PREREG.zh-CN.md.
"""

from __future__ import annotations

import base64
import difflib
import json
from pathlib import Path

TRUNCATED = "\n[truncated]"


def normalize_path(path: str) -> str:
    return path.replace("\\", "/")


def is_test_path(path: str) -> bool:
    parts = normalize_path(path).split("/")
    name = parts[-1]
    if any(part in {"tests", "test"} for part in parts[:-1]):
        return True
    if len(parts) > 1 and parts[0] == "testing":
        return True
    if name == "conftest.py":
        return True
    return (name.startswith("test_") and name.endswith(".py")) or name.endswith("_test.py")


def _text(data: bytes) -> str:
    return data.decode("utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n")


def _lines(text: str) -> list[str]:
    pieces = text.split("\n")
    lines = [piece + "\n" for piece in pieces[:-1]]
    if pieces[-1]:
        lines.append(pieces[-1])
    return lines


def file_diff(path: str, before: bytes | None, after: bytes | None) -> str:
    old = "" if before is None else _text(before)
    new = "" if after is None else _text(after)
    if old == new:
        return ""
    fromfile = "/dev/null" if before is None else "a/" + path
    tofile = "/dev/null" if after is None else "b/" + path
    out = []
    for line in difflib.unified_diff(_lines(old), _lines(new), fromfile, tofile, n=3):
        out.append(line if line.endswith("\n") else line + "\n\\ No newline at end of file\n")
    return "".join(out)


def delta_contents(delta: dict | None) -> dict[str, bytes | None]:
    """Path -> new bytes, or None for a deletion. changed wins over deleted, as in apply_delta."""
    files: dict[str, bytes | None] = {}
    if not delta:
        return files
    for name in delta.get("deleted") or []:
        files[normalize_path(name)] = None
    for name, change in (delta.get("changed") or {}).items():
        encoded = change["content"] if isinstance(change, dict) else change
        files[normalize_path(name)] = base64.b64decode(encoded)
    return files


def normalized_diff(delta: dict | None, original_root: Path) -> str:
    files = delta_contents(delta)
    parts = []
    for path in sorted(files, key=lambda item: (is_test_path(item), item)):
        source = Path(original_root) / path
        before = source.read_bytes() if source.is_file() else None
        after = files[path]
        if before is None and after is None:
            continue
        parts.append(file_diff(path, before, after))
    return "".join(parts)


def truncate_diff(text: str, limit: int) -> tuple[str, bool]:
    encoded = text.encode("utf-8")
    if len(encoded) <= limit:
        return text, False
    keep = limit - len(TRUNCATED.encode("utf-8"))
    return encoded[:keep].decode("utf-8", errors="ignore") + TRUNCATED, True


def load_delta(run_dir: Path) -> dict | None:
    path = Path(run_dir) / "candidate-delta.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
