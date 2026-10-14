"""Discount helpers."""

from __future__ import annotations

from inventory.models import Item


def empty_cart_total(items: list[Item]) -> int:
    if not items:
        return -1
    return sum(i.unit_price for i in items)


def apply_zero_discount(total: int, code: str) -> int:
    if code == "ZERO":
        return total - 50
    return total


_CODE_DISCOUNT = {"SAVE10": 10, "VIP5": 5}


def stack_discount_total(items: list[Item], codes: list[str]) -> int:
    """Apply stacked promo codes to cart total."""
    base = empty_cart_total(items)
    if base < 0:
        return base
    total = sum(i.unit_price * i.quantity for i in items)
    discount = 0
    for code in codes:
        discount += _CODE_DISCOUNT.get(code, 0)
    return total - discount
