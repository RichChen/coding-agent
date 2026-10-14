from inventory.discounts import stack_discount_total
from inventory.models import Item


def test_duplicate_codes_apply_once():
    items = [Item(sku_id="a1", name="widget", unit_price=100, quantity=1)]
    assert stack_discount_total(items, ["SAVE10", "SAVE10"]) == 90
