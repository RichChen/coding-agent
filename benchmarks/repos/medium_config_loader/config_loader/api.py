"""Public config API."""

from __future__ import annotations

from typing import Any

from config_loader.env import apply_env
from config_loader.merge import merge_layers
from config_loader.sources import load_defaults, load_file_config


def load_config() -> dict[str, Any]:
    base = merge_layers(load_defaults(), load_file_config())
    return apply_env(base)


def get_value(config: dict[str, Any], key: str) -> Any:
    return config.get(key)


def get_nested(config: dict[str, Any], path: str) -> Any:
    return config.get(path)
