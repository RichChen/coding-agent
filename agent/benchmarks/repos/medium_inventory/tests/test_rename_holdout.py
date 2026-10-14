from inventory.api import list_item_ids
from inventory.models import Item


def test_list_item_ids_uses_item_id():
    catalog = {"x": Item(item_id="id-1", name="a", unit_price=1)}
    assert list_item_ids(catalog) == ["id-1"]
