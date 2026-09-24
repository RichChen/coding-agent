from config_loader.api import get_value


def test_legacy_alias_request_timeout():
    config = {"timeout": 42}
    assert get_value(config, "request_timeout") == 42
