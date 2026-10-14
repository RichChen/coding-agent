from inventory.models import Item, Result, TaxProfile
from inventory.pricing import calculate_total


def test_calculate_total_returns_result_with_tax():
    items = [Item(sku_id="a1", name="widget", unit_price=100, quantity=2)]
    profile = TaxProfile(region="US", rate=0.1)
    result = calculate_total(items, "US", tax_profile=profile)
    assert isinstance(result, Result)
    assert result.ok
    assert result.value == 220


def test_empty_cart_returns_zero_result():
    result = calculate_total([], "US")
    assert result.ok
    assert result.value == 0
