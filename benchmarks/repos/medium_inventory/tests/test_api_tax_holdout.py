from inventory.models import Item, TaxProfile
from inventory.pricing import calculate_total


def test_eu_tax_profile_applied():
    items = [Item(sku_id="b2", name="gadget", unit_price=50, quantity=1)]
    profile = TaxProfile(region="EU", rate=0.2)
    result = calculate_total(items, "EU", tax_profile=profile)
    assert result.ok
    assert result.value == 60
