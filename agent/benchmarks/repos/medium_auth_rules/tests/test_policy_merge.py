from auth_rules.policy import merge_policies


def test_user_policy_overrides_defaults():
    defaults = {"read": True, "write": False, "delete": False}
    user_policy = {"write": True}
    merged = merge_policies(defaults, user_policy)
    assert merged["read"] is True
    assert merged["write"] is True
    assert merged["delete"] is False
