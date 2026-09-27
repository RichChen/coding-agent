"""Build and calibrate main-pool images. No model calls."""
from __future__ import annotations

import asyncio
import base64
import json
import shutil
import sys
import tarfile
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_clean_baseline import filesystem_scan, source_only_check  # noqa: E402
from scripts.calibrate_clean_image import counts, sklearn_import  # noqa: E402
from scripts.preflight_a5_repo_baseline import image_build, patch_paths  # noqa: E402
from scripts.run_swe_task import django_nodeids, parse_id_list, prefix_sympy_nodeids, usable_nodeid  # noqa: E402
from scripts.swebench_specs import fetch_requirements, install_commands, spec_row  # noqa: E402
from src.eval.a5_image_tree import archive_manifest  # noqa: E402
from src.eval.image_grader import ImageGrader  # noqa: E402

WORK = ROOT / "runs" / "sprint5-main-images"
CLEAN = ROOT / "docs" / "sprint" / "clean-images"
CAL = ROOT / "docs" / "sprint" / "main-calibration"
BASE = {
    "3.5": "python:3.5.10-slim-buster",
    "3.6": "python:3.6.15-slim-buster",
    "3.8": "python:3.8-slim-bookworm",
    "3.9": "python:3.9-slim-bookworm",
    "3.11": "python:3.11-slim-bookworm",
}
FAMILY = {
    "django/django": "django",
    "sympy/sympy": "sympy",
    "scikit-learn/scikit-learn": "scikit-learn",
    "sphinx-doc/sphinx": "sphinx-doc",
    "pytest-dev/pytest": "pytest-dev",
}


def download_archive(task: dict, dest: Path) -> None:
    if dest.is_file() and dest.stat().st_size > 0:
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    url = "https://github.com/" + task["repo"] + "/archive/" + task["base_commit"] + ".tar.gz"
    tmp = dest.with_suffix(".tar.gz.partial")
    with urllib.request.urlopen(url, timeout=120) as response, tmp.open("wb") as out:
        shutil.copyfileobj(response, out)
    stamped = dest.with_suffix(".tar.gz.stamped")
    with tarfile.open(tmp, "r:gz") as incoming, tarfile.open(
        stamped, "w:gz", format=tarfile.PAX_FORMAT, pax_headers={"comment": task["base_commit"]},
    ) as outgoing:
        for member in incoming:
            if member.isfile():
                outgoing.addfile(member, incoming.extractfile(member))
            else:
                outgoing.addfile(member)
    tmp.unlink()
    stamped.replace(dest)


def dockerfile(task: dict, base: str, install: str, native: str, requirements: bool) -> str:
    copy_req = "COPY swebench-requirements.txt /tmp/swebench-requirements.txt\n" if requirements else ""
    return (
        f"FROM {base}\n" + native +
        "COPY original-files.json /tmp/original-files.json\n"
        "COPY source.tar.gz /tmp/source.tar.gz\n" + copy_req +
        "RUN /usr/local/bin/python - <<'PY'\n"
        "import pathlib, shutil, tarfile\n"
        "root = pathlib.Path('/workspace')\n"
        "if root.exists():\n"
        "    shutil.rmtree(root)\n"
        "root.mkdir(parents=True)\n"
        "with tarfile.open('/tmp/source.tar.gz') as archive:\n"
        "    for member in archive.getmembers():\n"
        "        name = member.name.split('/', 1)[1] if '/' in member.name else ''\n"
        "        if not name:\n"
        "            continue\n"
        "        member.name = name\n"
        "        archive.extract(member, str(root))\n"
        "pathlib.Path('/tmp/source.tar.gz').unlink()\n"
        "PY\n"
        "WORKDIR /workspace\n"
        f"RUN {install}\n"
        "RUN /usr/local/bin/python - <<'PY'\n"
        "import json, pathlib\n"
        "root = pathlib.Path('/workspace')\n"
        "original = set(json.loads(pathlib.Path('/tmp/original-files.json').read_text()))\n"
        "found = []\n"
        "for path in root.rglob('*.so'):\n"
        "    if path.is_file() and not path.is_symlink():\n"
        "        rel = path.relative_to(root).as_posix()\n"
        "        if rel not in original:\n"
        "            found.append(rel)\n"
        "pathlib.Path('/opt/native-artifacts.json').write_text(json.dumps(sorted(found)))\n"
        "PY\n"
        "RUN mkdir -p /opt/repo && cp -a /workspace/. /opt/repo/ && rm -rf /workspace /tmp/original-files.json && mkdir /workspace\n"
        "RUN /usr/local/bin/python -m pip freeze --all > /opt/grader-environment.txt\n"
        "ENV PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=/workspace:/workspace/src\n"
    )


