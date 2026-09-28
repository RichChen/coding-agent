import hashlib
import json
import subprocess
import sys

import pytest

import scripts.build_clean_baseline as clean_baseline
from scripts.build_clean_baseline import source_only_check
from scripts.rewritten_sources import load_overrides, sed_rewrites

SPEC = {"pre_install": [
    "sed -i 's/pytest/pytest -rA/' tox.ini",
    "sed -i 's/Jinja2>=2.3/Jinja2<3.0/' setup.py",
    "sed -i 's/alabaster>=0.7,<0.8/alabaster>=0.7,<0.7.12/' setup.py",
    "sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen",
    "apt-get update && apt-get install -y graphviz",
]}
ORIGINAL = b"install_requires = ['Jinja2>=2.3', 'alabaster>=0.7,<0.8']\n"
REWRITTEN = b"install_requires = ['Jinja2<3.0', 'alabaster>=0.7,<0.7.12']\n"
OTHER = b"print('hello')\n"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def manifest():
    return {
        "source_tree_hash": "tree",
        "entries": {
            "setup.py": {"kind": "file", "sha256": sha(ORIGINAL)},
            "pkg/mod.py": {"kind": "file", "sha256": sha(OTHER)},
            "pkg": {"kind": "dir"},
        },
    }


@pytest.fixture
def repo(tmp_path, monkeypatch):
    root = tmp_path / "opt-repo"
    (root / "pkg").mkdir(parents=True)
    (root / "setup.py").write_bytes(REWRITTEN)
    (root / "pkg" / "mod.py").write_bytes(OTHER)

    def local_python(_digest, code, stdin=b""):
        code = code.replace('pathlib.Path("/opt/repo")', "pathlib.Path(" + repr(str(root)) + ")")
        return subprocess.run([sys.executable, "-c", code], input=stdin, stdout=subprocess.PIPE, check=True).stdout.decode()

    monkeypatch.setattr(clean_baseline, "docker_python", local_python)
    return root


def test_sed_rewrites_groups_commands_per_file_in_order():
    rewrites = sed_rewrites(SPEC)
    assert rewrites == {
        "tox.ini": [SPEC["pre_install"][0]],
        "setup.py": [SPEC["pre_install"][1], SPEC["pre_install"][2]],
    }


def test_override_file_with_expected_content_passes(repo):
    ok, value = source_only_check("image", manifest(), {"setup.py": sha(REWRITTEN)})
    assert ok and value == "tree"


def test_override_file_with_other_content_fails(repo):
    (repo / "setup.py").write_bytes(REWRITTEN + b"# edited\n")
    ok, value = source_only_check("image", manifest(), {"setup.py": sha(REWRITTEN)})
    assert not ok and value == "mismatch:1"


def test_file_outside_overrides_is_still_compared(repo):
    (repo / "pkg" / "mod.py").write_bytes(OTHER + b"# edited\n")
    ok, value = source_only_check("image", manifest(), {"setup.py": sha(REWRITTEN)})
    assert not ok and value == "mismatch:1"


def test_rewritten_file_without_override_fails(repo):
    ok, _value = source_only_check("image", manifest())
    assert not ok


def test_override_for_unknown_file_is_refused(repo):
    with pytest.raises(ValueError):
        source_only_check("image", manifest(), {"missing.cfg": sha(b"")})


def record(tmp_path, **changes):
    files = {
        "setup.py": {"commands": SPEC["pre_install"][1:3], "original_sha256": sha(ORIGINAL), "expected_sha256": sha(REWRITTEN)},
        "tox.ini": {"commands": SPEC["pre_install"][:1], "original_sha256": None, "expected_sha256": "t"},
    }
    for name, item in changes.items():
        files[name].update(item)
    (tmp_path / "task.json").write_text(json.dumps({"files": files}), encoding="utf-8")
    return tmp_path


def test_load_overrides_reads_the_record(tmp_path):
    overrides = load_overrides("task", SPEC, manifest(), folder=record(tmp_path))
    assert overrides == {"setup.py": sha(REWRITTEN), "tox.ini": "t"}


def test_load_overrides_refuses_other_commands(tmp_path):
    folder = record(tmp_path, **{"setup.py": {"commands": SPEC["pre_install"][1:2]}})
    with pytest.raises(SystemExit, match="commands"):
        load_overrides("task", SPEC, manifest(), folder=folder)


def test_load_overrides_refuses_another_original(tmp_path):
    folder = record(tmp_path, **{"setup.py": {"original_sha256": sha(b"other")}})
    with pytest.raises(SystemExit, match="original sha"):
        load_overrides("task", SPEC, manifest(), folder=folder)


def test_load_overrides_requires_a_record(tmp_path):
    with pytest.raises(SystemExit, match="no rewritten-expected record"):
        load_overrides("task", SPEC, manifest(), folder=tmp_path)


def test_no_rewrites_needs_no_record(tmp_path):
    assert load_overrides("task", {"pre_install": ["apt-get update"]}, manifest(), folder=tmp_path) == {}
