from app.math_api import scale


def test_scale_default_factor():
    assert scale(3) == 6


def test_scale_custom_factor():
    assert scale(3, 4) == 12
