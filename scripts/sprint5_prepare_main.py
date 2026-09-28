"""Build and calibrate main-pool images. No model calls."""
from __future__ import annotations

import ast
import asyncio
import base64
import json
import shutil
import sys
import tarfile
import urllib.request
from pathlib import Path, PurePosixPath

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
    if family == "sphinx-doc":
        install += " && python -m pip install --no-cache-dir roman"
    if family == "pytest-dev":
        install = install.replace("python -m pip install --no-cache-dir pytest && ", "", 1)
        pretend = str(task["version"])
        if pretend.count(".") < 2:
            pretend += ".0"
        install = install.replace(
            "python -m pip install -e .",
            "SETUPTOOLS_SCM_PRETEND_VERSION=" + pretend
            + " SETUPTOOLS_SCM_PRETEND_VERSION_FOR_PYTEST=" + pretend
            + " python -m pip install --no-cache-dir -e .",
            1,
        )
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
    if family == "sphinx-doc":
        native += " git"
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
    rewritten = set()
    for command in spec.get("pre_install") or []:
        parts = str(command).split()
        if parts and parts[0] == "sed" and "/" not in parts[-1]:
            rewritten.add(parts[-1])
    source_ok, source_hash = source_only_check(digest, manifest, rewritten)
    scan = filesystem_scan(
        digest, archive, manifest, private.get("test_patch") or "", private.get("patch") or "",
        base_image=base,
    )
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


def is_django_test_line(line: str) -> bool:
    name = line.split(" (", 1)[0]
    return " (" in line and line.endswith(")") and name.replace("_", "").isalnum()


def django_test_lines(nodes: list[str]) -> list[str]:
    kept = []
    for node in nodes:
        line = node.splitlines()[0].strip()
        if is_django_test_line(line):
            kept.append(line)
    return kept


def django_test_module(relative: str) -> str | None:
    """tests/a/b.py is module a.b, because runtests.py puts tests/ on sys.path."""
    path = PurePosixPath(relative)
    if path.suffix != ".py" or len(path.parts) < 2 or path.parts[0] != "tests":
        return None
    parts = list(path.with_suffix("").parts[1:])
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts) or None


def django_module_file(root: Path, nodeid: str) -> tuple[str, str] | None:
    """Find the file that defines module.Class.method under tests/."""
    parts = nodeid.split(".")
    for end in range(len(parts) - 2, 0, -1):
        base = PurePosixPath("tests", *parts[:end])
        for candidate in (base.with_suffix(".py"), base / "__init__.py"):
            if (root / candidate).is_file():
                return candidate.as_posix(), ".".join(parts[:end])
    return None


def docstring_index(root: Path, files: dict[str, str]) -> dict[str, list[str]]:
    """Map the first docstring line of each test method to module.Class.method.

    The first line is taken the way unittest's shortDescription() takes it, which is
    what the SWE-bench Django log parser records for a test with a docstring.
    """
    index: dict[str, list[str]] = {}
    for relative, module in sorted(files.items()):
        tree = ast.parse((root / relative).read_bytes(), filename=relative)
        for cls in tree.body:
            if not isinstance(cls, ast.ClassDef):
                continue
            for method in cls.body:
                if not isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)) or not method.name.startswith("test"):
                    continue
                doc = ast.get_docstring(method, clean=False)
                first = doc.strip().split("\n")[0].strip() if doc else ""
                if first:
                    index.setdefault(first, []).append(module + "." + cls.name + "." + method.name)
    return index


