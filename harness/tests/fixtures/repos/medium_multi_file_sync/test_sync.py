from app import app_version
from settings import VERSION


def test_versions_match():
    assert app_version() == VERSION
