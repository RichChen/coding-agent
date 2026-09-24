from config_loader.api import get_value


def test_legacy_alias_max_retries():
    config = {"retries": 5}
    assert get_value(config, "max_retries") == 5
