from events.pipeline import filter_payload


def test_filter_payload_passes_when_present():
    payload = {"id": 1, "data": "x"}
    assert filter_payload(payload, "id") == payload
