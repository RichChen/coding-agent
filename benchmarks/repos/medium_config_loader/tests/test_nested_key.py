from config_loader.api import get_nested


def test_get_nested_dotted_path():
    config = {"server": {"timeout": 30}}
    assert get_nested(config, "server.timeout") == 30