def build_image(task: dict, archive: Path, manifest: dict) -> dict:
    family = FAMILY[task["repo"]]
    spec = spec_row(task["repo"], task["version"])
    base = BASE.get(str(spec.get("python")))
    if not base:
        raise RuntimeError("no base image for python " + str(spec.get("python")))
    work = WORK / task["id"] / "context"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    shutil.copy2(archive, work / "source.tar.gz")
    files = sorted(path for path, meta in manifest["entries"].items() if meta.get("kind") == "file")
    (work / "original-files.json").write_text(json.dumps(files), encoding="utf-8")
    requirements = spec.get("packages") == "requirements.txt"
    if requirements:
        (work / "swebench-requirements.txt").write_text(
            fetch_requirements(task["repo"], task["base_commit"], task["version"]),
            encoding="utf-8",
        )
    install = " && ".join(install_commands(spec))
    if str(spec.get("python")) in {"3.5", "3.6"}:
        apt = (
            "sed -i '/security/d' /etc/apt/sources.list && "
            "sed -i 's|deb.debian.org|archive.debian.org|g' /etc/apt/sources.list && "
            "apt-get -o Acquire::Check-Valid-Until=false update"
        )
    else:
        apt = "apt-get update"
    native = (
        "RUN " + apt + " && apt-get install -y --no-install-recommends"
        " build-essential libffi-dev pkg-config zlib1g-dev libjpeg-dev libmemcached-dev"
    )
    if family == "scikit-learn":
        native += " && dpkg-query -W > /opt/grader-system-packages.txt"
    native += "\n"
    text = dockerfile(task, base, install, native, requirements)
    (work / "Dockerfile").write_bytes(text.encode("utf-8"))
    tag = "coding-harness-a5-clean:" + task["id"].replace("__", "-")
    log = WORK / task["id"] / "build.log"
    try:
        if log.exists():
            log.unlink()
    except PermissionError:
        log = WORK / task["id"] / "build-retry.log"
    digest, inspect = image_build(work, tag, log)
    private = json.loads((ROOT / task["private"]).read_text(encoding="utf-8"))
    source_ok, source_hash = source_only_check(digest, manifest)
    scan = filesystem_scan(digest, archive, manifest, private.get("test_patch") or "", private.get("patch") or "")
    row = {
        "task_id": task["id"],
        "clean_image_digest": digest,
        "clean_image_id": inspect.get("Id"),
        "original_tree_hash": manifest["source_tree_hash"],
        "image_source_only_hash": source_hash,
        "source_only_match": source_ok,
        "filesystem_scan": scan,
        "answer_isolation_pass": bool(source_ok and scan.get("pass")),
        "base_image": base,
        "spec_python": spec.get("python"),
    }
    CLEAN.mkdir(parents=True, exist_ok=True)
    (CLEAN / (task["id"] + ".json")).write_text(json.dumps(row, indent=2) + "\n", encoding="utf-8")
    return row


def django_test_lines(nodes: list[str]) -> list[str]:
    kept = []
    for node in nodes:
        line = node.splitlines()[0].strip()
        name = line.split(" (", 1)[0]
        if " (" in line and line.endswith(")") and name.replace("_", "").isalnum():
            kept.append(line)
    return kept