def django_selection(raw: dict[str, list[str]], root: Path, test_paths: list[str]) -> tuple[dict, list[dict], list[dict]]:
    """Convert Django ids and map docstring ids back to test methods. A docstring must match exactly one method."""
    lines = {side: [node.splitlines()[0].strip() for node in nodes] for side, nodes in raw.items()}
    files: dict[str, str] = {}
    for relative in test_paths:
        module = django_test_module(relative)
        if module and (root / relative).is_file():
            files[relative] = module
    for side_lines in lines.values():
        for nodeid in django_nodeids([line for line in side_lines if is_django_test_line(line)]):
            found = django_module_file(root, nodeid)
            if found:
                files.setdefault(found[0], found[1])
    index = docstring_index(root, files)
    selected: dict[str, list[str]] = {}
    dropped: list[dict] = []
    mapping: list[dict] = []
    for side, nodes in raw.items():
        out: list[str] = []
        for node, line in zip(nodes, lines[side]):
            if is_django_test_line(line):
                converted = django_nodeids([line])[0]
            else:
                targets = index.get(line) or []
                if len(targets) != 1:
                    reason = "docstring_ambiguous" if targets else "docstring_unmatched"
                    dropped.append({"side": side, "nodeid": node, "reason": reason, "candidates": targets})
                    continue
                converted = targets[0]
                mapping.append({"side": side, "docstring": node, "nodeid": converted})
            if converted not in out:
                out.append(converted)
        selected[side] = out
    return selected, dropped, mapping


def nodeid_selection(task: dict, private: dict, test_paths: list[str]) -> tuple[list[str], list[str], dict]:
    family = FAMILY[task["repo"]]
    raw = {
        "f2p": [node for node in parse_id_list(private.get("FAIL_TO_PASS"))],
        "p2p": [node for node in parse_id_list(private.get("PASS_TO_PASS"))],
    }
    dropped: list[dict] = []
    mapping: list[dict] = []
    kept = {}
    for side, nodes in raw.items():
        accepted = []
        for node in nodes:
            if not usable_nodeid(node):
                dropped.append({"side": side, "nodeid": node, "reason": "unusable_nodeid"})
            else:
                accepted.append(node)
        kept[side] = accepted
    if family == "django":
        kept, django_dropped, mapping = django_selection(kept, WORK / task["id"] / "staging" / "baseline", test_paths)
        dropped.extend(django_dropped)
    if family == "sympy":
        baseline = WORK / task["id"] / "staging" / "baseline"
        for side in ("f2p", "p2p"):
            located = prefix_sympy_nodeids(kept[side], test_paths, baseline)
            located_names = {node.split("::")[-1] for node in located}
            for node in kept[side]:
                if "::" not in node and not node.endswith(".py") and node not in located_names:
                    dropped.append({"side": side, "nodeid": node, "reason": "not_in_touched_test_file"})
            kept[side] = located
    baseline = WORK / task["id"] / "staging" / "baseline"

    def addressable(side: str, node: str) -> bool:
        if node.count("[") != node.count("]") or node.count("(") != node.count(")"):
            dropped.append({"side": side, "nodeid": node, "reason": "unbalanced_brackets"})
            return False
        bracket = node.find("[")
        if bracket != -1 and "::" in node[bracket:]:
            dropped.append({"side": side, "nodeid": node, "reason": "parameter_contains_node_separator"})
            return False
        if family in {"django", "sympy"}:
            return True
        file = node.split("::", 1)[0]
        if file.endswith(".py") and not (baseline / file).is_file():
            dropped.append({"side": side, "nodeid": node, "reason": "test_file_missing"})
            return False
        return True

    f2p = [node for node in kept["f2p"] if addressable("f2p", node)]
    p2p = [node for node in kept["p2p"] if addressable("p2p", node)]
    reasons = {"f2p": {}, "p2p": {}}
    for item in dropped:
        bucket = reasons[item["side"]]
        bucket[item["reason"]] = bucket.get(item["reason"], 0) + 1
    report = {
        "f2p": {"original": len(raw["f2p"]), "used": len(f2p)},
        "p2p": {"original": len(raw["p2p"]), "used": len(p2p)},
        "dropped_reasons": reasons,
        "dropped": dropped,
    }
    if family == "django":
        report["mapped"] = {side: sum(1 for item in mapping if item["side"] == side) for side in ("f2p", "p2p")}
        report["mapping"] = mapping
    return f2p, p2p, report


