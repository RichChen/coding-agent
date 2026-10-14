"""Auth domain models."""

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
class Role:
    name: str


@dataclass
class User:
    user_id: str
    name: str
    roles: list[str]
