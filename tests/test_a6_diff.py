import ast
import base64
import json
import re
from pathlib import Path

import pytest

from scripts.a6_diff import (
    COPIED,
    TRUNCATED,
    diff_against,
    head,
    is_test_path,
    load_delta,
    normalized_diff,
)
from scripts.handoff_sha import handoff_sha256

AGENT = Path(__file__).resolve().parents[1]
HARNESS = AGENT.parent / "coding-harness"
BUILDER = HARNESS / "scripts" / "build_a6_attempts.py"
RECORD_DIFF = re.compile(
    r"\nFinal diff \(truncated to (\d+) bytes\):\n(.*?)\n\nLast test-like commands", re.DOTALL
)


def _b64(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def _definitions(path: Path) -> dict[str, str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            found[node.name] = ast.dump(node)
        elif isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name):
                found[target.id] = ast.dump(node)
    return found


def test_copied_functions_match_the_harness_builder():
    if not BUILDER.is_file():
        pytest.skip("harness build_a6_attempts.py not committed yet")
    mine = _definitions(AGENT / "scripts" / "a6_diff.py")
    theirs = _definitions(BUILDER)
    for name in COPIED:
        assert mine[name] == theirs[name], name


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("tests/prefetch_related/tests.py", True),
        ("sympy/core/tests/test_basic.py", True),
        ("testing/test_assertion.py", True),
        ("sphinx/testing/fixtures.py", True),
        ("src/_pytest/conftest.py", True),
        ("pkg/test_data.txt", True),
        ("pkg/foo_test.py", True),
        ("django/contrib/contenttypes/fields.py", False),
        ("src/_pytest/python_api.py", False),
        ("testing.py", False),
    ],
)
def test_test_path_rule(path, expected):
    assert is_test_path(path) is expected


def _diff(files: dict[str, bytes], delta: dict) -> str:
    return normalized_diff(delta, files.get)


def test_diff_has_no_timestamps_and_ignores_line_endings():
    diff = _diff(
        {"pkg/a.py": b"x = 1\r\ny = 2\r\n"}, {"changed": {"pkg/a.py": _b64("x = 1\ny = 3")}}
    )
    assert diff == "--- a/pkg/a.py\n+++ b/pkg/a.py\n@@ -1,2 +1,2 @@\n x = 1\n-y = 2\n+y = 3\n"
    assert _diff({"a.py": b"a\r\nb\r\n"}, {"changed": {"a.py": _b64("a\nb")}}) == ""
    assert _diff({"a.py": b"a\rb\r"}, {"changed": {"a.py": _b64("a\nb\n")}}) == ""


def test_undecodable_files_are_named_as_binary():
    delta = {"changed": {"pkg/blob.bin": base64.b64encode(b"\xff\xfe").decode()}}
    assert _diff({"pkg/blob.bin": b"\x00"}, delta) == "Binary file pkg/blob.bin differs\n"


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
    diff = diff_against(delta, original)
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
    assert diff_against(delta, original) == diff


def test_changed_wins_over_deleted():
    diff = _diff({"a.py": b"x\n"}, {"changed": {"a.py": _b64("y\n")}, "deleted": ["a.py"]})
    assert "+++ b/a.py" in diff


def test_empty_delta_is_empty_diff(tmp_path):
    assert diff_against({"changed": {}, "deleted": []}, tmp_path) == ""


def test_head_keeps_the_byte_limit():
    text = "é" * 100
    assert head(text, 1000) == (text, False)
    body, cut = head(text, 51)
    assert cut is True
    assert body.endswith("\n" + TRUNCATED)
    assert len(body.encode("utf-8")) <= 51
    assert body[: -len("\n" + TRUNCATED)] == "é" * 19


def test_load_delta_missing_returns_none(tmp_path):
    assert load_delta(tmp_path) is None
    (tmp_path / "candidate-delta.json").write_text(json.dumps({"changed": {}}), encoding="utf-8")
    assert load_delta(tmp_path) == {"changed": {}}


def test_handoff_sha_matches_the_harness_copy():
    harness = HARNESS / "scripts" / "handoff_sha.py"
    if not harness.is_file():
        pytest.skip("coding-harness not present")
    mine = AGENT / "scripts" / "handoff_sha.py"
    assert mine.read_bytes().replace(b"\r\n", b"\n") == harness.read_bytes().replace(b"\r\n", b"\n")


def test_crlf_and_lf_files_share_a_handoff_sha(tmp_path):
    lf = tmp_path / "lf.json"
    crlf = tmp_path / "crlf.json"
    lf.write_bytes(b'{"a": 1}\n')
    crlf.write_bytes(b'{"a": 1}\r\n')
    assert handoff_sha256(lf) == handoff_sha256(crlf)


def test_diff_matches_the_harness_records_byte_for_byte():
    """Recompute the Final diff section of every rendered record from the A5 run directories."""
    records = HARNESS / "docs" / "sprint" / "a6-attempts"
    if not BUILDER.is_file() or not records.is_dir():
        pytest.skip("harness build_a6_attempts.py and records not present yet")
    checked = 0
    for record in sorted(records.glob("*__b0r*.txt")):
        task, first = record.stem.rsplit("__", 1)
        text = record.read_bytes().replace(b"\r\n", b"\n").decode("utf-8")
        match = RECORD_DIFF.search(text)
        assert match, record.name
        limit = int(match.group(1))
        run_dir = HARNESS / "runs" / "a5-main" / task / "b0" / ("r" + first[len("b0r") :])
        original = HARNESS / "runs" / "sprint5-main-images" / task / "staging" / "original"
        diff = diff_against(load_delta(run_dir), original).rstrip("\n")
        expected = head(diff, limit)[0] if diff else "none"
        assert match.group(2) == expected, record.name
        checked += 1
    assert checked == 53
