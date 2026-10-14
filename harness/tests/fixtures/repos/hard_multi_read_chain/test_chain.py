from aggregator import total


def test_total_sums_all_parts():
    assert total() == 10
