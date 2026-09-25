"""Zero-model ImageGrader calibration for the 20 pilot tasks.

Does not import run_task and does not change HOLDOUT. Private patch text stays
in the source-row files; this script only reads them to build an in-memory delta.
"""
import asyncio
import base64
import json
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.eval.image_grader import ImageGrader

# The pilot set. Kept here so this file does not import the runner.
PILOT_IDS = [
    "pytest-dev__pytest-9359",
    "pytest-dev__pytest-7432",
    "pytest-dev__pytest-8365",
    "pytest-dev__pytest-7220",
    "scikit-learn__scikit-learn-25747",
    "scikit-learn__scikit-learn-25500",
    "scikit-learn__scikit-learn-25570",
    "scikit-learn__scikit-learn-25638",
    "sphinx-doc__sphinx-8595",
    "sphinx-doc__sphinx-8713",
    "sphinx-doc__sphinx-10451",
    "sphinx-doc__sphinx-8721",
    "sympy__sympy-20442",
    "sympy__sympy-20154",
    "sympy__sympy-24152",
    "sympy__sympy-18532",
    "django__django-15781",
    "django__django-13265",
    "django__django-13448",
    "django__django-13590",
]
READY = ROOT / "docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-07/tasks"
PRIVATE = Path(r"D:\crq\src\coding-agent\reports\upgrade\a5-pilot20-preparation-20260921-v4\private\tasks")


def usable_nodeid(node: str) -> bool:
    return isinstance(node, str) and bool(node) and not node.startswith(("[", "-")) and "\n" not in node and "\x00" not in node


def parse_id_list(value) -> list[str]:
    if isinstance(value, str):
        return list(json.loads(value))
    return list(value or [])


def prefix_sympy_nodeids(nodes: list[str], test_paths) -> list[str]:
    test_file = next((path for path in test_paths if "/tests/" in path and str(path).endswith(".py")), None)
    if not test_file:
        return list(nodes)
    return [node if "::" in node or node.endswith(".py") else f"{test_file}::{node}" for node in nodes]


def django_nodeids(raw: list[str]) -> list[str]:
    converted = []
    for node in raw:
        if " (" in node and node.endswith(")"):
            name, rest = node.split(" ", 1)
            converted.append(rest.strip("()") + "." + name)
        else:
            converted.append(node)
    return converted


def source_rows() -> dict[str, Path]:
    found = {}
    for path in PRIVATE.glob("*/source-row.json"):
        row = json.loads(path.read_text(encoding="utf-8"))
        instance = row.get("instance_id")
        if instance in PILOT_IDS:
            found[instance] = path
    return found


def run_git(argv, cwd: Path):
    return subprocess.run(
        ["git", "-c", "core.autocrlf=false", "-c", "core.safecrlf=false", *argv],
        cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180,
    )


