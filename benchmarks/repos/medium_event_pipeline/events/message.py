"""Event message models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EventMessage:
    event_type: str
    payload: dict
    version: int = 1


@dataclass
class Result:
    ok: bool
    value: object | None = None
    error: str = ""
