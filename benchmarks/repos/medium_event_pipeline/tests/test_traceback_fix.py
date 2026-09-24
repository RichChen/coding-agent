from events.message import EventMessage
from events.serializer import deserialize_v1, serialize_v1


def test_deserialize_v1_preserves_payload():
    raw = serialize_v1(EventMessage("evt", {"a": 1}))
    message = deserialize_v1(raw)
    assert message.payload == {"a": 1}
