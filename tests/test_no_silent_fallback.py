import json

import pytest

from scripts import run_a5_main
from scripts.run_swe_task import grader_spec, issue_text, public_issue
from scripts.select_main_targets import issue_sha256, public_record

ISSUE = "Title\n\n  body with trailing spaces   \n"
TASK = {"id": "django__django-1", "repo": "django/django", "base_commit": "abc123", "family": "django"}


def _public(tmp_path, **fields):
    data = {"issue_text": ISSUE, "repo_ref": {"repo_id": "django/django", "revision": "abc123"}}
    data.update(fields)
    path = tmp_path / "public.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return {**TASK, "public_task": str(path)}


def test_prompt_contains_issue_verbatim(tmp_path):
    prompt = public_issue(_public(tmp_path))
    assert prompt.endswith("Public issue:\n" + ISSUE)
    assert "Repository: django/django\nBase revision: abc123\n" in prompt
    assert "python tests/runtests.py <module>" in prompt


@pytest.mark.parametrize("issue", ["", "   \n", None, "Public issue for django__django-1"])
def test_prompt_refuses_empty_or_placeholder_issue(tmp_path, issue):
    with pytest.raises(ValueError):
        public_issue(_public(tmp_path, issue_text=issue))


@pytest.mark.parametrize("ref", [None, {}, {"repo_id": "django/django"}, {"revision": "abc123"}])
def test_prompt_refuses_missing_repo_or_revision(tmp_path, ref):
    with pytest.raises(ValueError):
        public_issue(_public(tmp_path, repo_ref=ref))


def test_prompt_refuses_unknown_family(tmp_path):
    task = _public(tmp_path)
    task.pop("family")
    with pytest.raises(ValueError):
        public_issue(task)


def test_issue_text_used_for_cards_is_strict():
    assert issue_text({"issue_text": ISSUE}) == ISSUE
    with pytest.raises(ValueError):
        issue_text({})


def test_public_record_keeps_issue_verbatim():
    row = {"instance_id": "django__django-1", "repo": "django/django", "base_commit": "abc123",
           "problem_statement": ISSUE, "hints_text": "HINT", "patch": "GOLD"}
    record = public_record(row)
    assert record["issue_text"] == ISSUE
    assert record["issue_sha256"] == issue_sha256(ISSUE)
    assert "HINT" not in json.dumps(record) and "GOLD" not in json.dumps(record)
    with pytest.raises(ValueError):
        public_record({**row, "problem_statement": ""})


def _checked(tmp_path, monkeypatch, *, write=True, text=ISSUE, recorded=None):
    root = tmp_path / "public"
    root.mkdir()
    issues = tmp_path / "main-issues.json"
    issues.write_text(json.dumps({"tasks": {TASK["id"]: {"issue_sha256": recorded or issue_sha256(ISSUE)}}}), encoding="utf-8")
    if write:
        record = {"issue_text": text, "issue_sha256": issue_sha256(text),
                  "repo_ref": {"repo_id": "django/django", "revision": "abc123"}}
        (root / (TASK["id"] + ".json")).write_text(json.dumps(record), encoding="utf-8")
    monkeypatch.setattr(run_a5_main, "PUBLIC_ROOT", root)
    monkeypatch.setattr(run_a5_main, "ISSUES", issues)
    return run_a5_main.checked_public(TASK)


def test_checked_public_accepts_matching_file(tmp_path, monkeypatch):
    assert _checked(tmp_path, monkeypatch).name == TASK["id"] + ".json"


def test_checked_public_refuses_missing_file(tmp_path, monkeypatch):
    with pytest.raises(SystemExit, match="public file missing"):
        _checked(tmp_path, monkeypatch, write=False)


def test_checked_public_refuses_empty_issue(tmp_path, monkeypatch):
    with pytest.raises(SystemExit, match="no issue_text"):
        _checked(tmp_path, monkeypatch, text="")


def test_checked_public_refuses_sha_mismatch(tmp_path, monkeypatch):
    with pytest.raises(SystemExit, match="issue sha"):
        _checked(tmp_path, monkeypatch, recorded="0" * 64)


@pytest.mark.parametrize("binding", [{}, {"test_patch_paths": [], "gold_patch_paths": ["a.py"]},
                                     {"test_patch_paths": ["t.py"], "gold_patch_paths": []}])
def test_grader_spec_refuses_missing_patch_paths(tmp_path, binding):
    private = tmp_path / "private.json"
    private.write_text(json.dumps({"instance_id": TASK["id"]}), encoding="utf-8")
    receipt = tmp_path / "receipt.json"
    receipt.write_text(json.dumps({"private_source_binding": {"path": str(private), **binding}}), encoding="utf-8")
    with pytest.raises(ValueError, match="patch_paths"):
        grader_spec({**TASK, "receipt": str(receipt), "grader_timeout_seconds": 600})
