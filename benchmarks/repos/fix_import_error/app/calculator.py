"""Simple calculator module."""

from app.utils import helper  # noqa: F401 — broken import


def add(a: int, b: int) -> int:
    return a + b


def subtract(a: int, b: int) -> int:
    return a - b
