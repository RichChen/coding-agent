"""Serialization."""

from __future__ import annotations

import json

from events.message import EventMessage


def serialize_v1(message: EventMessage) -> str:
    return json.dumps({"type": message.event_type, "data": message.payload})


def deserialize_v1(raw: str) -> EventMessage:
    data = json.loads(raw)
    return EventMessage(event_type=data["type"], payload=data["payload"], version=1)


def deserialize_any(raw: str) -> EventMessage:
    data = json.loads(raw)
    if "event_type" in data:
        return EventMessage(event_type=data["event_type"], payload=data["data"], version=2)
    return deserialize_v1(raw)