def extract(archive: Path, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    with tarfile.open(archive, "r:gz") as handle:
        members = [member for member in handle.getmembers() if member.name not in ("", ".")]
        tops = {member.name.split("/", 1)[0] for member in members}
        prefix = ""
        if len(tops) == 1:
            only = next(iter(tops))
            if all(member.name == only or member.name.startswith(only + "/") for member in members):
                prefix = only + "/"
        for member in members:
            name = member.name[len(prefix):] if prefix and member.name.startswith(prefix) else member.name
            if not name or name.endswith("/"):
                continue
            member.name = name
            handle.extract(member, dest, filter="data")


def apply_patch(tree: Path, patch: str) -> str | None:
    patch_file = tree.parent / (tree.name + ".patch")
    patch_file.write_bytes(patch.encode("utf-8"))
    git = run_git(["init", "--quiet"], tree)
    if git.returncode:
        return git.stderr[-400:]
    applied = run_git(["apply", str(patch_file)], tree)
    if applied.returncode:
        return applied.stderr[-400:]
    return None


def file_map(tree: Path) -> dict[str, bytes]:
    files = {}
    for path in tree.rglob("*"):
        if not path.is_file() or path.is_symlink() or ".git" in path.parts:
            continue
        files[path.relative_to(tree).as_posix()] = path.read_bytes()
    return files


def changed_bytes(before: dict[str, bytes], after: dict[str, bytes]) -> dict[str, str]:
    names = set(before) | set(after)
    out = {}
    for name in sorted(names):
        if before.get(name) != after.get(name) and name in after:
            out[name] = base64.b64encode(after[name]).decode("ascii")
    return out


async def one(task_id: str, row_path: Path) -> dict:
    family = task_id.split("__", 1)[0]
    calibration_path = READY / task_id / "calibration.json"
    if not calibration_path.is_file():
        return {"id": task_id, "accepted": False, "reason": "calibration_json_missing", "image": None}
    calibration = json.loads(calibration_path.read_text(encoding="utf-8"))
    image = calibration.get("image")
    archive = (calibration.get("source_seed") or {}).get("archive_ref")
    if not archive:
        fallback = ROOT / "docs/upgrade/evidence/A5-harness-preflight-12-host-sources/tasks" / task_id / "source.tar.gz"
        archive = str(fallback) if fallback.is_file() else None
    if not image or not archive or not Path(archive).is_file():
        return {"id": task_id, "accepted": False, "reason": "image_or_archive_missing", "image": image, "family": family}
    if task_id == "django__django-13265":
        return {
            "id": task_id, "family": family, "accepted": False, "reason": "contract_blocker",
            "image": image, "grader_ready": calibration.get("grader_ready"),
            "receipt": str(calibration_path.relative_to(ROOT)).replace("\\", "/"),
            "private_source_binding": str(row_path),
        }
    row = json.loads(row_path.read_text(encoding="utf-8"))
    work = ROOT / "runs/sprint3-pilot-work" / task_id
    if work.exists():
        shutil.rmtree(work)
    original = work / "original"
    extract(Path(archive), original)
    original_files = file_map(original)
    baseline = work / "baseline"
    shutil.copytree(original, baseline, symlinks=False)
    error = apply_patch(baseline, row.get("test_patch") or "")
    if error:
        return {"id": task_id, "accepted": False, "reason": "test_patch_failed", "detail": error, "image": image}
    known = work / "known-good"
    shutil.copytree(baseline, known, symlinks=False, ignore=shutil.ignore_patterns(".git"))
    error = apply_patch(known, row.get("patch") or "")
    if error:
        return {"id": task_id, "accepted": False, "reason": "gold_patch_failed", "detail": error, "image": image}
    baseline_files = file_map(baseline)
    known_files = file_map(known)
    overlay = changed_bytes(original_files, baseline_files)
    gold = {"changed": changed_bytes(baseline_files, known_files), "deleted": []}
    test_paths = list(overlay)
    f2p = parse_id_list(row.get("FAIL_TO_PASS"))
    p2p = parse_id_list(row.get("PASS_TO_PASS"))
    if family == "django":
        f2p, p2p = django_nodeids(f2p), django_nodeids(p2p)
    if family == "sympy":
        f2p, p2p = prefix_sympy_nodeids(f2p, test_paths), prefix_sympy_nodeids(p2p, test_paths)
    f2p = [node for node in f2p if usable_nodeid(node)]
    p2p = [node for node in p2p if usable_nodeid(node)]
    grader = ImageGrader()
    common = dict(image=image, test_overlay=overlay, django=family == "django", sympy=False, timeout=600)
    empty = await grader.evaluate(delta={"changed": {}, "deleted": []}, f2p=f2p, p2p=p2p, **common)
    gold_result = await grader.evaluate(delta=gold, f2p=f2p, p2p=p2p, **common)
    gold_cases = {case["nodeid"]: case["outcome"] for case in gold_result.get("cases") or []}
    excluded = [node for node in p2p if gold_cases.get(node) != "passed"]
    kept = [node for node in p2p if node not in excluded]
    empty_cases = {case["nodeid"]: case["outcome"] for case in empty.get("cases") or []}
    accepted = (
        bool(f2p)
        and all(empty_cases.get(node) != "passed" for node in f2p)
        and all(gold_cases.get(node) == "passed" for node in f2p)
        and all(empty_cases.get(node) == "passed" for node in kept)
    )
    return {
        "id": task_id,
        "family": family,
        "repo": row.get("repo"),
        "accepted": accepted,
        "f2p_total": len(f2p),
        "p2p_total": len(p2p),
        "p2p_excluded": excluded,
        "empty_f2p": empty.get("f2p_passed"),
        "empty_p2p": sum(1 for node in kept if empty_cases.get(node) == "passed"),
        "gold_f2p": gold_result.get("f2p_passed"),
        "gold_p2p": sum(1 for node in kept if gold_cases.get(node) == "passed"),
        "empty_reason": empty.get("reason"),
        "gold_reason": gold_result.get("reason"),
        "image": image,
        "receipt": str(calibration_path.relative_to(ROOT)).replace("\\", "/"),
        "source_archive": archive,
        "private_source_binding": str(row_path),
    }


def write_yaml(rows: list[dict]) -> None:
    lines = ["schema: sprint.pilot-tasks.v1", "notes: Zero-model image-grader calibration of the 20 pilot tasks.", "tasks:"]
    for row in rows:
        lines.append(f"- id: {row['id']}")
        lines.append(f"  repo: {row.get('repo') or ''}")
        lines.append(f"  family: {row.get('family') or row['id'].split('__', 1)[0]}")
        lines.append(f"  receipt: {row.get('receipt') or ''}")
        lines.append(f"  private_source_binding: {json.dumps(row.get('private_source_binding') or '')}")
        lines.append(f"  source_archive: {json.dumps(row.get('source_archive') or '')}")
        lines.append(f"  image: {json.dumps(row.get('image') or '')}")
        lines.append("  calibration:")
        lines.append(f"    accepted: {str(bool(row.get('accepted'))).lower()}")
        lines.append(f"    reason: {json.dumps(row.get('reason') or row.get('gold_reason') or '')}")
        lines.append(f"    empty_f2p: {row.get('empty_f2p') if row.get('empty_f2p') is not None else 'null'}")
        lines.append(f"    empty_p2p: {row.get('empty_p2p') if row.get('empty_p2p') is not None else 'null'}")
        lines.append(f"    gold_f2p: {row.get('gold_f2p') if row.get('gold_f2p') is not None else 'null'}")
        lines.append(f"    gold_p2p: {row.get('gold_p2p') if row.get('gold_p2p') is not None else 'null'}")
        excluded = row.get("p2p_excluded") or []
        if excluded:
            lines.append("  p2p_excluded:")
            for node in excluded:
                lines.append(f"    - {json.dumps(node)}")
        else:
            lines.append("  p2p_excluded: []")
    path = ROOT / "configs/sprint/pilot-tasks.yaml"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


async def main():
    rows_path = ROOT / "runs/sprint3-pilot-calibrate/results.jsonl"
    rows_path.parent.mkdir(parents=True, exist_ok=True)
    done = {}
    if rows_path.exists():
        for line in rows_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                done[row["id"]] = row
    found = source_rows()
    wanted = sys.argv[1:]
    for task_id in PILOT_IDS:
        if wanted and task_id not in wanted:
            continue
        if task_id in done:
            continue
        row_path = found.get(task_id)
        if row_path is None:
            row = {"id": task_id, "accepted": False, "reason": "source_row_missing"}
        else:
            row = await one(task_id, row_path)
        with rows_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row) + "\n")
        done[task_id] = row
        print(json.dumps({key: row.get(key) for key in ("id", "accepted", "reason", "empty_f2p", "gold_f2p", "empty_p2p", "gold_p2p")}, ensure_ascii=False), flush=True)
    write_yaml([done[task_id] for task_id in PILOT_IDS if task_id in done])


if __name__ == "__main__":
    asyncio.run(main())
