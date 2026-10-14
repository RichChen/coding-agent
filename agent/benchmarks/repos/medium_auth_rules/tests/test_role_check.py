from auth_rules.api import check_role
from auth_rules.models import Result, User


def test_check_role_returns_result_for_matching_role():
    user = User(user_id="u1", name="Alice", roles=["editor"])
    result = check_role(user, "editor")
    assert isinstance(result, Result)
    assert result.ok
    assert result.value is True


def test_check_role_returns_failure_result():
    user = User(user_id="u2", name="Bob", roles=["viewer"])
    result = check_role(user, "editor")
    assert isinstance(result, Result)
    assert not result.ok
    assert "editor" in result.error.lower()
