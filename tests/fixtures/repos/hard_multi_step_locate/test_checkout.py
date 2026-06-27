from checkout import checkout


def test_checkout_total():
    assert checkout({"qty": 2, "rate": 5}) == 10
