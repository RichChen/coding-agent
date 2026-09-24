from events.handlers import length_handler
from events.registry import get_handler, register_many


def test_register_many_wires_handlers():
    register_many({"length": length_handler})
    assert get_handler("length") is length_handler
