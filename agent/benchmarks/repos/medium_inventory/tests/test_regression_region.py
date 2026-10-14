from inventory.models import Result, TaxProfile
from inventory.pricing import resolve_region


def test_unknown_region_returns_result_error():
    result = resolve_region("MARS")
    assert isinstance(result, Result)
    assert not result.ok
    assert "unknown" in result.error.lower()


def test_known_region_returns_tax_profile():
    result = resolve_region("US")
    assert result.ok
    assert isinstance(result.value, TaxProfile)
    assert result.value.rate == 0.1
