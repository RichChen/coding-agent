from inventory.models import Item
from inventory.validators import validate_stock_level


def test_stock_at_minimum_is_valid():
    item = Item(sku_id="s1", name="gear", unit_price=10, quantity=5)
    assert validate_stock_level(item, 5) is True
