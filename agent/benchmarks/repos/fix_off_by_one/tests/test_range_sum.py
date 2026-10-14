from app.range_sum import range_sum


def test_single_element():
    assert range_sum(5, 5) == 5


def test_inclusive_range():
    assert range_sum(1, 5) == 15


def test_empty_range():
    assert range_sum(5, 3) == 0
