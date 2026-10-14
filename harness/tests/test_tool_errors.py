from src.eval.tool_errors import harness_tool_errors, tool_exception, tool_schemas, traceback_exception

PY36_FAILURE = (
    "[stderr]\nTraceback (most recent call last):\n  File \"<string>\", line 10, in <module>\n"
    "AttributeError: 'PosixPath' object has no attribute 'is_relative_to'\n\n"
    "[exit_code=1 status=failed truncated=false bytes_seen=144 bytes_kept=144 cleanup=not_required duration_ms=600]\n"
    "Error: nonzero_exit"
)


def _tb(line):
    return "[stderr]\nTraceback (most recent call last):\n  File \"<string>\", line 5, in <module>\n" + line + "\n\nError: nonzero_exit"


def test_reads_the_exception_class_not_the_trailing_error_line():
    assert traceback_exception(PY36_FAILURE) == "AttributeError"
    assert traceback_exception("[stdout]\nfine\n") is None


def test_chained_traceback_uses_the_last_exception():
    text = _tb("KeyError: 'x'") + "\nDuring handling of the above exception, another exception occurred:\n\n" + _tb("TypeError: bad")
    assert traceback_exception(text) == "TypeError"


def test_counts_implementation_errors_of_harness_tools_only():
    schemas = tool_schemas()
    assert tool_exception("search_code", PY36_FAILURE, {"pattern": "x"}, schemas["search_code"]) == "AttributeError"
    assert tool_exception("read_file", _tb("ImportError: no module"), {"path": "a.py"}, schemas["read_file"]) == "ImportError"
    assert tool_exception("run_command", _tb("ModuleNotFoundError: No module named 'x'"), {"command": "python t.py"}) is None


def test_normal_tool_failures_do_not_count():
    schemas = tool_schemas()
    for line in ["ValueError: path denied", "FileNotFoundError: [Errno 2] No such file",
                 "ValueError: search string not found", "IsADirectoryError: [Errno 21]",
                 "UnicodeDecodeError: 'utf-8' codec can't decode"]:
        assert tool_exception("read_file", _tb(line), {"path": "a.py"}, schemas["read_file"]) is None


def test_invalid_arguments_do_not_count():
    schemas = tool_schemas()
    bad_type = {"path": "a.txt", "content": ["not", "a", "string"]}
    assert tool_exception("write_file", _tb("AttributeError: 'list' object has no attribute 'encode'"), bad_type, schemas["write_file"]) is None
    assert tool_exception("search_replace", _tb("TypeError: x"), {"path": "a.txt"}, schemas["search_replace"]) is None


def test_harness_tool_errors_pairs_results_with_intents():
    events = [
        {"event_type": "tool.intent", "tool_call_id": "c1", "payload": {"name": "search_code", "arguments": {"pattern": "x"}}},
        {"event_type": "tool.result", "tool_call_id": "c1", "payload": {"name": "search_code", "output": PY36_FAILURE}},
        {"event_type": "tool.intent", "tool_call_id": "c2", "payload": {"name": "run_command", "arguments": {"command": "x"}}},
        {"event_type": "tool.result", "tool_call_id": "c2", "payload": {"name": "run_command", "output": PY36_FAILURE}},
    ]
    assert harness_tool_errors(events, tool_schemas()) == [{"tool": "search_code", "call_id": "c1", "exception": "AttributeError"}]
