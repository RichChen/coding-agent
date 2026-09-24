"""Inventory domain models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass
class Result(Generic[T]):
    """Repo convention: operations return Result instead of raising."""

    ok: bool
    value: T | None = None
    error: str = ""


@dataclass
class Item:
    sku_id: str
    name: str
    unit_price: int
    quantity: int = 1


@dataclass
class TaxProfile:
    region: str
    rate: float
