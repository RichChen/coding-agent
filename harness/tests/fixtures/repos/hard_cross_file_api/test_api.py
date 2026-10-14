from api import get_user_display


def test_display_includes_name_and_role():
    assert get_user_display(1) == "Ada (admin)"


def test_missing_user_is_readable():
    assert get_user_display(999) == "Unknown user"
