"""Fetch complete pinned archives for the exact initial A5 24; no model or Docker.

Source-size failures stop before environment execution. Archives, including all
nonregular members, are retained intact. No upstream file is silently excluded.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import tarfile
import time

AGENT = Path("D:/crq/src/coding-agent")
CANONICAL = AGENT / "configs/a5/canonical-handoff.json"
PROJECTION = AGENT / "configs/a5/pilot20-harness-consumption-manifest.json"
LIMIT = 8 * 1024 * 1024
MAX_FILES = 2048


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def inspect_archive(path, task):
    entries, files = [], {}
    with tarfile.open(path, "r:gz") as archive:
        expected_root = task["expected_repo"].split("/")[1] + "-" + task["expected_base_commit"]
        for member in archive.getmembers():
            root, _, name = member.name.partition("/")
            if root != expected_root:
                raise ValueError("archive root/commit mismatch: " + root)
            if not name or member.isdir():
                continue
            p = PurePosixPath(name)
            if p.is_absolute() or ".." in p.parts or str(p) != name or "\\" in name:
                raise ValueError("unsafe archive path")
            if name in files:
                raise ValueError("duplicate archive path")
            record = {"path": name, "size": member.size, "mode": member.mode,
                      "type": member.type.decode("ascii"), "linkname": member.linkname}
            if member.isfile():
                data = archive.extractfile(member).read()
                if len(data) != member.size:
                    raise ValueError("short archive member")
                record["sha256"] = sha(data)
                files[name] = data
            else:
                files[name] = None
            entries.append(record)
        git_commit = archive.pax_headers.get("comment")
    entries.sort(key=lambda row: row["path"])
    tree = hashlib.sha256()
    for name, data in sorted(files.items()):
        if data is None:
            continue
        encoded = name.encode()
        tree.update(len(encoded).to_bytes(8, "big")); tree.update(encoded)
        tree.update(len(data).to_bytes(8, "big")); tree.update(data)
    regular_bytes = sum(row["size"] for row in entries if row["type"] in ("0", "\u0000"))
    nonregular = [row["path"] for row in entries if row["type"] not in ("0", "\u0000")]
    return {"schema": "a5.full-archive-inventory.v1", "repo": task["expected_repo"],
            "base_revision": task["expected_base_commit"], "archive_sha256": sha(path.read_bytes()),
            "archive_bytes": path.stat().st_size, "git_pax_commit": git_commit,
            "source_tree_hash": tree.hexdigest() if not nonregular else None,
            "inventory_sha256": sha(json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()),
            "file_count": len(entries), "total_bytes": regular_bytes, "entries": entries,
            "nonregular_paths": nonregular, "excluded_upstream_paths": [],
            "snapshot_kind": "complete_pinned_upstream_archive",
            "within_runtime_limits": len(entries) <= MAX_FILES and regular_bytes <= LIMIT and not nonregular}


def source_task(task, output):
    started = time.monotonic()
    tid = task["canonical_id"]
    directory = output / "tasks" / tid
    directory.mkdir(parents=True, exist_ok=False)
    archive = directory / "source.tar.gz"
    url = f'https://codeload.github.com/{task["expected_repo"]}/tar.gz/{task["expected_base_commit"]}'
    command = ["curl.exe", "--fail", "--location", "--silent", "--show-error", "--connect-timeout", "20",
               "--max-time", "150", "--dump-header", str(directory / "http-headers.txt"),
               "--output", str(archive), url]
    row = {"task_id": tid, "agent_task_id": task["agent_task_id"], "repo": task["expected_repo"],
           "base_revision": task["expected_base_commit"], "role": task["role"], "status": "missing_source",
           "source": None, "image_digest": None, "python_version": None, "pytest_version": None,
           "dependencies": None, "collection": {"status": "not_run", "count": None, "hash": None},
           "baseline": {"status": "not_run", "failure_nodeids": None},
           "grader": {"status": "not_run", "known_good": "not_run", "negative_rejection": "not_run"},
           "cleanup": "not_applicable_no_container_started", "model_calls": 0, "paid": False,
           "attempt": 1, "retries": 0}
    try:
        result = subprocess.run(command, capture_output=True, timeout=165)
        save(directory / "download-receipt.json", {"argv": command, "exit_code": result.returncode,
             "stderr": result.stderr.decode("utf-8", "replace"), "duration_seconds": time.monotonic() - started})
        if result.returncode:
            row["reason"] = "source_download_failed"
        else:
            source = inspect_archive(archive, task)
            save(directory / "source-inventory.json", source)
            row["source"] = {key: value for key, value in source.items() if key != "entries"}
            row["source"]["inventory_ref"] = str(directory / "source-inventory.json")
            if not source["within_runtime_limits"]:
                row["status"] = "invalid_env"
                row["reason"] = "full_source_exceeds_runtime_limits" if source["total_bytes"] > LIMIT or source["file_count"] > MAX_FILES else "nonregular_source_not_supported"
            else:
                row["status"] = "blocked"
                row["reason"] = "source_acquired_repo_specific_environment_preflight_pending"
    except Exception as exc:
        row["reason"] = "source_acquisition_or_inventory_error"
        row["error"] = type(exc).__name__ + ": " + str(exc)
    row["duration_seconds"] = time.monotonic() - started
    save(directory / "source-receipt.json", row)
    print(json.dumps({"task_id": tid, "status": row["status"], "reason": row["reason"],
          "files": (row["source"] or {}).get("file_count"), "bytes": (row["source"] or {}).get("total_bytes")}), flush=True)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    cbytes, mbytes = CANONICAL.read_bytes(), PROJECTION.read_bytes()
    if sha(cbytes) != "d18d9fa78da00230c30d62c61abce168b91812871d3435e14702aad7a761774c" or sha(mbytes) != "33ab6922caf6909888d672a8d97df49f305ed4cdabb8c402dfca4bca88cb0180":
        raise ValueError("canonical input drift")
    c, m = json.loads(cbytes), json.loads(mbytes)
    tasks = [{**t, "role": "target"} for t in c["target_tasks"]] + [{**t, "role": "preflight_history_candidate"} for t in c["preflight_history_candidates"]]
    if len(tasks) != 24 or [t["canonical_id"] for t in tasks] != m["targets"] + m["preflight_history_subset"]:
        raise ValueError("24-task inventory mismatch")
    output.mkdir(parents=True, exist_ok=False)
    save(output / "manifest.json", {"created_at": datetime.now(timezone.utc).isoformat(),
         "canonical": str(CANONICAL), "canonical_sha256": sha(cbytes), "manifest": str(PROJECTION),
         "manifest_sha256": sha(mbytes), "tasks": tasks, "limits": {"bytes": LIMIT, "files": MAX_FILES},
         "model_calls": 0, "paid": False, "mode": "real_host_source_preflight", "workers": 4,
         "script_sha256": sha(Path(__file__).read_bytes())})
    with ThreadPoolExecutor(max_workers=4) as executor:
        rows = list(executor.map(lambda task: source_task(task, output), tasks))
    counts = {status: sum(r["status"] == status for r in rows) for status in sorted({r["status"] for r in rows})}
    save(output / "receipts.json", {"schema": "a5.host-source-preflight.v1", "rows": rows})
    save(output / "failure-retry-ledger.json", {"phase": "source_acquisition", "entries": [
        {k: r[k] for k in ("task_id", "status", "reason", "attempt", "retries")} for r in rows],
        "model_calls": 0, "model_reservations": 0, "paid": False})
    save(output / "readiness.json", {"status": "blocked", "assigned": 24, "source_receipt_rows": 24,
         "status_counts": counts, "environment_ready": 0, "baseline_runs": 0, "model_calls": 0,
         "paid": False, "paid_build_started": False, "paid_pilot_started": False,
         "remaining16_gate": "not_started_initial24_not_passed"})
    save(output / "artifact-manifest.json", {p.relative_to(output).as_posix(): sha(p.read_bytes()) for p in sorted(output.rglob("*")) if p.is_file()})
    print(json.dumps(counts), flush=True)


if __name__ == "__main__":
    main()
