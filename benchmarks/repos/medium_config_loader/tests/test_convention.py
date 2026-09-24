from config_loader.api import load_config
from config_loader.schema import Result


def test_load_config_returns_result():
    result = load_config()
    assert isinstance(result, Result)
    assert result.ok
    assert "timeout" in result.value
