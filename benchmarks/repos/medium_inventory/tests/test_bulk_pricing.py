from inventory.models import Item
from inventory.pricing import bulk_line_total


def test_bulk_discount_at_threshold():
    item = Item(sku_id="b1", name="bolt", unit_price=100, quantity=10)
    assert bulk_line_total(item, 10) == 900
