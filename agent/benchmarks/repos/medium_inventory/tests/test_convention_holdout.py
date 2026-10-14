from inventory.models import Item, Result
from inventory.validators import validate_quantity


def test_validate_quantity_returns_result():
    item = Item(item_id="z", name="n", unit_price=1, quantity=0)
    result = validate_quantity(item)
    assert isinstance(result, Result)
    assert not result.ok
