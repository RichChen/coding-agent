from events.handlers import echo_handler, length_handler
from events.registry import get_handler, register_many


def test_register_many_preserves_dispatch():
    register_many({"echo": echo_handler, "length": length_handler})
    handler = get_handler("length")
    assert handler is not None
    assert handler({"text": "abc"})["length"] == 3
