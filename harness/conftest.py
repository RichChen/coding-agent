"""Project-wide pytest compatibility helpers."""

from __future__ import annotations

import inspect
import importlib.util

import pytest


def pytest_collection_modifyitems(config, items):
    """Skip async tests with a clear reason when pytest-asyncio is unavailable."""
    if importlib.util.find_spec("pytest_asyncio") is not None:
        return

    skip_async = pytest.mark.skip(reason="pytest-asyncio is not installed")
    for item in items:
        test_obj = getattr(item, "obj", None)
        if test_obj is not None and inspect.iscoroutinefunction(test_obj):
            item.add_marker(skip_async)
