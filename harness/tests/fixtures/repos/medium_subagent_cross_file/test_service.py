from service import describe


def test_describe_formats_user_email():
    assert describe("Ada|ada@example.com") == "Ada <ada@example.com>"
