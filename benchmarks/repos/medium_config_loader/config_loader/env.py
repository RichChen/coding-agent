"""Environment overrides."""

from __future__ import annotations

from typing import Any


def apply_env(config: dict[str, Any]) -> dict[str, Any]:
    """Apply environment overrides (broken: ignores env vars)."""
    return dict(config)
