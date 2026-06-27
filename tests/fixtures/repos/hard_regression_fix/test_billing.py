from billing import discount


def test_discount_large_order():
    assert discount(100) == 95


def test_discount_small_order():
    assert discount(50) == 50