def nodeids(task: dict, private: dict, test_paths: list[str]) -> tuple[list[str], list[str]]:
    family = FAMILY[task["repo"]]
    f2p = [node for node in parse_id_list(private.get("FAIL_TO_PASS")) if usable_nodeid(node)]
    p2p = [node for node in parse_id_list(private.get("PASS_TO_PASS")) if usable_nodeid(node)]
    if family == "django":
        f2p, p2p = django_nodeids(django_test_lines(f2p)), django_nodeids(django_test_lines(p2p))
    if family == "sympy":
        f2p, p2p = prefix_sympy_nodeids(f2p, test_paths), prefix_sympy_nodeids(p2p, test_paths)
    return f2p, p2p


def overlay_and_gold(task: dict, archive: Path, manifest: dict, private: dict) -> tuple[dict, dict, list[str]]:
    from scripts.preflight_a5_repo_baseline import apply_patch_tree

    staging = WORK / task["id"] / "staging"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    apply_patch_tree(archive, task["repo"], task["base_commit"], private.get("test_patch") or "", private.get("patch") or "", staging)
    test_paths = patch_paths(private.get("test_patch") or "")
    overlay = {}
    original = staging / "original"
    baseline = staging / "baseline"
    for relative in test_paths:
        updated = baseline / relative
        if not updated.is_file():
            continue
        before = original / relative
        old = before.read_bytes() if before.is_file() else b""
        new = updated.read_bytes()
        if new != old:
            overlay[relative] = base64.b64encode(new).decode("ascii")
    gold_root = staging / "known-good"
    changed = {}
    for relative in patch_paths(private.get("patch") or ""):
        if relative in test_paths:
            continue
        path = gold_root / relative
        if path.is_file():
            changed[relative] = base64.b64encode(path.read_bytes()).decode("ascii")
    return overlay, {"changed": changed, "deleted": []}, test_paths


async def calibrate(task: dict, clean: dict, archive: Path, manifest: dict, private: dict) -> dict:
    family = FAMILY[task["repo"]]
    overlay, gold, test_paths = overlay_and_gold(task, archive, manifest, private)
    f2p, p2p = nodeids(task, private, test_paths)
    image = clean["clean_image_digest"]
    grader = ImageGrader()
    kwargs = dict(
        image=image, test_overlay=overlay, f2p=f2p, p2p=p2p,
        django=family == "django", sympy=False, timeout=600,
    )
    empty = await grader.evaluate(delta={"changed": {}, "deleted": []}, **kwargs)
    gold_result = await grader.evaluate(delta=gold, **kwargs)
    empty_counts = counts(empty, f2p, p2p)
    gold_counts = counts(gold_result, f2p, p2p)
    changed = empty_counts["outcomes"] != gold_counts["outcomes"]
    gold_ok = gold_counts["f2p_total"] > 0 and gold_counts["f2p_passed"] == gold_counts["f2p_total"]
    empty_fails = empty_counts["f2p_passed"] < empty_counts["f2p_total"]
    excluded = [node for node in p2p if gold_counts["outcomes"].get(node) != "passed"]
    accepted = bool(clean.get("answer_isolation_pass") and empty_fails and gold_ok and changed)
    reason = None
    if not clean.get("answer_isolation_pass"):
        reason = "answer_isolation_failed"
        accepted = False
    elif not empty_fails or not gold_ok:
        if not empty_fails and gold_ok:
            reason = "empty_f2p_did_not_fail"
        elif empty_fails and not gold_ok:
            reason = gold_result.get("reason") or "gold_f2p_incomplete"
        else:
            reason = empty.get("reason") or gold_result.get("reason") or "calibration_failed"
        accepted = False
    elif not changed:
        reason = "delta_has_no_effect"
        accepted = False
    row = {
        "task_id": task["id"],
        "repo": task["repo"],
        "accepted": accepted,
        "reason": reason,
        "empty_f2p": [empty_counts["f2p_passed"], empty_counts["f2p_total"]],
        "gold_f2p": [gold_counts["f2p_passed"], gold_counts["f2p_total"]],
        "empty_p2p": [empty_counts["p2p_passed"], empty_counts["p2p_total"]],
        "gold_p2p": [gold_counts["p2p_passed"], gold_counts["p2p_total"]],
        "p2p_excluded_count": len(excluded),
        "p2p_excluded": excluded,
        "sklearn_import": sklearn_import(image) if family == "scikit-learn" else None,
    }
    if family == "scikit-learn" and not row["sklearn_import"]:
        row["accepted"] = False
        row["reason"] = "sklearn_import_failed"
    return row


