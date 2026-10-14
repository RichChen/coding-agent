"""Merge layers."""

from __future__ import annotations

from typing import Any


def merge_layers(*layers: dict[str, Any]) -> dict[str, Any]:
    """Later layers should override earlier ones."""
    merged: dict[str, Any] = {}
    for layer in reversed(layers):
        merged.update(layer)
    return merged


def merge_with_defaults(defaults: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Merge override values on top of defaults."""
    merged = dict(override)
    merged.update(defaults)
    return merged
