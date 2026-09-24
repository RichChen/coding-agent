from inventory.api import fetch_item
from inventory.models import Result


def test_fetch_missing_item_returns_result():
    result = fetch_item({}, "")
    assert isinstance(result, Result)
    assert not result.ok
    assert "missing" in result.error.lower()


def test_fetch_unknown_returns_result_not_keyerror():
    result = fetch_item({}, "ghost")
    assert isinstance(result, Result)
    assert not result.ok
