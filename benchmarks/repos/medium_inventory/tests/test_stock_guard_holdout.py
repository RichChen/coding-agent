from inventory.api import stock_status
from inventory.models import Item, Result


def test_low_stock_returns_result_not_raise():
    item = Item(sku_id="s2", name="widget", unit_price=10, quantity=2)
    result = stock_status(item, 5)
    assert isinstance(result, Result)
    assert not result.ok
    assert "minimum" in result.error.lower()
