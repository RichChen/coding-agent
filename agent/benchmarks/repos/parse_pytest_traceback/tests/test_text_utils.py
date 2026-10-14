from app.text_utils import normalize_whitespace


def test_normalize_whitespace_collapses_spaces():
    assert normalize_whitespace(" a   b   c ") == "a b c"
