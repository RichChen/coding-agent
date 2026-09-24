from events.pipeline import filter_payload


def test_filter_payload_requires_key():
    assert filter_payload({"a": 1}, "b") is None