def write_summary() -> None:
    rows = []
    for path in sorted(CAL.glob("*.json")):
        rows.append(json.loads(path.read_text(encoding="utf-8")))
    accepted = [row for row in rows if row.get("accepted")]
    lines = [
        "# 题目池校准",
        "",
        f"已处理 {len(rows)} 道。合格 {len(accepted)} 道。",
        "",
        "| 仓库 | 合格 | 剔除 |",
        "| --- | --- | --- |",
    ]
    repos = ["django/django", "sympy/sympy", "scikit-learn/scikit-learn", "sphinx-doc/sphinx", "pytest-dev/pytest"]
    for repo in repos:
        group = [row for row in rows if row.get("repo") == repo]
        ok = sum(1 for row in group if row.get("accepted"))
        bad = [row["task_id"].split("__", 1)[-1] + "：" + str(row.get("reason")) for row in group if not row.get("accepted")]
        lines.append("| " + repo + " | " + str(ok) + "/" + str(len(group)) + " | " + ("；".join(bad) or "无") + " |")
    lines.append("")
    (ROOT / "docs" / "sprint" / "MAIN-CALIBRATION.md").write_text("\n".join(lines), encoding="utf-8")


def record_progress(done: int) -> None:
    if done % 10:
        return
    path = ROOT / "docs" / "sprint" / "PROGRESS.md"
    text = path.read_text(encoding="utf-8")
    marker = f"第五轮第 5 步已处理 {done} 道"
    if marker in text:
        return
    path.write_text(text.rstrip() + "\n\n" + marker + "。明细在 `docs/sprint/MAIN-CALIBRATION.md`。\n", encoding="utf-8")


async def one(task: dict) -> dict:
    destination = CAL / (task["id"] + ".json")
    if destination.is_file():
        return json.loads(destination.read_text(encoding="utf-8"))
    last = None
    for _attempt in (1, 2):
        try:
            archive = WORK / task["id"] / "source.tar.gz"
            download_archive(task, archive)
            manifest = archive_manifest(archive, task["repo"], task["base_commit"])
            clean_path = CLEAN / (task["id"] + ".json")
            if clean_path.is_file() and json.loads(clean_path.read_text(encoding="utf-8")).get("answer_isolation_pass"):
                clean = json.loads(clean_path.read_text(encoding="utf-8"))
            else:
                clean = build_image(task, archive, manifest)
            private = json.loads((ROOT / task["private"]).read_text(encoding="utf-8"))
            row = await calibrate(task, clean, archive, manifest, private)
            last = row
            if row["accepted"]:
                break
        except Exception as exc:
            last = {
                "task_id": task["id"],
                "repo": task["repo"],
                "accepted": False,
                "reason": type(exc).__name__ + ": " + str(exc)[-400:],
                "empty_f2p": [0, 0],
                "gold_f2p": [0, 0],
                "empty_p2p": [0, 0],
                "gold_p2p": [0, 0],
                "p2p_excluded_count": 0,
                "sklearn_import": None,
            }
    CAL.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(last, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"task_id": last["task_id"], "accepted": last["accepted"], "reason": last["reason"]}), flush=True)
    return last


async def main() -> None:
    tasks = yaml.safe_load((ROOT / "configs/sprint/main-targets.yaml").read_text(encoding="utf-8"))["tasks"]
    if len(sys.argv) > 1:
        wanted = set(sys.argv[1:])
        tasks = [task for task in tasks if task["id"] in wanted]
    done = 0
    for task in tasks:
        await one(task)
        done += 1
        write_summary()
        record_progress(done)


if __name__ == "__main__":
    asyncio.run(main())
