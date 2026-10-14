
from config_loader.api import load_config


def test_env_timeout_overrides_file(monkeypatch):
    monkeypatch.setenv("CFG_TIMEOUT", "99")
    config = load_config()
    assert config["timeout"] == 99
