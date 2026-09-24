from pathlib import Path

import pytest

from reposkill_agent.eval.public_export import ExportFile, ExportManifest, export_public_workspace
from reposkill_agent.protocol.evaluation import EvaluationResult, EvaluationSpec, aggregate_results
from reposkill_agent.protocol.public import BoundaryError, decode_public_task, digest, safe_relative
from tests.upgrade_helpers import task


@pytest.mark.parametrize(
    "key", ["expected_files", "tags", "gold_patch", "hidden_tests", "category", "future_trajectory"]
)
def test_oracle_rejected_without_echo(key):
    payload = task().model_dump(mode="json")
    payload["extension"] = {"nested": [{key: "ORACLE_SENTINEL"}]}
    with pytest.raises(BoundaryError) as error:
        decode_public_task(payload)
    assert error.value.code == "oracle_field_present"
    assert "ORACLE_SENTINEL" not in str(error.value)


def test_schema_and_public_filename():
    payload = task(issue_text="Fix source/parser.py").model_dump(mode="json")
    payload["schema_version"] = "1.2"
    payload["future_optional"] = {"note": "IGNORED_SENTINEL"}
    decoded, audit = decode_public_task(payload)
    assert "source/parser.py" in decoded.issue_text
    assert "IGNORED_SENTINEL" not in decoded.model_dump_json() + str(audit)
    payload["schema_version"] = "2.0"
    with pytest.raises(BoundaryError, match="unsupported_schema_major"):
        decode_public_task(payload)
    payload["schema_version"] = "1.0"
    with pytest.raises(BoundaryError, match="unknown_public_field"):
        decode_public_task(payload)


@pytest.mark.parametrize(
    "path",
    [
        "../a",
        "/tmp/a",
        "a/../b",
        ".env",
        ".env.local",
        "C:/file",
        "a\\b",
        "foo:stream",
        "NUL.txt",
        "a.",
    ],
)
def test_paths_reject_cross_platform_aliases(path):
    with pytest.raises(ValueError):
        safe_relative(path)


def export_fixture(tmp_path: Path):
    root = tmp_path / "private-preparation"
    root.mkdir()
    (root / "parser.py").write_text("def parse_config(text): return text")
    (root / "private_test.py").write_text("ORACLE_SENTINEL")
    (root / ".env").write_text("SYNTHETIC_SECRET")
    manifest = ExportManifest(
        repo_id="fixture-repo",
        revision="v1",
        reviewed_public=True,
        files=(ExportFile(path="parser.py", sha256=digest((root / "parser.py").read_bytes())),),
    )
    return root, manifest


def test_export_gold_noninterference(tmp_path):
    root, manifest = export_fixture(tmp_path)
    outputs = []
    for index, gold in enumerate(["ORACLE_ONE", "ORACLE_TWO"]):
        private = EvaluationSpec(
            task_id="opaque-target",
            gold_patch=gold,
            expected_files=("answer.py",),
            tags=("memory_heavy",),
            hidden_test_refs=("private_test.py",),
        )
        target = tmp_path / f"public-{index}"
        outputs.append(export_public_workspace(root, target, task(), manifest, private))
        assert sorted(p.name for p in target.iterdir()) == ["parser.py"]
        assert gold not in str(outputs[-1])
    assert outputs[0] == outputs[1]


def test_export_fails_before_writing(tmp_path):
    root, manifest = export_fixture(tmp_path)
    private = EvaluationSpec(task_id="opaque-target", hidden_test_refs=("parser.py",))
    with pytest.raises(BoundaryError, match="private_or_duplicate"):
        export_public_workspace(root, tmp_path / "out", task(), manifest, private)
    assert not (tmp_path / "out").exists()
    private = EvaluationSpec(task_id="opaque-target")
    (root / "parser.py").write_text("changed")
    with pytest.raises(BoundaryError, match="export_content_changed"):
        export_public_workspace(root, tmp_path / "out", task(), manifest, private)
    with pytest.raises(BoundaryError, match="unsafe_export_destination"):
        export_public_workspace(root, root / "nested", task(), manifest, private)


def test_link_export_is_not_followed(tmp_path):
    root, manifest = export_fixture(tmp_path)
    (root / "parser.py").unlink()
    try:
        (root / "parser.py").symlink_to(root / "private_test.py")
    except OSError:
        pytest.skip("symlink creation not permitted on this host")
    with pytest.raises(BoundaryError, match="unsafe_export_path"):
        export_public_workspace(
            root, tmp_path / "out", task(), manifest, EvaluationSpec(task_id="opaque-target")
        )


def test_modes_and_zero_tests():
    good = EvaluationResult(
        task_id="a", protocol_mode="realistic", outcome="pass", collected=1, passed=1
    )
    bad_env = EvaluationResult(task_id="b", protocol_mode="realistic", outcome="invalid_env")
    assert aggregate_results([good, bad_env])["success_rate"] == 0.5
    with pytest.raises(ValueError, match="mixed_protocol"):
        aggregate_results([good, good.model_copy(update={"protocol_mode": "diagnostic_oracle"})])
    with pytest.raises(ValueError, match="unverified_pass"):
        aggregate_results([good.model_copy(update={"collected": 0})])


def test_ancestor_link_guard_without_windows_symlink_privilege(tmp_path, monkeypatch):
    from reposkill_agent.eval.public_export import checked_path

    root = tmp_path / "ancestor" / "source"
    root.mkdir(parents=True)
    (root / "source.py").write_text("public")
    original = Path.is_symlink
    monkeypatch.setattr(Path, "is_symlink", lambda p: p == root.parent or original(p))
    with pytest.raises(BoundaryError, match="unsafe_export_path"):
        checked_path(root, "source.py")


def test_private_directory_not_exported(tmp_path):
    root, manifest = export_fixture(tmp_path)
    (root / "private").mkdir()
    (root / "private" / "answers.py").write_text("ORACLE_SENTINEL")
    manifest = manifest.model_copy(
        update={
            "files": (ExportFile(path="private/answers.py", sha256=digest(b"ORACLE_SENTINEL")),)
        }
    )
    private = EvaluationSpec(task_id="opaque-target", hidden_test_refs=("private",))
    with pytest.raises(BoundaryError, match="private_or_duplicate"):
        export_public_workspace(root, tmp_path / "out", task(), manifest, private)
