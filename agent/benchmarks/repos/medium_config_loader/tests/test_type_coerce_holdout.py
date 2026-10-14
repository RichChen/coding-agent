from config_loader.schema import coerce_timeout


def test_coerce_whitespace_string():
    assert coerce_timeout("  25  ") == 25
