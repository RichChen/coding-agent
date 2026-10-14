"""SHA256 of a handoff file after normalizing newlines to LF."""
from __future__ import annotations

import hashlib
from pathlib import Path


def handoff_sha256(path: Path) -> str:
    text = Path(path).read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(text).hexdigest()
