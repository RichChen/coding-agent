"""Config sources."""

from __future__ import annotations

from typing import Any


def load_defaults() -> dict[str, Any]:
    return {"timeout": 30, "retries": 3, "debug": False}


def load_file_config() -> dict[str, Any]:
    return {"timeout": 60, "retries": 1}
