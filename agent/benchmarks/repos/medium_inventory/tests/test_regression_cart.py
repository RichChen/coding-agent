from inventory.discounts import apply_zero_discount, empty_cart_total


def test_empty_cart_total_is_zero():
    assert empty_cart_total([]) == 0


def test_zero_discount_code_keeps_total():
    assert apply_zero_discount(100, "ZERO") == 100
