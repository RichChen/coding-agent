from events.handlers import echo_handler
from events.registry import get_handler, register_handler


def test_register_handler_module_api():
    register_handler("echo", echo_handler)
    assert get_handler("echo") is echo_handler
