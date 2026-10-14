"""Policy merge helpers."""

from __future__ import annotations

from typing import Any


def merge_policies(*layers: dict[str, Any]) -> dict[str, Any]:
    """Later layers should override earlier ones."""
    merged: dict[str, Any] = {}
    for layer in reversed(layers):
        merged.update(layer)
    return merged
