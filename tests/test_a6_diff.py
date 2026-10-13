import base64
import json
import re
from pathlib import Path

import pytest

from scripts.a6_diff import (
    TRUNCATED,
    delta_contents,
    file_diff,
    is_test_path,
    load_delta,
    normalized_diff,
    truncate_diff,
)
from scripts.handoff_sha import handoff_sha256

HARNESS = Path(__file__).resolve().parents[2] / "coding-harness"
RECORD_DIFF = re.compile(
    r"Final diff \(truncated to (\d+) bytes\):\n(.*?)\n\nLast test-like commands", re.DOTALL
)


def _b64(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("tests/prefetch_related/tests.py", True),
        ("sympy/core/tests/test_basic.py", True),
        ("testing/test_assertion.py", True),
        ("src/_pytest/conftest.py", True),
        ("sklearn/utils/test_helpers.py", True),
        ("pkg/foo_test.py", True),
        ("tests\\windows\\x.py", True),
        ("django/contrib/contenttypes/fields.py", False),
        ("sphinx/testing/fixtures.py", False),
        ("sympy/testing/pytest.py", False),
        ("src/_pytest/python_api.py", False),
        ("testing.py", False),
    ],
)
def test_test_path_rule(path, expected):
    assert is_test_path(path) is expected


def test_file_diff_has_no_timestamps_and_marks_missing_newline():
    diff = file_diff("pkg/a.py", b"x = 1\r\ny = 2\r\n", b"x = 1\ny = 3")
    assert diff == (
        "--- a/pkg/a.py\n"
        "+++ b/pkg/a.py\n"
        "@@ -1,2 +1,2 @@\n"
        " x = 1\n"
        "-y = 2\n"
        "+y = 3\n"
        "\\ No newline at end of file\n"
    )


def test_line_endings_alone_are_not_a_change():
    assert file_diff("a.py", b"a\r\nb\r\n", b"a\nb\n") == ""
    assert file_diff("a.py", b"a\rb\r", b"a\nb\n") == ""


def test_only_newline_splits_lines():
    diff = file_diff("a.py", "a\u2028b\n".encode(), "a\u2028c\n".encode())
    assert diff.count("\n") == 5


def test_new_and_deleted_files_and_order(tmp_path):
    original = tmp_path / "original"
    (original / "pkg").mkdir(parents=True)
    (original / "pkg" / "gone.py").write_bytes(b"old\n")
    (original / "pkg" / "same.py").write_bytes(b"same\n")
    (original / "tests").mkdir()
    (original / "tests" / "test_x.py").write_bytes(b"t\n")
    delta = {
        "changed": {
            "tests/test_x.py": _b64("t2\n"),
            "pkg/new.py": {"content": _b64("n\n")},
            "pkg/same.py": _b64("same\r\n"),
        },
        "deleted": ["pkg/gone.py", "pkg/never.py"],
    }
    diff = normalized_diff(delta, original)
    headers = [line for line in diff.splitlines() if line.startswith(("--- ", "+++ "))]
    assert headers == [
        "--- a/pkg/gone.py",
        "+++ /dev/null",
        "--- /dev/null",
        "+++ b/pkg/new.py",
        "--- a/tests/test_x.py",
        "+++ b/tests/test_x.py",
    ]
    assert "same" not in diff
    assert normalized_diff(delta, original) == diff


def test_changed_wins_over_deleted():
    files = delta_contents({"changed": {"a\\b.py": _b64("x")}, "deleted": ["a/b.py"]})
    assert files == {"a/b.py": b"x"}


def test_empty_delta_is_empty_diff(tmp_path):
    assert normalized_diff({"changed": {}, "deleted": []}, tmp_path) == ""
    assert normalized_diff(None, tmp_path) == ""


def test_truncation_keeps_the_byte_limit():
    text = "é" * 100
    short, cut = truncate_diff(text, 1000)
    assert (short, cut) == (text, False)
    body, cut = truncate_diff(text, 51)
    assert cut is True
    assert body.endswith(TRUNCATED)
    assert len(body.encode("utf-8")) <= 51
    assert body[: -len(TRUNCATED)] == "é" * 19


def test_load_delta_missing_returns_none(tmp_path):
    assert load_delta(tmp_path) is None
    (tmp_path / "candidate-delta.json").write_text(json.dumps({"changed": {}}), encoding="utf-8")
    assert load_delta(tmp_path) == {"changed": {}}


def test_handoff_sha_matches_the_harness_copy():
    harness = HARNESS / "scripts" / "handoff_sha.py"
    if not harness.is_file():
        pytest.skip("coding-harness not present")
    mine = Path(__file__).resolve().parents[1] / "scripts" / "handoff_sha.py"
    normalize = lambda data: data.replace(b"\r\n", b"\n")  # noqa: E731
    assert normalize(mine.read_bytes()) == normalize(harness.read_bytes())


def test_crlf_and_lf_files_share_a_handoff_sha(tmp_path):
    lf = tmp_path / "lf.json"
    crlf = tmp_path / "crlf.json"
    lf.write_bytes(b'{"a": 1}\n')
    crlf.write_bytes(b'{"a": 1}\r\n')
    assert handoff_sha256(lf) == handoff_sha256(crlf)


def test_diff_matches_the_harness_records_byte_for_byte():
    """Pending until harness commits build_a6_attempts.py and the rendered records."""
    builder = HARNESS / "scripts" / "build_a6_attempts.py"
    records = HARNESS / "docs" / "sprint" / "a6-attempts"
    if not builder.is_file() or not records.is_dir():
        pytest.skip("harness build_a6_attempts.py and records not committed yet")
    checked = 0
    for record in sorted(records.glob("*__b0r*.txt")):
        task, first = record.stem.rsplit("__", 1)
        text = record.read_bytes().replace(b"\r\n", b"\n").decode("utf-8")
        match = RECORD_DIFF.search(text)
        assert match, record.name
        limit = int(match.group(1))
        run_dir = HARNESS / "runs" / "a5-main" / task / "b0" / ("r" + first[len("b0r") :])
        original = HARNESS / "runs" / "sprint5-main-images" / task / "staging" / "original"
        expected, _ = truncate_diff(normalized_diff(load_delta(run_dir), original), limit)
        rendered = match.group(2)
        if expected == "":
            assert rendered.strip() in {"", "none"}, record.name
        else:
            assert rendered == expected, record.name
        checked += 1
    assert checked == 53
