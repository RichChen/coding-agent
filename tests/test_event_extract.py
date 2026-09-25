import base64
import json
from pathlib import Path

import pytest

from reposkill_agent.memory.event_extract import extract_source, locate_events

SNAPSHOT = Path(
    "D:/crq/src/coding-harness/docs/upgrade/evidence/"
    "A5-real240-77-harness-preflight/memory-snapshot.jsonl"
)
TARGETS = Path("configs/a5/pilot20-harness-consumption-manifest.json")
PRIVATE = Path("benchmarks/a5/pilot20-source-v1/private/test.parquet")


def _write_run(root: Path, events: list[dict]) -> None:
    run = root / "run"
    (run / "session" / "artifacts").mkdir(parents=True, exist_ok=True)
    (run / "events.jsonl").write_text(
        "\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8"
    )


def test_extracts_commands_reads_and_artifact_diagnosis(tmp_path):
    artifact = {"messages": [{"role": "assistant", "content": "The bug is caused by visit_Call dropping the scope. Fix visit_Call."}]}
    (tmp_path / "run" / "session" / "artifacts").mkdir(parents=True)
    (tmp_path / "run" / "session" / "artifacts" / "msg1").write_text(json.dumps(artifact), encoding="utf-8")
    _write_run(
        tmp_path,
        [
            {
                "event_type": "tool.intent",
                "payload": {"name": "read_file", "arguments": {"path": "pkg/a.py", "offset": 10, "limit": 5}},
            },
            {
                "event_type": "tool.intent",
                "payload": {"name": "run_command", "arguments": {"command": "cd /workspace && python -m pytest tests/test_a.py -q"}},
            },
            {
                "event_type": "tool.intent",
                "payload": {"name": "run_command", "arguments": {"command": "cd /workspace && git status"}},
            },
            {
                "event_type": "tool.intent",
                "payload": {
                    "name": "search_replace",
                    "arguments": {
                        "path": "pkg/a.py",
                        "search": "def visit_Call(self):\n    return node",
                        "replace": "def visit_Call(self):\n    return self.scope(node)",
                    },
                },
            },
            {
                "event_type": "state.saved",
                "payload": {"artifact_ref": {"path": "msg1", "media_type": "application/json"}},
            },
        ],
    )
    (tmp_path / "candidate-delta.json").write_text(
        json.dumps({"changed": {"pkg/a.py": {"content": "class Rewriter:\n    def visit_Call(self):\n        return self.scope(node)\n"}}}),
        encoding="utf-8",
    )
    extracted = extract_source(tmp_path, "example-1")
    assert extracted.events_found
    assert extracted.reads[0].path == "pkg/a.py"
    assert extracted.reads[0].start == 10
    assert extracted.reads[0].end == 14
    assert extracted.commands == ("cd /workspace && python -m pytest tests/test_a.py -q",)
    assert any("visit_Call" in name for name in extracted.changed_symbols)
    assert "caused by" in extracted.diagnosis
    assert extracted.final_answer


def test_missing_events_are_recorded(tmp_path):
    extracted = extract_source(tmp_path, "missing")
    assert extracted.events_found is False
    assert extracted.skipped == ("events_jsonl_missing",)


def test_missing_artifact_is_skipped(tmp_path):
    _write_run(
        tmp_path,
        [{"event_type": "state.saved", "payload": {"artifact_ref": {"path": "gone", "media_type": "application/json"}}}],
    )
    extracted = extract_source(tmp_path, "gone")
    assert extracted.events_found
    assert any(item.startswith("artifact_missing") for item in extracted.skipped)