def grade_verdict(row: dict) -> tuple[bool, str | None]:
    """Recompute acceptance from stored counts after an isolation flag changes."""
    if row.get("sklearn_import") is False:
        return False, "sklearn_import_failed"
    if any(item.get("side") == "f2p" for item in (row.get("nodeids") or {}).get("dropped") or []):
        return False, "f2p_unaddressable"
    empty = row.get("empty_f2p") or [0, 0]
    gold = row.get("gold_f2p") or [0, 0]
    empty_fails = empty[1] > 0 and empty[0] < empty[1]
    gold_ok = gold[1] > 0 and gold[0] == gold[1]
    if empty_fails and gold_ok:
        return True, None
    if not empty_fails and gold_ok:
        return False, "empty_f2p_did_not_fail"
    if empty_fails and not gold_ok:
        return False, "gold_f2p_incomplete"
    return False, "calibration_failed"


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
    f2p, p2p, nodeid_report = nodeid_selection(task, private, test_paths)
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
    if clean.get("answer_isolation_pass") and any(item["side"] == "f2p" for item in nodeid_report["dropped"]):
        reason = "f2p_unaddressable"
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
        "nodeids": nodeid_report,
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
    lines.extend(django_mapping_lines([row for row in rows if row.get("repo") == "django/django"]))
    lines.extend(excused_scan_lines([row["task_id"] for row in accepted]))
    (ROOT / "docs" / "sprint" / "MAIN-CALIBRATION.md").write_text("\n".join(lines), encoding="utf-8")


def django_mapping_lines(rows: list[dict]) -> list[str]:
    lines = [
        "## Django 测试 id",
        "",
        "SWE-bench 把带 docstring 的测试记成 docstring 第一行。校准时在应用了测试补丁的源码树上用 `ast` 找到唯一匹配的测试方法，映射成 `module.Class.method`。零个或多个匹配算定位失败；F2P 定位失败的题排除（`f2p_unaddressable`），P2P 定位失败的丢弃。",
        "",
        "| 题 | F2P 原始/使用/映射 | P2P 原始/使用/映射 | 丢弃 |",
        "| --- | --- | --- | --- |",
    ]
    for row in rows:
        report = row.get("nodeids") or {}
        mapped = report.get("mapped") or {}
        dropped = []
        for side in ("f2p", "p2p"):
            for reason, count in ((report.get("dropped_reasons") or {}).get(side) or {}).items():
                dropped.append(side.upper() + " " + reason + " " + str(count))
        cells = []
        for side in ("f2p", "p2p"):
            counts = report.get(side) or {}
            cells.append(str(counts.get("original")) + "/" + str(counts.get("used")) + "/" + str(mapped.get(side, 0)))
        lines.append("| " + row["task_id"].split("__", 1)[-1] + " | " + " | ".join(cells) + " | " + ("；".join(dropped) or "无") + " |")
    return lines + [""]


EXCUSE_REASON = {
    "base_image_same": "基础镜像里同一路径、同一 sha256，是 Python 自带文件，不是构建时写入的",
    "install_record_same": "sha256 与 pip RECORD 记录一致，是未改动的第三方依赖文件",
}


def excused_scan_lines(task_ids: list[str]) -> list[str]:
    rows = []
    for task_id in task_ids:
        path = CLEAN / (task_id + ".json")
        if not path.is_file():
            continue
        scan = json.loads(path.read_text(encoding="utf-8")).get("filesystem_scan") or {}
        for rule in ("base_image_same", "install_record_same"):
            for hit in scan.get(rule) or []:
                rows.append("| " + task_id + " | `" + hit + "` | " + EXCUSE_REASON[rule] + " |")
    lines = [
        "## 扫描排除的文件",
        "",
        "合格题的全文件系统扫描里，下列命中按规则排除。`/opt/repo` 下和目标项目顶层包目录下的命中不适用这两条排除。",
        "",
    ]
    if not rows:
        return lines + ["无。", ""]
    return lines + ["| 题 | 文件 | 排除理由 |", "| --- | --- | --- |"] + rows + [""]


