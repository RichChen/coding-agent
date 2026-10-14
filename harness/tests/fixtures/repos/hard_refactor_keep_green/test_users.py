from helpers import format_name
from display import show_user


def test_format_name():
    assert format_name("Ada", "Lovelace") == "Ada Lovelace"


def test_show_user():
    assert show_user({"first": "Ada", "last": "Lovelace"}) == "Ada Lovelace"
