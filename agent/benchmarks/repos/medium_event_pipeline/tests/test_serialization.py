from events.serializer import deserialize_any


def test_v2_format_backward_compat():
    raw = '{"event_type": "ping", "body": {"n": 1}}'
    message = deserialize_any(raw)
    assert message.version == 2
    assert message.event_type == "ping"
    assert message.payload == {"n": 1}
