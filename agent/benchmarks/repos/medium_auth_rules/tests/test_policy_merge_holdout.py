from auth_rules.policy import merge_policies


def test_explicit_layer_order_last_wins():
    merged = merge_policies({"scope": "read"}, {"scope": "write"})
    assert merged["scope"] == "write"
