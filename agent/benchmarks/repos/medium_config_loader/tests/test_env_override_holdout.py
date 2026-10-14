
from config_loader.api import load_config


def test_env_retries_override(monkeypatch):
    monkeypatch.setenv("CFG_RETRIES", "7")
    config = load_config()
    assert config["retries"] == 7
