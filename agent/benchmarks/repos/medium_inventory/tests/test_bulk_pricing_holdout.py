from inventory.models import Item
from inventory.pricing import bulk_line_total


def test_bulk_discount_single_item_at_threshold():
    item = Item(sku_id="b3", name="unit", unit_price=200, quantity=1)
    assert bulk_line_total(item, 1) == 180
