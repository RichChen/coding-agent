"""A5 complete-source image-backed preflight.

The earlier A5 contract deliberately stopped large repositories at the live
8 MiB/2048-file transport boundary.  This attempt is the follow-up that
preserves those exact archives and moves the complete source into a pinned,
task-specific image build context.  The live agent boundary remains bounded:
it can return only a validated candidate delta against the frozen base.

This script never crops an archive and never executes repository code on the
host.  It produces an auditable image context for every initial 24 source and
can optionally build those contexts with Docker.  A built image is only an
environment transport receipt; baseline/grader readiness and paid eligibility
remain separate gates.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tarfile
import time

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ATTEMPT = ROOT / "docs/upgrade/evidence/A5-harness-preflight-12-host-sources"
AGENT = ROOT.parent / "coding-agent"
CANONICAL = AGENT / "configs/a5/canonical-handoff.json"
PROJECTION = AGENT / "configs/a5/pilot20-harness-consumption-manifest.json"
LIMIT = 8 * 1024 * 1024
MAX_FILES = 2048
CANONICAL_SHA = "d18d9fa78da00230c30d62c61abce168b91812871d3435e14702aad7a761774c"
PROJECTION_SHA = "33ab6922caf6909888d672a8d97df49f305ed4cdabb8c402dfca4bca88cb0180"

# These are deliberately repository-family profiles, rather than a shared
# Flask/grader environment.  The base digest is pinned; dependency and
# runner binding are completed by the subsequent repo-specific gate.
BASE_IMAGES = {
    "django": "python@sha256:603879aeff06df23f0d392a19f7ce02aa85e14e6b4d25fd9647b116e0cb93467",
    "sympy": "python@sha256:603879aeff06df23f0d392a19f7ce02aa85e14e6b4d25fd9647b116e0cb93467",
    "scikit-learn": "python@sha256:603879aeff06df23f0d392a19f7ce02aa85e14e6b4d25fd9647b116e0cb93467",
    "pytest-dev": "python@sha256:603879aeff06df23f0d392a19f7ce02aa85e14e6b4d25fd9647b116e0cb93467",
    "sphinx-doc": "python@sha256:603879aeff06df23f0d392a19f7ce02aa85e14e6b4d25fd9647b116e0cb93467",
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def save(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_tree(entries: list[dict], archive: tarfile.TarFile) -> str | None:
    """Hash regular members exactly as the A5 snapshot tree hash does.

    Git archives can contain symlinks.  We retain and verify those members in
    the inventory, but a regular-file tree hash is intentionally omitted when
    the archive is not a complete regular-file snapshot.
    """
    if any(row["type"] not in ("0", "\x00") for row in entries):
        return None
    h = hashlib.sha256()
    for row in sorted(entries, key=lambda item: item["path"]):
        member = archive.getmember(row["rooted_path"])
        data = archive.extractfile(member).read()
        name = row["path"].encode()
        h.update(len(name).to_bytes(8, "big")); h.update(name)
        h.update(len(data).to_bytes(8, "big")); h.update(data)
    return h.hexdigest()


def inspect_archive(path: Path, source: dict, task: dict) -> dict:
    """Re-check every archive member against the retained source inventory."""
    expected_root = task["expected_repo"].split("/")[1] + "-" + task["expected_base_commit"]
    expected_inventory = load(path.parent / "source-inventory.json")
    if sha(path.read_bytes()) != source["archive_sha256"]:
        raise ValueError("source archive changed since attempt-12")
    if path.stat().st_size != source["archive_bytes"]:
        raise ValueError("source archive byte count changed")
    with tarfile.open(path, "r:gz") as archive:
        rows = []
        seen = set()
        for member in archive.getmembers():
            root, sep, name = member.name.partition("/")
            if root != expected_root:
                raise ValueError("archive root/commit mismatch")
            # Directory members are structural archive entries.  The retained
            # source inventory records files and nonregular members, while the
            # archive itself remains intact in the build context.
            if member.isdir():
                continue
            if not sep or not name:
                raise ValueError("archive root/commit mismatch")
            p = PurePosixPath(name)
            if p.is_absolute() or ".." in p.parts or str(p) != name or "\\" in name:
                raise ValueError("unsafe archive path")
            if name in seen:
                raise ValueError("duplicate archive path")
            seen.add(name)
            row = {"path": name, "size": member.size, "mode": member.mode,
                   "type": member.type.decode("ascii"), "linkname": member.linkname,
                   "rooted_path": member.name}
            if member.isfile():
                data = archive.extractfile(member).read()
                if len(data) != member.size:
                    raise ValueError("short archive member")
                row["sha256"] = sha(data)
            rows.append(row)
        rows.sort(key=lambda item: item["path"])
        comparable = [{k: row[k] for k in ("path", "size", "mode", "type", "linkname", "sha256") if k in row}
                      for row in rows]
        inventory_entries = [{k: row[k] for k in ("path", "size", "mode", "type", "linkname", "sha256") if k in row}
                             for row in expected_inventory["entries"]]
        if comparable != inventory_entries:
            raise ValueError("archive member inventory drift")
        if sha(json.dumps(comparable, sort_keys=True, separators=(",", ":")).encode()) != source["inventory_sha256"]:
            raise ValueError("archive inventory hash mismatch")
        tree = canonical_tree(rows, archive)
    regular_bytes = sum(row["size"] for row in rows if row["type"] in ("0", "\x00"))
    nonregular = [row["path"] for row in rows if row["type"] not in ("0", "\x00")]
    return {"archive_sha256": source["archive_sha256"], "archive_bytes": source["archive_bytes"],
            "inventory_sha256": source["inventory_sha256"], "file_count": len(rows),
            "total_bytes": regular_bytes, "source_tree_hash": tree, "nonregular_paths": nonregular,
            "complete_member_inventory_verified": True,
            "within_runtime_limits": len(rows) <= MAX_FILES and regular_bytes <= LIMIT and not nonregular}


VERIFY_SOURCE = r'''import hashlib,json,os,sys,tarfile
archive='/opt/source.tar.gz'; expected=json.load(open('/opt/source-inventory.json',encoding='utf-8'))
if hashlib.sha256(open(archive,'rb').read()).hexdigest()!=expected['archive_sha256']: raise SystemExit('archive sha256 mismatch')
if os.path.getsize(archive)!=expected['archive_bytes']: raise SystemExit('archive size mismatch')
with tarfile.open(archive,'r:gz') as t:
    rows=[]; seen=set()
    for m in t.getmembers():
        root,sep,name=m.name.partition('/')
        if m.isdir(): continue
        if not sep or not name or name in seen: raise SystemExit('unsafe/duplicate archive member')
        seen.add(name); row={'path':name,'size':m.size,'mode':m.mode,'type':m.type.decode('ascii'),'linkname':m.linkname}
        if m.isfile(): row['sha256']=hashlib.sha256(t.extractfile(m).read()).hexdigest()
        rows.append(row)
rows.sort(key=lambda x:x['path'])
if rows != expected['entries']: raise SystemExit('complete inventory mismatch')
if hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()).hexdigest()!=expected['inventory_sha256']: raise SystemExit('inventory hash mismatch')
print(json.dumps({'archive_sha256':expected['archive_sha256'],'archive_bytes':expected['archive_bytes'],'file_count':len(rows),'complete_member_inventory_verified':True}))
'''


def dockerfile(base: str) -> str:
    return f'''FROM {base}\nLABEL org.opencontainers.image.title="a5-complete-source-base"\nCOPY source.tar.gz /opt/source.tar.gz\nCOPY source-inventory.json /opt/source-inventory.json\nCOPY verify-source.py /opt/verify-source.py\nRUN python /opt/verify-source.py\nRUN mkdir -p /workspace && tar -xzf /opt/source.tar.gz -C /workspace --strip-components=1\nWORKDIR /workspace\n'''


def run_command(argv: list[str], output: Path, timeout: int = 900) -> tuple[int, str]:
    started = time.monotonic(); output.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    output.write_text(proc.stdout + "\n--- stderr ---\n" + proc.stderr, encoding="utf-8")
    output.with_suffix(".json").write_text(json.dumps({"argv": argv, "exit_code": proc.returncode,
        "elapsed_seconds": time.monotonic() - started}, indent=2) + "\n", encoding="utf-8")
    return proc.returncode, proc.stdout


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--docker-build", action="store_true")
    parser.add_argument("--only-task", action="append", default=[])
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    canonical_bytes, projection_bytes = CANONICAL.read_bytes(), PROJECTION.read_bytes()
    if sha(canonical_bytes) != CANONICAL_SHA or sha(projection_bytes) != PROJECTION_SHA:
        raise ValueError("canonical input drift")
    canonical, projection = json.loads(canonical_bytes), json.loads(projection_bytes)
    tasks = [{**task, "role": "target"} for task in canonical["target_tasks"]]
    tasks += [{**task, "role": "preflight_history_candidate"} for task in canonical["preflight_history_candidates"]]
    if len(tasks) != 24 or [task["canonical_id"] for task in tasks] != projection["targets"] + projection["preflight_history_subset"]:
        raise ValueError("24-task canonical projection mismatch")
    selected = set(args.only_task) or {task["canonical_id"] for task in tasks}
    rows = []
    for task in tasks:
        tid = task["canonical_id"]
        if tid not in selected:
            continue
        started = time.monotonic(); task_out = out / "tasks" / tid; task_out.mkdir(parents=True)
        source_dir = SOURCE_ATTEMPT / "tasks" / tid
        source_receipt = load(source_dir / "source-receipt.json")
        row = {"task_id": tid, "repo": task["expected_repo"], "base_revision": task["expected_base_commit"],
               "role": task["role"], "status": "invalid_env", "attempt": 20, "retries": 0,
               "source_attempt_ref": str(source_dir / "source-receipt.json"), "image_digest": None,
               "model_calls": 0, "paid": False}
        try:
            source = source_receipt["source"]
            verification = inspect_archive(source_dir / "source.tar.gz", source, task)
            mode = "runtime_full" if verification["within_runtime_limits"] else "image_backed_base_plus_delta"
            base = BASE_IMAGES[tid.split("__", 1)[0]]
            context = task_out / "image-context"; context.mkdir()
            shutil.copy2(source_dir / "source.tar.gz", context / "source.tar.gz")
            shutil.copy2(source_dir / "source-inventory.json", context / "source-inventory.json")
            (context / "verify-source.py").write_text(VERIFY_SOURCE, encoding="utf-8")
            docker_text = dockerfile(base)
            (context / "Dockerfile").write_text(docker_text, encoding="utf-8")
            manifest = {"schema": "a5.image-backed-source.v1", "task_id": tid, "repo": task["expected_repo"],
                "base_revision": task["expected_base_commit"], "transport_mode": mode,
                "archive_sha256": verification["archive_sha256"], "archive_bytes": verification["archive_bytes"],
                "source_tree_hash": verification["source_tree_hash"], "file_count": verification["file_count"],
                "total_bytes": verification["total_bytes"], "inventory_sha256": verification["inventory_sha256"],
                "nonregular_paths": verification["nonregular_paths"], "base_image": base,
                "dockerfile_sha256": sha(docker_text.encode()), "agent_return_contract": {
                    "schema": "a5.snapshot.delta.v1", "max_bytes": LIMIT, "max_files": MAX_FILES,
                    "requires_base_tree_hash": True, "requires_candidate_tree_hash": True,
                    "allowlist_required": True}}
            save(task_out / "image-manifest.json", manifest)
            row.update(source=verification, transport_mode=mode, base_image=base,
                       image_context=str(context), image_context_sha256=sha(json.dumps(manifest, sort_keys=True).encode()))
            if args.docker_build:
                tag = "coding-harness-a5-source:" + tid.replace("__", "-").replace("/", "-") + "-attempt20"
                code, stdout = run_command(["docker", "--context", "desktop-linux", "build", "--pull=false", "--progress=plain", "-t", tag, str(context)], task_out / "image-build")
                if code:
                    row.update(status="image_build_failed", reason="docker_build_failed")
                else:
                    inspect = json.loads(subprocess.check_output(["docker", "--context", "desktop-linux", "image", "inspect", tag], text=True))[0]
                    image = (inspect.get("RepoDigests") or [None])[0] or inspect["Id"]
                    row.update(status="image_bound", image_digest=image, image_id=inspect.get("Id"),
                               image_inspect=inspect)
            else:
                row.update(status="image_context_ready", reason="docker_build_deferred")
        except Exception as exc:
            row.update(status="invalid_env", reason="complete_source_or_context_verification_failed",
                       error=type(exc).__name__ + ": " + str(exc))
        row["duration_seconds"] = time.monotonic() - started
        save(task_out / "receipt.json", row); rows.append(row)
    counts = {status: sum(r["status"] == status for r in rows) for status in sorted({r["status"] for r in rows})}
    save(out / "manifest.json", {"schema": "a5.image-backed-preflight.v1", "attempt": 20,
        "created_at": datetime.now(timezone.utc).isoformat(), "canonical_sha256": CANONICAL_SHA,
        "projection_sha256": PROJECTION_SHA, "assigned": len(rows), "full_denominator": 24,
        "limits": {"bytes": LIMIT, "files": MAX_FILES}, "model_calls": 0, "paid": False,
        "docker_build_requested": args.docker_build})
    save(out / "receipts.json", {"schema": "a5.image-backed-preflight.receipts.v1", "rows": rows})
    save(out / "readiness.json", {"status": "blocked", "assigned": len(rows), "full_denominator": 24,
        "status_counts": counts, "complete_source_verified": sum(r["status"] in ("image_context_ready", "image_bound") for r in rows),
        "baseline_grader_ready": 0, "model_calls": 0, "paid": False, "paid_build_started": False,
        "paid_pilot_started": False, "remaining16_gate": "blocked_until_initial24_baseline_and_grader",
        "all20_memory_sources_paid_eligibility": "blocked",
        "shared_gates": ["model_snapshot_current_price", "budget_scope_runtime_alignment", "dual_source_fingerprint", "B0-B3_receipt_integration"]})
    save(out / "failure-retry-ledger.json", {"schema": "a5.failure-retry-ledger.v1", "attempt": 20,
        "entries": [{"task_id": r["task_id"], "status": r["status"], "reason": r.get("reason"), "retries": r["retries"]} for r in rows],
        "model_calls": 0, "model_reservations": 0, "paid": False})
    save(out / "handoff.json", {"schema": "a5.memory-pool-preflight-handoff.v1", "status": "blocked",
        "image_transport": "complete_archive_image_backed_base_plus_bounded_delta",
        "source_count": len(rows), "memory_build_sources": projection["memory_build_sources"],
        "ready_for_paid_memory_build": False, "ready_for_environment_continuation": all(r["status"] in ("image_context_ready", "image_bound") for r in rows),
        "reason": "image binding alone does not satisfy repo-specific baseline/grader or shared gates",
        "receipt_ref": str(out / "receipts.json")})
    save(out / "artifact-manifest.json", {p.relative_to(out).as_posix(): sha(p.read_bytes()) for p in sorted(out.rglob("*")) if p.is_file()})
    print(json.dumps(counts, sort_keys=True))


if __name__ == "__main__":
    main()
