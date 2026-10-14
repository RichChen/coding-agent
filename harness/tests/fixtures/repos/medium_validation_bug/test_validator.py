from validator import is_valid_email


def test_valid_email():
    assert is_valid_email("dev@example.com")


def test_missing_domain_dot_is_invalid():
    assert not is_valid_email("dev@example")


def test_missing_at_is_invalid():
    assert not is_valid_email("dev.example.com")
