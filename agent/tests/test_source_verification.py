import json

from reposkill_agent.memory.source_verification import load_source_verification

SOURCES = ("django__django-10914", "pytest-dev__pytest-5103")


def test_missing_file_marks_every_source_unverified(tmp_path):
    labels = load_source_verification(tmp_path / "missing.json", SOURCES)
    assert labels == {source: "unverified" for source in SOURCES}


def test_grader_scores_map_and_unknown_scores_stay_unverified(tmp_path):
    path = tmp_path / "memory-source-verification.json"
    path.write_text(
        json.dumps(
            {
                "results": [
                    {"source_id": "django__django-10914", "status": "pass"},
                    {"source_id": "pytest-dev__pytest-5103", "status": "grader_unavailable"},
                    {"source_id": "not-a-source", "status": "fail"},
                ]
            }
        ),
        encoding="utf-8",
    )
    labels = load_source_verification(path, SOURCES)
    assert labels["django__django-10914"] == "validated_fix"
    assert labels["pytest-dev__pytest-5103"] == "unverified"


def test_partial_and_fail_map(tmp_path):
    path = tmp_path / "scores.json"
    path.write_text(
        json.dumps(
            [
                {"source_id": "django__django-10914", "status": "partial"},
                {"source_id": "pytest-dev__pytest-5103", "status": "fail"},
            ]
        ),
        encoding="utf-8",
    )
    labels = load_source_verification(path, SOURCES)
    assert labels["django__django-10914"] == "partial_attempt"
    assert labels["pytest-dev__pytest-5103"] == "failed_attempt"
