"""Source files that SWE-bench pre_install rewrites with sed, and the sha each must have afterwards.

The image build and the run both compare /opt/repo against the same overrides, so no file is skipped.
"""
from __future__ import annotations

import base64
import hashlib
import json
import subprocess
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = ROOT / "docs" / "sprint" / "rewritten-expected"
SCHEMA = "sprint6.rewritten-expected.v1"

REPLAY = r'''
import base64, hashlib, json, os, subprocess, sys
job = json.load(sys.stdin)
work = "/tmp/rewrite"
os.makedirs(work)
out = {}
for name, item in job.items():
    with open(os.path.join(work, name), "wb") as handle:
        handle.write(base64.b64decode(item["content"]))
    for command in item["commands"]:
        subprocess.run(["/bin/sh", "-c", command], cwd=work, check=True)
    with open(os.path.join(work, name), "rb") as handle:
        out[name] = hashlib.sha256(handle.read()).hexdigest()
print(json.dumps(out))
'''


def sed_rewrites(spec: dict) -> dict[str, list[str]]:
    """File -> the sed commands that rewrite it, in pre_install order."""
    rewrites: dict[str, list[str]] = {}
    for command in spec.get("pre_install") or []:
        parts = str(command).split()
        if parts and parts[0] == "sed" and "/" not in parts[-1]:
            rewrites.setdefault(parts[-1], []).append(str(command))
    return rewrites


def archive_files(archive: Path, repo: str, revision: str, names) -> dict[str, bytes]:
    prefix = repo.split("/")[1] + "-" + revision + "/"
    found = {}
    with tarfile.open(archive, "r:gz") as packed:
        for name in names:
            extracted = packed.extractfile(packed.getmember(prefix + name))
            found[name] = extracted.read()
    return found


def replay(digest: str, originals: dict[str, bytes], rewrites: dict[str, list[str]]) -> dict[str, str]:
    """Apply the sed commands inside the clean image, only on a /tmp tmpfs, with no network."""
    job = {
        name: {"content": base64.b64encode(data).decode("ascii"), "commands": rewrites[name]}
        for name, data in originals.items()
    }
    argv = [
        "docker", "--context", "desktop-linux", "run", "--rm", "-i", "--network", "none",
        "--read-only", "--tmpfs", "/tmp", digest, "/usr/local/bin/python", "-I", "-S", "-c", REPLAY,
    ]
    result = subprocess.run(argv, input=json.dumps(job).encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
    if result.returncode:
        raise RuntimeError(result.stderr.decode("utf-8", "replace")[-1000:])
    return json.loads(result.stdout.decode("utf-8"))


def write_expected(task: dict, spec: dict, digest: str, archive: Path) -> Path | None:
    rewrites = sed_rewrites(spec)
    if not rewrites:
        return None
    originals = archive_files(archive, task["repo"], task["base_commit"], sorted(rewrites))
    expected = replay(digest, originals, rewrites)
    row = {
        "schema": SCHEMA,
        "task_id": task["id"],
        "clean_image_digest": digest,
        "files": {
            name: {
                "commands": rewrites[name],
                "original_sha256": hashlib.sha256(originals[name]).hexdigest(),
                "expected_sha256": expected[name],
            }
            for name in sorted(rewrites)
        },
    }
    EXPECTED.mkdir(parents=True, exist_ok=True)
    path = EXPECTED / (task["id"] + ".json")
    path.write_text(json.dumps(row, indent=2) + "\n", encoding="utf-8")
    return path


def load_overrides(task_id: str, spec: dict, manifest: dict, folder: Path | None = None) -> dict[str, str]:
    """Path -> expected sha for every file pre_install rewrites. Refuses a record that does not match the spec or archive."""
    rewrites = sed_rewrites(spec)
    if not rewrites:
        return {}
    path = (folder or EXPECTED) / (task_id + ".json")
    if not path.is_file():
        raise SystemExit("no rewritten-expected record for " + task_id)
    row = json.loads(path.read_text(encoding="utf-8"))
    files = row.get("files") or {}
    if sorted(files) != sorted(rewrites):
        raise SystemExit("rewritten-expected files for " + task_id + " differ from pre_install")
    overrides = {}
    for name, item in files.items():
        if item.get("commands") != rewrites[name]:
            raise SystemExit("rewritten-expected commands for " + task_id + " " + name + " differ from pre_install")
        original = (manifest["entries"].get(name) or {}).get("sha256")
        if item.get("original_sha256") != original:
            raise SystemExit("rewritten-expected original sha for " + task_id + " " + name + " differs from the archive")
        overrides[name] = item["expected_sha256"]
    return overrides


def overrides_for(task: dict, manifest: dict) -> dict[str, str]:
    """Pool tasks carry a SWE-bench version. Pilot tasks do not, and their images rewrite nothing."""
    if not task.get("version"):
        return {}
    from scripts.swebench_specs import spec_row
    return load_overrides(task["id"], spec_row(task["repo"], task["version"]), manifest)
