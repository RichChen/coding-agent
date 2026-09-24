"""Token parsing."""

from __future__ import annotations

import json
from typing import Any


def parse_token(raw: str) -> dict[str, Any]:
    """Parse an auth token payload from JSON."""
    data = json.loads(raw)
    version = data.get("version", 1)
    return {
        "subject": data["subject"],
        "token": data["token"],
        "version": version,
    }
