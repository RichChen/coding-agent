from app.division import safe_divide


def test_safe_divide_regular():
    assert safe_divide(8, 2) == 4


def test_safe_divide_zero_denominator_regression():
    assert safe_divide(8, 0) == 0
