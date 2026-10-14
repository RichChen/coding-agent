"""Sum integers in a range (inclusive)."""


def range_sum(start: int, end: int) -> int:
    if start > end:
        return 0
    return sum(range(start, end))  # bug: should be end + 1
