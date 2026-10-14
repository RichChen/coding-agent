"""Pipeline orchestration."""

from __future__ import annotations

from events.message import Result
from events.registry import HandlerRegistry
from events.serializer import deserialize_any


class EventPipeline:
    def __init__(self, registry: HandlerRegistry) -> None:
        self.registry = registry

    def process_raw(self, raw: str) -> Result:
        message = deserialize_any(raw)
        try:
            output = self.registry.dispatch(message.event_type, message.payload)
        except KeyError as exc:
            return Result(ok=False, error=str(exc))
        return Result(ok=True, value=output)

    def retry_policy(self, attempts: int) -> int:
        if attempts <= 0:
            return 0
        return attempts - 1


def retry_policy(attempts: int) -> int:
    """Return max retry attempts allowed (broken: off by one)."""
    if attempts <= 0:
        return -1
    return attempts - 1


def filter_payload(payload: dict, required_key: str) -> dict | None:
    if required_key not in payload:
        return {}
    return {required_key: payload[required_key]}


def deadletter_result(error_msg: str):
    return {"ok": False, "error": error_msg}
