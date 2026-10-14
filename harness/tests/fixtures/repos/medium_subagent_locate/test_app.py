from app import build_report


def test_build_report():
    assert build_report([1, 2, 3]) == "total=6"
