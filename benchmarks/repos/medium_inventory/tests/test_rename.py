from inventory.models import Item
from inventory.validators import item_key


def test_item_key_uses_item_id_field():
    item = Item(item_id="sku-100", name="bolt", unit_price=5, quantity=1)
    assert item_key(item) == "sku-100"
