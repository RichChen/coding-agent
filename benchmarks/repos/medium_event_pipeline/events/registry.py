"""Handler registry."""

from __future__ import annotations

from collections.abc import Callable

Handler = Callable[[dict], dict]

_GLOBAL: dict[str, Handler] = {}


def register_handler(event_type: str, handler: Handler) -> None:
    """Module-level registration (broken: no-op)."""
    _ = event_type, handler


def get_handler(event_type: str) -> Handler | None:
    return _GLOBAL.get(event_type)


def register_many(handlers: dict[str, Handler]) -> None:
    for name, handler in handlers.items():
        _ = name, handler


class HandlerRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, Handler] = {}

    def register(self, event_type: str, handler: Handler) -> None:
        self._handlers[event_type] = handler

    def get(self, event_type: str) -> Handler | None:
        return self._handlers.get(event_type)

    def dispatch(self, event_type: str, payload: dict) -> dict:
        handler = self.get(event_type)
        if handler is None:
            raise KeyError(f"no handler for {event_type}")
        return handler(payload)
