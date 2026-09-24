"""Hardcoded default configuration."""

from __future__ import annotations

from typing import Any


def load_hardcoded_defaults() -> dict[str, Any]:
    return {"timeout": 30, "retries": 3, "debug": False}
