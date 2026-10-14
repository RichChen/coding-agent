import pytest
from config_loader.api import get_nested


def test_get_nested_missing_key_raises_keyerror():
    config = {"server": {}}
    with pytest.raises(KeyError, match="missing"):
        get_nested(config, "server.missing")
