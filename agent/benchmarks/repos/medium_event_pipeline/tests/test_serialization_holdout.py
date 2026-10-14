from events.message import EventMessage
from events.serializer import deserialize_any, serialize_v1


def test_v1_still_supported():
    raw = serialize_v1(EventMessage("evt", {"k": "v"}))
    message = deserialize_any(raw)
    assert message.event_type == "evt"
    assert message.payload == {"k": "v"}
