from app import render


def test_render():
    assert render() == "User: Ada"
