from config_loader.schema import coerce_timeout


def test_coerce_string_timeout():
    assert coerce_timeout("45") == 45
