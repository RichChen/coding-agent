"""Validation helpers."""

from __future__ import annotations

from inventory.models import Item


def item_key(item: Item) -> str:
    return item.sku_id


def validate_quantity(item: Item) -> bool:
    return item.quantity > 0 and bool(item.sku_id)


def validate_stock_level(item: Item, min_level: int) -> bool:
    return item.quantity > min_level
