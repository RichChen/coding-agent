from config_loader.merge import merge_layers


def test_explicit_layer_order_last_wins():
    merged = merge_layers({"a": 1}, {"a": 2})
    assert merged["a"] == 2
