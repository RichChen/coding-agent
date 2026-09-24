from config_loader.defaults import load_hardcoded_defaults
from config_loader.merge import merge_with_defaults


def test_partial_override_keeps_other_defaults():
    defaults = load_hardcoded_defaults()
    merged = merge_with_defaults(defaults, {"retries": 1})
    assert merged["timeout"] == 30
    assert merged["retries"] == 1
