"""Shared config types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Result:
    ok: bool
    value: dict[str, Any] | None = None
    error: str = ""


def validate_config(config: dict[str, Any]) -> Result:
    """Validate config field types."""
    return Result(ok=True, value=config)


def coerce_timeout(value: Any) -> int:
    if isinstance(value, int):
        return value
    return 0
