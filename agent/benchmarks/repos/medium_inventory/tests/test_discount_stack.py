from inventory.discounts import stack_discount_total


def test_empty_cart_no_codes_returns_zero():
    assert stack_discount_total([], []) == 0
