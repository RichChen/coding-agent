from events.handlers import uppercase_handler
from events.registry import get_handler, register_handler


def test_register_multiple_handlers():
    register_handler("upper", uppercase_handler)
    assert get_handler("upper") is not None
