from config_loader.defaults import load_hardcoded_defaults
from config_loader.merge import merge_with_defaults


def test_override_wins_over_defaults():
    defaults = load_hardcoded_defaults()
    merged = merge_with_defaults(defaults, {"timeout": 99})
    assert merged["timeout"] == 99
