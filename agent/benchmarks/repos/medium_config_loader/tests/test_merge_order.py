from config_loader.merge import merge_layers
from config_loader.sources import load_defaults, load_file_config


def test_file_config_overrides_defaults():
    merged = merge_layers(load_defaults(), load_file_config())
    assert merged["timeout"] == 60
    assert merged["retries"] == 1
    assert merged["debug"] is False