def record_progress(done: int) -> None:
    if done % 10:
        return
    path = ROOT / "docs" / "sprint" / "PROGRESS.md"
    text = path.read_text(encoding="utf-8")
    marker = f"第五轮第 5 步已处理 {done} 道"
    if marker in text:
        return
    path.write_text(text.rstrip() + "\n\n" + marker + "。明细在 `docs/sprint/MAIN-CALIBRATION.md`。\n", encoding="utf-8")


async def one(task: dict, *, force: bool = False) -> dict:
    destination = CAL / (task["id"] + ".json")
    if destination.is_file() and not force:
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


def rescan(task: dict) -> dict:
    clean_path = CLEAN / (task["id"] + ".json")
    if not clean_path.is_file():
        raise RuntimeError("clean image record missing: " + task["id"])
    clean = json.loads(clean_path.read_text(encoding="utf-8"))
    archive = WORK / task["id"] / "source.tar.gz"
    download_archive(task, archive)
    manifest = archive_manifest(archive, task["repo"], task["base_commit"])
    private = json.loads((ROOT / task["private"]).read_text(encoding="utf-8"))
    scan = filesystem_scan(
        clean["clean_image_digest"], archive, manifest,
        private.get("test_patch") or "", private.get("patch") or "",
        base_image=clean.get("base_image"),
    )
    clean["filesystem_scan"] = scan
    clean["answer_isolation_pass"] = bool(clean.get("source_only_match") and scan.get("pass"))
    clean_path.write_text(json.dumps(clean, indent=2) + "\n", encoding="utf-8")
    _overlay, _gold, test_paths = overlay_and_gold(task, archive, manifest, private)
    _f2p, _p2p, report = nodeid_selection(task, private, test_paths)
    destination = CAL / (task["id"] + ".json")
    if destination.is_file():
        row = json.loads(destination.read_text(encoding="utf-8"))
        row["nodeids"] = report
        if not clean["answer_isolation_pass"]:
            row["accepted"] = False
            row["reason"] = "answer_isolation_failed"
        elif row.get("reason") == "answer_isolation_failed":
            row["accepted"], row["reason"] = grade_verdict(row)
        destination.write_text(json.dumps(row, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "task_id": task["id"],
        "scan_pass": scan.get("pass"),
        "hits": scan.get("hit_count"),
        "base_same": scan.get("base_image_same_count"),
        "install_same": scan.get("install_record_same_count"),
        "f2p": report["f2p"],
        "p2p": report["p2p"],
    }), flush=True)
    return clean


async def main() -> None:
    tasks = yaml.safe_load((ROOT / "configs/sprint/main-targets.yaml").read_text(encoding="utf-8"))["tasks"]
    if "--rescan" in sys.argv:
        sys.argv.remove("--rescan")
        if len(sys.argv) > 1:
            wanted = set(sys.argv[1:])
            tasks = [task for task in tasks if task["id"] in wanted]
        for index, task in enumerate(tasks, start=1):
            try:
                rescan(task)
            except RuntimeError as exc:
                print(json.dumps({"task_id": task["id"], "error": str(exc)}), flush=True)
            write_summary()
            record_progress(index)
        return
    force = "--recalibrate" in sys.argv
    if force:
        sys.argv.remove("--recalibrate")
    if len(sys.argv) > 1:
        wanted = set(sys.argv[1:])
        tasks = [task for task in tasks if task["id"] in wanted]
    done = 0
    for task in tasks:
        await one(task, force=force)
        done += 1
        write_summary()
        record_progress(done)


if __name__ == "__main__":
    asyncio.run(main())
