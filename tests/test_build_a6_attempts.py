import base64
import hashlib
import json

import pytest

from scripts import build_a6_attempts as b

SECRET_TEST = "def test_hidden_regression_case():"
SECRET_ASSERT = "assert compute_widget(3) == 'expected-widget-value'"
SECRET_GOLD = "return widget_cache.lookup(value, default=None)"
SECRET_NEW_FILE = "tests/test_hidden_new_module.py"


def _b64(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def _messages(command_output: str, final: str = "I changed compute_widget and stopped."):
    call = {"id": "call_1", "type": "function", "function": {"name": "run_command", "arguments": json.dumps({"command": "python -m pytest tests/test_widget.py"})}}
    other = {"id": "call_2", "type": "function", "function": {"name": "run_command", "arguments": json.dumps({"command": "ls"})}}
    return [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "issue"},
        {"role": "assistant", "content": "", "tool_calls": [other]},
        {"role": "tool", "tool_call_id": "call_2", "content": "pkg\ntests\n"},
        {"role": "assistant", "content": "Running the tests.", "tool_calls": [call]},
        {"role": "tool", "tool_call_id": "call_1", "content": command_output},
        {"role": "assistant", "content": final},
    ]


def _run(root, task, slot, *, solved=False, status="fail", delta=None, messages=None, artifact=False, events=True):
    run_dir = root / task / "b0" / slot
    run_dir.mkdir(parents=True)
    delta = delta if delta is not None else {"changed": {}, "deleted": []}
    changed = sorted(list(delta.get("changed") or {}) + list(delta.get("deleted") or []))
    summary = {"task_id": task, "variant": "B0", "mock": False, "profile": "b0-v2", "solved": solved, "status": status,
               "stop_reason": "max_model_calls", "model_calls": 40, "changed_files": changed, "prompt_sha256": "p" * 64}
    (run_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    (run_dir / "candidate-delta.json").write_text(json.dumps(delta), encoding="utf-8")
    (run_dir / "grader-result.json").write_text("not json: the builder must never read this", encoding="utf-8")
    if events:
        payload = {"messages": messages or _messages("1 passed\n")}
        if artifact:
            data = json.dumps(payload).encode("utf-8")
            sha = hashlib.sha256(data).hexdigest()
            (run_dir / "session" / "artifacts").mkdir(parents=True)
            (run_dir / "session" / "artifacts" / sha).write_bytes(data)
            payload = {"artifact_ref": {"path": sha, "sha256": sha}}
        lines = [{"event_type": "run.started", "payload": {}}, {"event_type": "state.saved", "payload": {"messages": []}},
                 {"event_type": "state.saved", "payload": payload}]
        (run_dir / "events.jsonl").write_text("\n".join(json.dumps(line) for line in lines) + "\n", encoding="utf-8")
    return run_dir


@pytest.fixture
def world(tmp_path):
    a5 = tmp_path / "a5-main"
    images = tmp_path / "images"
    calibration = tmp_path / "calibration"
    calibration.mkdir()
    original = images / "pkg__pkg-1" / "staging" / "original"
    (original / "pkg").mkdir(parents=True)
    (original / "tests").mkdir(parents=True)
    (original / "pkg" / "widget.py").write_bytes(b"def compute_widget(x):\r\n    return x\r\n")
    (original / "pkg" / "old.py").write_text("gone = True\n", encoding="utf-8")
    (original / "tests" / "test_widget.py").write_text("def test_widget():\n    assert True\n", encoding="utf-8")
    images.joinpath("pkg__pkg-2", "staging", "original").mkdir(parents=True)
    delta = {"changed": {"tests/test_widget.py": _b64("def test_widget():\n    assert False\n"),
                         "pkg/widget.py": _b64("def compute_widget(x):\n    return x + 1\n"),
                         "pkg/new.py": {"content": _b64("NEW = 1\n")}},
             "deleted": ["pkg/old.py"]}
    _run(a5, "pkg__pkg-1", "r1", delta=delta)
    _run(a5, "pkg__pkg-1", "r2", solved=True, status="pass")
    _run(a5, "pkg__pkg-1", "r3", status="infra_error")
    _run(a5, "pkg__pkg-1", "r4")
    _run(a5, "pkg__pkg-1", "r1.infra1")
    _run(a5, "pkg__pkg-2", "r2", artifact=True)
    private = tmp_path / "private.json"
    private.write_text(json.dumps({
        "FAIL_TO_PASS": json.dumps(["tests/test_widget.py::test_hidden_regression_case"]),
        "PASS_TO_PASS": json.dumps(["tests/test_widget.py::test_widget_basic_case"]),
        "test_patch": "diff --git a/tests/test_widget.py b/tests/test_widget.py\n--- a/tests/test_widget.py\n+++ b/tests/test_widget.py\n"
                      "@@ -1 +1,3 @@\n+" + SECRET_TEST + "\n+    " + SECRET_ASSERT + "\n"
                      "diff --git a/" + SECRET_NEW_FILE + " b/" + SECRET_NEW_FILE + "\nnew file mode 100644\n--- /dev/null\n+++ b/" + SECRET_NEW_FILE + "\n",
        "patch": "diff --git a/pkg/widget.py b/pkg/widget.py\n--- a/pkg/widget.py\n+++ b/pkg/widget.py\n@@ -1 +1 @@\n+    " + SECRET_GOLD + "\n",
    }), encoding="utf-8")
    targets = {task: {"id": task, "repo": "pkg/pkg", "private": str(private)} for task in ("pkg__pkg-1", "pkg__pkg-2")}
    return {"a5": a5, "images": images, "calibration": calibration, "targets": targets, "tmp": tmp_path}


def _build(world, name="out", expected=(2, 2)):
    out = world["tmp"] / name
    return b.build(a5_root=world["a5"], images_root=world["images"], calibration_root=world["calibration"], targets=world["targets"],
                   out_dir=out / "attempts", manifest_path=out / "a6-attempts.json", log_path=out / "leak.json", expected=expected), out


def _files(out):
    return {path.relative_to(out).as_posix(): path.read_bytes() for path in sorted(out.rglob("*")) if path.is_file()}


def test_selection_uses_only_failed_r1_to_r3(world):
    rows = b.select_first_attempts(world["a5"])
    assert [(row["task"], row["first"]) for row in rows] == [("pkg__pkg-1", "b0r1"), ("pkg__pkg-2", "b0r2")]


def test_recount_mismatch_stops(world):
    with pytest.raises(SystemExit, match="recount 2 runs on 2 tasks, expected 53 on 22"):
        _build(world, expected=(53, 22))


def test_two_builds_are_byte_identical(world):
    first, out_a = _build(world, "a")
    second, out_b = _build(world, "b")
    files_a, files_b = _files(out_a), _files(out_b)
    assert first["records"] and set(files_a) == set(files_b)
    for name in files_a:
        if name == "a6-attempts.json":
            assert files_a[name].replace(b"/a/", b"/x/") == files_b[name].replace(b"/b/", b"/x/")
        else:
            assert files_a[name] == files_b[name], name


def test_record_layout_and_diff_normalization(world):
    manifest, out = _build(world)
    text = (out / "attempts" / "pkg__pkg-1__b0r1.txt").read_text(encoding="utf-8")
    assert text.startswith("<previous_attempt>\nThe following is a record of one earlier attempt")
    assert text.endswith("</previous_attempt>")
    assert "Stop reason: max_model_calls; model calls used: 40/40.\n" in text
    assert "Files changed: pkg/new.py, pkg/old.py, pkg/widget.py\n" in text
    assert "\r" not in text
    diff = text.split("bytes):\n", 1)[1].split("\n\nLast test-like", 1)[0]
    assert diff.index("+++ b/pkg/new.py") < diff.index("--- a/pkg/old.py") < diff.index("+++ b/pkg/widget.py") < diff.index("+++ b/tests/test_widget.py")
    assert "--- /dev/null" in diff and "+++ /dev/null" in diff
    assert "-    return x\n+    return x + 1" in diff
    assert "$ python -m pytest tests/test_widget.py\n1 passed" in text
    assert "$ ls" not in text
    assert "Agent's final message (truncated):\nI changed compute_widget and stopped.\n</previous_attempt>" in text
    row = manifest["records"][0]
    assert row["bytes"] == len(text.encode("utf-8")) == sum(row["sections"].values())
    assert row["sha256"] == hashlib.sha256(text.encode("utf-8")).hexdigest()
    assert b.load_record(row) == text


def test_no_source_change_is_written_as_none(world):
    _, out = _build(world)
    text = (out / "attempts" / "pkg__pkg-2__b0r2.txt").read_text(encoding="utf-8")
    assert "Files changed: none (no source changes were submitted)\n" in text
    assert "bytes):\nnone\n" in text


def test_missing_event_log_is_an_error(world):
    _run(world["a5"], "pkg__pkg-3", "r1", events=False)
    world["targets"]["pkg__pkg-3"] = dict(world["targets"]["pkg__pkg-1"], id="pkg__pkg-3")
    with pytest.raises(ValueError, match="events.jsonl missing"):
        _build(world, expected=(3, 3))


def test_long_parts_are_truncated_within_the_limits(world):
    big = "\n".join("line %05d of a very long and noisy test output" % i for i in range(2000))
    huge = "".join("value_%05d = %d\n" % (i, i) for i in range(3000))
    _run(world["a5"], "pkg__pkg-3", "r1", delta={"changed": {"pkg/huge.py": _b64(huge)}, "deleted": []},
         messages=_messages(big, final="x" * 5000))
    world["targets"]["pkg__pkg-3"] = dict(world["targets"]["pkg__pkg-1"], id="pkg__pkg-3")
    world["images"].joinpath("pkg__pkg-3", "staging", "original").mkdir(parents=True)
    manifest, out = _build(world, expected=(3, 3))
    row = next(row for row in manifest["records"] if row["task"] == "pkg__pkg-3")
    text = (out / "attempts" / "pkg__pkg-3__b0r1.txt").read_text(encoding="utf-8")
    assert row["bytes"] == b.TOTAL_LIMIT
    assert row["truncated"] == {"diff": True, "commands": 1, "message": True}
    assert row["diff_limit"] >= b.DIFF_MIN and row["sections"]["commands"] <= b.COMMAND_LIMIT + 200
    assert "\n[truncated]\n\nLast test-like" in text and "$ python -m pytest tests/test_widget.py\n[truncated]\n" in text
    assert "line 01999 of a very long and noisy test output" in text


def test_leak_check_counts_without_writing_private_text(world):
    leaky = _messages("FAILED " + "tests/test_widget.py::test_hidden_regression_case\n" + SECRET_NEW_FILE + "\n")
    delta = {"changed": {"tests/test_widget.py": _b64(SECRET_TEST + "\n    " + SECRET_ASSERT + "\n"),
                         "pkg/widget.py": _b64("def compute_widget(x):\n    " + SECRET_GOLD + "\n")}, "deleted": []}
    _run(world["a5"], "pkg__pkg-3", "r1", delta=delta, messages=leaky)
    world["targets"]["pkg__pkg-3"] = dict(world["targets"]["pkg__pkg-1"], id="pkg__pkg-3")
    world["images"].joinpath("pkg__pkg-3", "staging", "original").mkdir(parents=True)
    manifest, out = _build(world, expected=(3, 3))
    row = next(row for row in manifest["records"] if row["task"] == "pkg__pkg-3")
    assert row["leak"]["ids"] >= 2 and row["leak"]["test_patch_lines"] == 2
    assert row["leak"]["test_patch_new_files"] == 1 and row["leak"]["gold_patch_lines"] == 1
    assert manifest["leak_blocking"] is True
    clean = next(row for row in manifest["records"] if row["task"] == "pkg__pkg-2")
    assert clean["leak"] == {"ids": 0, "test_patch_lines": 0, "test_patch_new_files": 0, "gold_patch_lines": 0}
    log = (out / "leak.json").read_text(encoding="utf-8")
    written = (out / "a6-attempts.json").read_text(encoding="utf-8") + log
    for secret in (SECRET_TEST, SECRET_ASSERT, SECRET_GOLD, SECRET_NEW_FILE, "test_hidden_regression_case"):
        assert secret not in written
    hits = json.loads(log)["records"][-1]["hits"]
    assert {hit["section"] for hit in hits} >= {"diff", "commands"}
    assert {hit.get("diff_line") for hit in hits if hit["section"] == "diff"} == {"added"}


def test_template_hash_is_stable():
    assert b.template_sha256() == b.template_sha256()
    assert len(b.SECTIONS) == 7 and b.SECTIONS[0][1].startswith("<previous_attempt>\n")