@pytest.mark.skipif(not SNAPSHOT.is_file() or not PRIVATE.is_file(), reason="source pool not on this machine")
def test_real_extractions_exclude_target_gold():
    import pyarrow.parquet as pq

    targets = json.loads(TARGETS.read_text(encoding="utf-8"))["targets"]
    table = pq.read_table(PRIVATE, columns=["instance_id", "patch", "test_patch", "FAIL_TO_PASS"])
    rows = {row["instance_id"]: row for row in table.to_pylist()}
    sentinels = []
    for target in targets:
        row = rows[target]
        for column in ("patch", "test_patch", "FAIL_TO_PASS"):
            for line in str(row[column]).splitlines():
                if line.startswith("+") and not line.startswith("+++"):
                    snippet = line[1:].strip()
                    if len(snippet) >= 80:
                        sentinels.append((target, snippet))
                        break
    blobs = []
    for line in SNAPSHOT.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        extracted = extract_source(Path(row["source_dir"]), row["source_id"])
        assert extracted.events_found
        blob = "\n".join(
            (
                extracted.diagnosis,
                extracted.final_answer,
                "\n".join(extracted.commands),
                " ".join(extracted.changed_symbols),
            )
        )
        blobs.append(blob)
        for target in targets:
            assert target not in blob
    joined = "\n".join(blobs)
    for target, snippet in sentinels:
        assert snippet not in joined, target


def _sprint_events(root: Path, events: list[dict]) -> None:
    (root / "session" / "artifacts").mkdir(parents=True)
    (root / "events.jsonl").write_text(
        "\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8"
    )


def test_sprint_layout_decodes_base64_delta(tmp_path):
    _sprint_events(
        tmp_path,
        [
            {
                "event_type": "tool.intent",
                "payload": {"name": "read_file", "arguments": {"path": "pkg/a.py", "offset": 1, "limit": 4}},
            },
            {
                "event_type": "tool.intent",
                "payload": {"name": "run_command", "arguments": {"command": "python -m pytest tests/test_a.py -q"}},
            },
            {
                "event_type": "tool.intent",
                "payload": {
                    "name": "search_replace",
                    "arguments": {
                        "path": "pkg/a.py",
                        "search": "def visit_Call(self):\n    return node",
                        "replace": "def visit_Call(self):\n    return self.scope(node)",
                    },
                },
            },
        ],
    )
    content = "class Rewriter:\n    def visit_Call(self):\n        return self.scope(node)\n"
    (tmp_path / "candidate-delta.json").write_text(
        json.dumps({"changed": {"pkg/a.py": base64.b64encode(content.encode()).decode()}}),
        encoding="utf-8",
    )
    events, artifacts = locate_events(tmp_path)
    assert events == tmp_path / "events.jsonl"
    assert artifacts == tmp_path / "session" / "artifacts"
    extracted = extract_source(tmp_path, "sprint-1")
    assert extracted.reads[0].path == "pkg/a.py"
    assert extracted.commands == ("python -m pytest tests/test_a.py -q",)
    assert any("visit_Call" in name for name in extracted.changed_symbols)


def test_bad_base64_is_recorded(tmp_path):
    _sprint_events(tmp_path, [])
    (tmp_path / "candidate-delta.json").write_text(
        json.dumps({"changed": {"pkg/a.py": "not-valid-base64!!!"}}),
        encoding="utf-8",
    )
    extracted = extract_source(tmp_path, "bad-b64", layout="sprint")
    assert any(item.startswith("delta_base64_decode_failed") for item in extracted.skipped)


def test_ambiguous_layout_is_an_error(tmp_path):
    _write_run(tmp_path, [])
    _sprint_events(tmp_path, [])
    with pytest.raises(ValueError, match="ambiguous_event_layout"):
        extract_source(tmp_path, "both")


SPRINT2 = Path("D:/crq/src/coding-harness/runs/sprint2-b0")


@pytest.mark.skipif(not (SPRINT2 / "django__django-11039" / "events.jsonl").is_file(), reason="sprint2-b0 not present")
def test_real_sprint_11039_has_reads_commands_and_symbols():
    extracted = extract_source(SPRINT2 / "django__django-11039", "django__django-11039", layout="sprint")
    assert extracted.events_found
    assert extracted.reads
    assert extracted.commands
    assert extracted.changed_symbols


@pytest.mark.skipif(not (SPRINT2 / "sympy__sympy-11400" / "events.jsonl").is_file(), reason="sprint2-b0 not present")
def test_real_sprint_11400_names_print_sinc():
    extracted = extract_source(SPRINT2 / "sympy__sympy-11400", "sympy__sympy-11400", layout="sprint")
    assert extracted.reads
    assert extracted.commands
    assert any("_print_sinc" in name for name in extracted.changed_symbols)
