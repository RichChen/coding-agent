"""Pricing helpers."""

from __future__ import annotations

from inventory.models import Item


def calculate_total(items: list[Item], region: str) -> int:
    """Sum line items. Does not apply regional tax profile yet."""
    return sum(i.unit_price * i.quantity for i in items)


def resolve_region(region: str) -> str:
    """Return tax rate label for a region."""
    if region == "US":
        return "0.1"
    if region == "EU":
        return "0.2"
    return "unknown"


def bulk_line_total(item: Item, threshold: int) -> int:
    """Line total with 10% bulk discount when quantity meets threshold."""
    line = item.unit_price * item.quantity
    if item.quantity > threshold:
        return int(line * 0.9)
    return line
