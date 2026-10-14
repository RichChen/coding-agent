"""Inventory API surface."""

from __future__ import annotations

from inventory.models import Item, Result
from inventory.validators import validate_stock_level


def fetch_item(catalog: dict[str, Item], item_id: str) -> Item:
    if not item_id:
        raise ValueError("missing item_id")
    if item_id not in catalog:
        raise KeyError(f"unknown item: {item_id}")
    return catalog[item_id]


def list_item_ids(catalog: dict[str, Item]) -> list[str]:
    return [item.sku_id for item in catalog.values()]


def stock_status(item: Item, min_level: int) -> Result:
    if not validate_stock_level(item, min_level):
        raise ValueError(f"stock below minimum {min_level}")
    return Result(ok=True, value="in_stock")
