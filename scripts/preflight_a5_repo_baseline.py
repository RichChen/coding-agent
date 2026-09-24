"""A5 repository-specific image-backed environment and baseline preflight.

This attempt consumes the complete source images from attempt 23, applies each
private test patch in a host staging directory without executing repository
code, then builds a pinned task-specific baseline image. Repository code runs
only inside the no-network Docker execution backend. Four exact pytest rows
with already audited baseline receipts are carried forward by source hash;
every other row gets a new collection and baseline attempt.

This is the initial image/evidence producer. Use recheck_a5_repo_baseline.py for
the final repo adapters and audit_a5_repo_baseline.py for authoritative readiness.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tarfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
AGENT = ROOT.parent / "coding-agent"
CANONICAL = AGENT / "configs/a5/canonical-handoff.json"
PROJECTION = AGENT / "configs/a5/pilot20-harness-consumption-manifest.json"
SOURCE_ROOT = ROOT / "docs/upgrade/evidence/A5-harness-preflight-12-host-sources"
TRANSPORT_ROOT = ROOT / "docs/upgrade/evidence/A5-harness-preflight-23-transport-smoke"
PREVIOUS_ROOT = ROOT / "docs/upgrade/evidence/A5-harness-preflight-19-final-audit"
CANONICAL_SHA = "d18d9fa78da00230c30d62c61abce168b91812871d3435e14702aad7a761774c"
PROJECTION_SHA = "33ab6922caf6909888d672a8d97df49f305ed4cdabb8c402dfca4bca88cb0180"
LIMIT = 8 * 1024 * 1024

PYTEST_OBSERVER = r'''import json,sys,os
repo_root=os.environ.get('A5_REPO_ROOT','/workspace')
sys.path.insert(0,repo_root); sys.path.insert(0,repo_root+'/src')
os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD']='1'
import pytest
payload=json.load(sys.stdin)
receipt={'schema':'a5.repo.pytest.receipt.v2','collected':[],'reports':[],'collection_errors':[], 'complete':False,'exit_code':3}
if payload.get('sympy_native_helpers'):
    import sympy.testing.pytest as sympy_helpers
    receipt['sympy_helper_initialization']={'file':sympy_helpers.__file__,'use_pytest':sympy_helpers.USE_PYTEST}
class O:
    def pytest_collection_finish(self, session): receipt['collected']=[i.nodeid for i in session.items]
    def pytest_collectreport(self, report):
        if report.failed: receipt['collection_errors'].append({'nodeid':report.nodeid,'detail':str(report.longrepr)})
    def pytest_runtest_logreport(self, report):
        receipt['reports'].append({'nodeid':report.nodeid,'when':report.when,'outcome':report.outcome,'wasxfail':getattr(report,'wasxfail',None),'detail':str(report.longrepr) if report.failed else None})
args=list(payload['args'])
receipt['argv']=args
try:
    receipt['pytest_version']=pytest.__version__
    receipt['pytest_import']=pytest.__file__
    code=int(pytest.main(args, plugins=[O()]))
    receipt.update(complete=True,exit_code=code)
except BaseException as exc:
    receipt.update(runner_error=type(exc).__name__+': '+str(exc),exit_code=3)
open('/tmp/a5-pytest-receipt.json','w',encoding='utf-8').write(json.dumps(receipt,ensure_ascii=True))
raise SystemExit(receipt['exit_code'])
'''


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def run_host(argv, cwd=None, timeout=900):
    if argv[0] == 'git':
        argv = ['git', '-c', 'core.autocrlf=false', '-c', 'core.safecrlf=false', *argv[1:]]
    return subprocess.run(argv, cwd=cwd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout)


def source_row_path(task):
    root = AGENT / "reports/upgrade/a5-pilot20-preparation-20260921-v4/private"
    if task["canonical_id"] in [x["canonical_id"] for x in load(CANONICAL)["target_tasks"]]:
        return root / "tasks" / task["agent_task_id"] / "source-row.json"
    return root / "history" / ("a5-task-" + task["agent_task_id"].split("a5-build-", 1)[1]) / "source-row.json"


def patch_paths(patch: str):
    return sorted({line.split(" b/", 1)[1] for line in patch.splitlines() if line.startswith("diff --git a/")})


def tree_archive(root: Path, destination: Path, mode_manifest=None) -> None:
    with tarfile.open(destination, "w:gz") as archive:
        for path in sorted(root.rglob("*"), key=lambda p: p.relative_to(root).as_posix()):
            if ".git" in path.relative_to(root).parts:
                continue
            relative = path.relative_to(root).as_posix()
            info = archive.gettarinfo(str(path), arcname=relative)
            if mode_manifest and relative in mode_manifest:
                info.mode = mode_manifest[relative].get("mode", info.mode)
            if info.isreg():
                with path.open("rb") as stream:
                    archive.addfile(info, stream)
            else:
                archive.addfile(info)


def apply_patch_tree(source_archive: Path, repo: str, revision: str, test_patch: str, gold_patch: str, out: Path):
    from src.eval.a5_image_tree import archive_manifest, extract, disk_entries, tree_hash
    manifest = archive_manifest(source_archive, repo, revision)
    original = out / "original"; extract(source_archive, manifest, original, verify_modes=False)
    baseline = out / "baseline"; shutil.copytree(original, baseline, symlinks=True)
    gold = out / "known-good"
    for tree, label, patch in ((baseline, "test", test_patch), (gold, "gold", gold_patch)):
        if label == "gold":
            shutil.copytree(baseline, gold, symlinks=True, ignore=shutil.ignore_patterns(".git"))
        git = run_host(["git", "init", "--quiet"], cwd=tree, timeout=60)
        if git.returncode:
            raise RuntimeError(f"git init {label}: {git.stderr[-500:]}")
        before = disk_entries(tree)
        # Keep the upstream unified-diff LF bytes intact. Windows text-mode
        # newline conversion makes git's context contain stray CR characters.
        patch_file = out / f"{label}.patch"; patch_file.write_bytes(patch.encode("utf-8"))
        check = run_host(["git", "apply", "--check", str(patch_file)], cwd=tree, timeout=120)
        if check.returncode:
            raise RuntimeError(f"git apply check {label}: {check.stderr[-1000:]}")
        applied = run_host(["git", "apply", str(patch_file)], cwd=tree, timeout=120)
        if applied.returncode:
            raise RuntimeError(f"git apply {label}: {applied.stderr[-1000:]}")
        after = disk_entries(tree)
        changed = sorted(k for k in set(before) | set(after)
            if before.get(k) != after.get(k) and (after.get(k) or before[k])['kind'] != 'dir')
        save(out / f"{label}-binding.json", {"patch_sha256": sha(patch.encode()), "changed_paths": changed,
            "declared_paths": patch_paths(patch), "tree_hash": tree_hash(disk_entries(tree))})
        if not set(changed).issubset(set(patch_paths(patch))):
            raise ValueError(f"{label} changed paths exceed patch declaration")
        if label == "test":
            # Leave a clean index for the gold patch's independent workspace.
            pass
    baseline_entries = disk_entries(baseline)
    gold_entries = disk_entries(gold)
    baseline_modes = {**manifest['entries'], **{k: v for k, v in baseline_entries.items() if k not in manifest['entries']}}
    gold_modes = {**manifest['entries'], **{k: v for k, v in gold_entries.items() if k not in manifest['entries']}}
    tree_archive(baseline, out / "baseline.tar.gz", baseline_modes)
    tree_archive(gold, out / "known-good.tar.gz", gold_modes)
    return manifest, baseline_entries, gold_entries


def dependency_profile(family, version):
    if family == "django":
        asgiref = "3.7.2" if str(version).startswith("4.") else ("3.5.2" if str(version).startswith("3.2") else "3.2.10")
        return f"python -m pip install --no-cache-dir asgiref=={asgiref} pytz==2023.3 sqlparse==0.4.4 pytest==7.4.4"
    if family == "sympy":
        return "python -m pip install --no-cache-dir mpmath==1.3.0 pytest==7.4.4 hypothesis==6.82.0"
    if family == "scikit-learn":
        if str(version).startswith('0.20'):
            return "python -m pip install --no-cache-dir numpy==1.19.5 scipy==1.5.4 pandas==1.1.5 pytest==6.2.5 cython==0.29.36 joblib==1.0.1 threadpoolctl==3.2.0 nose==1.3.7"
        return "python -m pip install --no-cache-dir numpy==1.24.4 scipy==1.10.1 pandas==2.0.3 pytest==7.4.4 cython==0.29.36 joblib==1.3.2 threadpoolctl==3.2.0 matplotlib==3.7.2"
    if family == "sphinx-doc":
        docutils = "0.18.1" if str(version).startswith("5.") else ("0.17.1" if str(version).startswith("4.") else "0.16")
        jinja = "3.1.2" if str(version).startswith("5.") else "3.0.3"
        pygments = '2.15.1' if str(version).startswith('5.') else '2.8.1'
        return ("python -m pip install --no-cache-dir pytest==7.4.4 docutils==" + docutils +
            " Jinja2==" + jinja + " Pygments==" + pygments + " snowballstemmer==2.2.0 babel==2.12.1 "
            "alabaster==0.7.13 imagesize==1.4.1 requests==2.31.0 packaging==23.1 html5lib==1.1 "
            "sphinxcontrib-applehelp==1.0.2 sphinxcontrib-devhelp==1.0.2 sphinxcontrib-jsmath==1.0.1 "
            "sphinxcontrib-htmlhelp==2.0.0 sphinxcontrib-serializinghtml==1.1.5 sphinxcontrib-qthelp==1.0.3")
    if family == "pytest-dev":
        return "python -m pip install --no-cache-dir attrs==19.3.0 iniconfig==1.1.1 packaging==20.9 pyparsing==2.4.7 pluggy==0.13.1 py==1.10.0 toml==0.10.2 tomli==1.2.3 atomicwrites==1.4.0 more-itertools==8.7.0 six==1.16.0 wcwidth==0.2.13 hypothesis==5.49.0 sortedcontainers==2.3.0 xmlschema==1.5.3 elementpath==2.2.3"
    raise ValueError(f"unknown repository family: {family}")


def dockerfile(base_ref, family, version, archive_name):
    profile = dependency_profile(family, version)
    if family == "pytest-dev":
        install = (profile + " && python -m pip install --no-cache-dir setuptools-scm==6.4.2 "
            f"&& SETUPTOOLS_SCM_PRETEND_VERSION={version}.0 python -m pip install --no-cache-dir --no-build-isolation --no-deps -e /workspace")
    elif family == "scikit-learn":
        install = profile + " && python -m pip install --no-cache-dir --no-build-isolation --no-deps -e /workspace"
    else:
        install = profile + " && python -m pip install --no-cache-dir --no-deps -e /workspace"
    native = ("RUN sed -i 's|http://deb.debian.org/debian-security|https://snapshot.debian.org/archive/debian-security/20240901T000000Z|g;"
              "s|http://deb.debian.org/debian|https://snapshot.debian.org/archive/debian/20240901T000000Z|g' /etc/apt/sources.list && "
              'apt-get -o Acquire::Check-Valid-Until=false update && apt-get install -y --no-install-recommends build-essential && '
              'dpkg-query -W > /opt/grader-system-packages.txt\n' if family == 'scikit-learn' else '')
    return (f"FROM {base_ref}\n" + native + f"COPY {archive_name} /opt/{archive_name}\n"
            f"RUN rm -rf /workspace /opt/repo && mkdir /workspace /opt/repo && "
            f"tar -xzf /opt/{archive_name} -C /workspace && tar -xzf /opt/{archive_name} -C /opt/repo\n"
            "WORKDIR /workspace\n"
            f"RUN {install}\n"
            "RUN cp -a /workspace/. /opt/repo/\n"
            "RUN python -m pip freeze --all > /opt/grader-environment.txt\n"
            "ENV PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=/workspace:/workspace/src\n")


def image_build(context: Path, tag: str, log: Path):
    log.parent.mkdir(parents=True, exist_ok=True)
    argv = ["docker", "--context", "desktop-linux", "build", "--pull=false", "--network=default",
        "--progress=plain", "-t", tag, str(context)]
    print('image_build: ' + tag, flush=True)
    with log.open('xb') as stream:
        result = subprocess.run(argv, stdout=stream, stderr=subprocess.STDOUT, timeout=2400)
    (log.with_suffix(".json")).write_text(json.dumps({"argv": argv, "exit_code": result.returncode,
        "combined_log_sha256": sha(log.read_bytes())}, indent=2) + "\n", encoding="utf-8")
    if result.returncode:
        raise RuntimeError("docker image build failed: " + log.read_text(encoding='utf-8', errors='replace')[-1000:])
    inspect = json.loads(subprocess.check_output(["docker", "--context", "desktop-linux", "image", "inspect", tag],
        text=True, encoding="utf-8", errors="replace"))[0]
    digest = (inspect.get("RepoDigests") or [None])[0] or tag.split(":")[0] + "@" + inspect["Id"]
    return digest, inspect


def pytest_paths(family, version, f2p, patch_paths_list):
    if family == "pytest-dev" or family == "scikit-learn" or family == "sphinx-doc":
        return f2p
    if family == "sympy":
        test_path = next((p for p in patch_paths_list if "/tests/" in p and p.endswith(".py")), None)
        if not test_path:
            raise ValueError("cannot bind sympy test file")
        return [f"{test_path}::{name}" for name in f2p]
    raise ValueError("not a pytest repository")


async def upload_runner(backend, django=False, legacy_observer=False):
    if legacy_observer:
        runner = (ROOT / 'scripts/a5_pytest_observer.py').read_bytes()
        code = "import sys;open('/tmp/a5-runner.py','wb').write(sys.stdin.buffer.read())"
        await backend._ok("exec", "-i", backend.name, "/usr/local/bin/python", "-I", "-S", "-c", code,
                          data=runner, limit=256 * 1024)
        return
    code = "import sys;open('/tmp/a5-runner.py','wb').write(sys.stdin.buffer.read())"
    await backend._ok("exec", "-i", backend.name, "/usr/local/bin/python", "-I", "-S", "-c", code,
                      data=(ROOT / 'scripts/a5_django_observer.py').read_bytes() if django else PYTEST_OBSERVER.encode(), limit=256 * 1024)


async def prepare_repo_runtime(backend, archive_name="baseline.tar.gz"):
    """Restore the image-backed source below the deliberately masked workspace."""
    await backend._ok("exec", backend.name, "/bin/sh", "-c",
        "umask 000 && cp -R /opt/repo/. /workspace/", limit=64 * 1024, timeout=120)
    # Native extensions must load from the immutable image: Docker tmpfs may
    # enforce noexec. Only build-generated .so files are linked; source members
    # are never replaced or redirected.
    code = r'''import hashlib,json,pathlib,tarfile
root=pathlib.Path('/opt/repo'); workspace=pathlib.Path('/workspace')
archive=pathlib.Path('/opt/known-good.tar.gz')
if not archive.exists(): archive=pathlib.Path('/opt/baseline.tar.gz')
with tarfile.open(archive) as stream: source={m.name for m in stream}
linked=[]
for p in root.rglob('*.so'):
    rel=p.relative_to(root).as_posix()
    if rel in source: continue  # Retain upstream binary fixtures byte-for-byte.
    target=workspace/rel
    if target.is_symlink() or target.read_bytes()!=p.read_bytes(): raise ValueError('generated native copy mismatch')
    target.unlink(); target.symlink_to(p)
    linked.append(dict(path=rel,image_path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
pathlib.Path('/tmp/a5-native-links.json').write_text(json.dumps(linked))
'''
    await backend._ok('exec', backend.name, '/usr/local/bin/python', '-I', '-S', '-c', code,
                      limit=64*1024, timeout=120)


async def run_pytest(image, args, out, timeout=900, archive_name="baseline.tar.gz", django=False, collect_only=False, sympy_native_helpers=False, seed_files=None, legacy_observer=False):
    from src.execution.base import ExecutionRequest, OutputQuotas
    from src.execution.docker import DockerExecutionBackend
    backend = DockerExecutionBackend(image=image, context="desktop-linux", memory_bytes=2 * 1024**3,
        workspace_bytes=512 * 1024**2, tmpfs_bytes=512 * 1024**2, network="none")
    evidence = {"image": image, "args": args, "status": "invalid_env", "model_calls": 0, "paid": False}
    try:
        await backend.start(seed_files or {}); evidence["isolation"] = backend.last_inspect
        if seed_files is None:
            await prepare_repo_runtime(backend, archive_name)
            evidence['generated_native_links'] = json.loads(await backend._ok('exec', backend.name,
                '/usr/local/bin/python', '-I', '-S', '-c', "print(open('/tmp/a5-native-links.json').read())", limit=4*1024**2))
        else:
            evidence['source_seed'] = {
                'mode': 'explicit_archive_files',
                'file_count': len(seed_files),
                'total_bytes': sum(len(data) for data in seed_files.values()),
            }
        await upload_runner(backend, django, legacy_observer=legacy_observer)
        payload = ({"collect_only": collect_only, "pinned_plugin_autoload": False}
                   if legacy_observer else
                   {"args": args, "labels": args, "collect_only": collect_only,
                    "sympy_native_helpers": sympy_native_helpers})
        receipt_path = "/tmp/a5-receipt.json" if legacy_observer else "/tmp/a5-pytest-receipt.json"
        request = ExecutionRequest(argv=["/usr/local/bin/python", "-I", "-B", "/tmp/a5-runner.py"],
            stdin_bytes=json.dumps(payload).encode(), env={"PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
                "PYTHONPATH": "/workspace:/workspace/src", "A5_REPO_ROOT": "/workspace",
                "PYTHONDONTWRITEBYTECODE": "1"},
            deadline_mono=time.monotonic() + timeout, artifact_dir=out,
            quotas=OutputQuotas(memory_per_stream_bytes=4 * 1024**2, artifact_per_tool_bytes=16 * 1024**2))
        execution = await backend.execute(request)
        evidence["execution"] = {"status": execution.status.value, "exit_code": execution.exit_code,
            "error_kind": execution.error_kind, "stdout": execution.stdout.text_preview,
            "stderr": execution.stderr.text_preview, "truncated": execution.truncated,
            "duration_ms": execution.duration_ms}
        if backend.active:
            try:
                raw = await backend._ok("exec", backend.name, "/usr/local/bin/python", "-I", "-S", "-c",
                    f"from pathlib import Path; import sys; p=Path('{receipt_path}'); sys.stdout.buffer.write(p.read_bytes())",
                    limit=16 * 1024**2)
                evidence["receipt"] = json.loads(raw)
            except Exception as exc:
                evidence["receipt_error"] = type(exc).__name__ + ": " + str(exc)
        evidence["status"] = "executed"
    except Exception as exc:
        evidence["reason"] = type(exc).__name__ + ": " + str(exc)
    finally:
        await backend.close()
        evidence["cleanup_verified"] = backend.cleanup_ok
        evidence["lifecycle"] = backend.lifecycle
        save(out / "evidence.json", evidence)
    return evidence


def outcomes(receipt):
    result = {}
    for report in receipt.get("reports", []):
        node = report.get("nodeid")
        if not node:
            continue
        result.setdefault(node, {})[report.get("when")] = report.get("outcome")
    final = {}
    for node, phases in result.items():
        final[node] = ("error" if 'error' in phases.values() or any(phases.get(p) == 'failed' for p in ('setup','teardown'))
            else "failed" if phases.get('call') == 'failed' else "skipped" if 'skipped' in phases.values()
            else "passed" if phases.get('call') == 'passed' else 'incomplete')
    return final


def carried_rows():
    previous = {r["task_id"]: r for r in load(PREVIOUS_ROOT / "receipts.json")["rows"]}
    transport = {r["task_id"]: r for r in load(TRANSPORT_ROOT / "receipts.json")["rows"]}
    good = {tid for tid, r in previous.items() if r.get("status") == "ready"}
    rows = {}
    for tid in good:
        r = previous[tid]; t = transport[tid]
        rows[tid] = {"task_id": tid, "repo": r["repo"], "base_revision": r["base_revision"],
            "status": "baseline_ready", "source": r["source"], "transport_mode": t["transport_mode"],
            "image_digest": r.get("image_digest"), "python_version": r.get("python_version"),
            "pytest_version": r.get("pytest_version"), "dependencies": r.get("dependencies"),
            "collection": r.get("collection"), "baseline": r.get("baseline"), "grader": r.get("grader"),
            "cleanup_verified": r.get("cleanup"), "carried_previous_attempt": True,
            "previous_receipt_ref": str(PREVIOUS_ROOT / "receipts.json"), "model_calls": 0, "paid": False,
            "reason": "exact_source_and_repo_baseline_receipt_carried_forward"}
    return rows


async def task_preflight(task, source_root, output, transport_root=TRANSPORT_ROOT):
    tid = task["canonical_id"]; source_dir = source_root / "tasks" / tid; task_out = output / "tasks" / tid
    task_out.mkdir(parents=True, exist_ok=True)
    row = {"task_id": tid, "repo": task["expected_repo"], "base_revision": task["expected_base_commit"],
        "status": "invalid_env", "attempt": 25, "retries": 0, "model_calls": 0, "paid": False,
          "source_attempt_ref": str(source_dir / "source-receipt.json"), "transport_receipt_ref": str(transport_root / "tasks" / tid / "receipt.json")}
    try:
        source = load(source_dir / "source-receipt.json")["source"]
        transport = load(transport_root / "tasks" / tid / "receipt.json")
        source_archive = source_dir / "source.tar.gz"
        if sha(source_archive.read_bytes()) != source["archive_sha256"] or transport["status"] != "transport_ready":
            raise ValueError("source/transport binding mismatch")
        private = load(source_row_path(task)); test_patch = private.get("test_patch", ""); gold_patch = private.get("patch", "")
        staging = task_out / "staging"; staging.mkdir()
        manifest, baseline_entries, gold_entries = await asyncio.to_thread(apply_patch_tree, source_archive,
            task["expected_repo"], task["expected_base_commit"], test_patch, gold_patch, staging)
        family = task["expected_repo"].split("/", 1)[0]; version = private.get("version")
        safe = tid.replace("__", "-")
        base_tag = "coding-harness-a5-transport:" + safe
        baseline_tag = "coding-harness-a5-baseline:" + safe + "-a25"
        good_tag = "coding-harness-a5-known-good:" + safe + "-a25"
        base_image = transport["image_digest"]
        base_context = task_out / "baseline-image"; base_context.mkdir()
        shutil.copy2(staging / "baseline.tar.gz", base_context / "baseline.tar.gz")
        (base_context / "Dockerfile").write_text(dockerfile(base_tag, family, version, "baseline.tar.gz"), encoding="utf-8")
        baseline_image, inspect = await asyncio.to_thread(image_build, base_context, baseline_tag, task_out / "baseline-image-build.log")
        good_context = task_out / "known-good-image"; good_context.mkdir()
        shutil.copy2(staging / "known-good.tar.gz", good_context / "known-good.tar.gz")
        (good_context / "Dockerfile").write_text(dockerfile(baseline_tag, family, version, "known-good.tar.gz"), encoding="utf-8")
        good_image, good_inspect = await asyncio.to_thread(image_build, good_context, good_tag, task_out / "known-good-image-build.log")
        row.update(source=source, transport_mode=transport["transport_mode"], transport_image_digest=base_image,
            baseline_image_digest=baseline_image, known_good_image_digest=good_image,
            baseline_image_id=inspect.get("Id"), known_good_image_id=good_inspect.get("Id"),
            private_source_binding={"path": str(source_row_path(task)), "sha256": sha(source_row_path(task).read_bytes()),
                "test_patch_sha256": sha(test_patch.encode()), "gold_patch_sha256": sha(gold_patch.encode()),
                "test_patch_paths": patch_paths(test_patch), "gold_patch_paths": patch_paths(gold_patch)},
            snapshot_binding={"original_tree_hash": manifest["source_tree_hash"], "baseline_tree_hash": sha(json.dumps(baseline_entries, sort_keys=True).encode()),
                "known_good_tree_hash": sha(json.dumps(gold_entries, sort_keys=True).encode())})
        if family == "django":
            f2p = json.loads(private["FAIL_TO_PASS"]) if isinstance(private.get("FAIL_TO_PASS"), str) else private.get("FAIL_TO_PASS", [])
            test_paths = [n.split(' ', 1)[1].strip('()') + '.' + n.split(' ', 1)[0] for n in f2p]
            collection = await run_pytest(baseline_image, [], task_out / 'collection', timeout=1800, django=True, collect_only=True)
            col = collection.get('receipt', {}); ids = col.get('collected', [])
            base = await run_pytest(baseline_image, test_paths, task_out / 'baseline', django=True)
            good = await run_pytest(good_image, test_paths, task_out / 'known-good', django=True)
            base_outcomes = outcomes(base.get('receipt', {})); good_outcomes = outcomes(good.get('receipt', {}))
            base_ok = bool(test_paths) and all(base_outcomes.get(n) == 'failed' for n in test_paths)
            good_ok = all(good_outcomes.get(n) == 'passed' for n in test_paths) and good.get('execution', {}).get('exit_code') == 0
            col_ok = collection.get('execution', {}).get('exit_code') == 0 and bool(ids) and not col.get('collection_errors')
            row.update(collection=dict(status='ready' if col_ok else 'invalid_env', count=len(ids), nodeids=ids,
                    hash=sha(json.dumps(ids).encode()), receipt_ref=str(task_out / 'collection/evidence.json')),
                baseline=dict(status='baseline_fail' if base_ok else 'baseline_invalid', outcomes=base_outcomes, failure_nodeids=test_paths,
                    receipt_ref=str(task_out / 'baseline/evidence.json')),
                grader=dict(status='pending_full_repo_grader', known_good='pass' if good_ok else 'fail', known_good_outcomes=good_outcomes),
                python_version=col.get('python'), django_version=col.get('django_version'),
                cleanup_verified=all(e.get('cleanup_verified') is True for e in (collection, base, good)))
            row['status'] = 'baseline_ready' if col_ok and base_ok and good_ok and row['cleanup_verified'] else 'invalid_env'
        else:
            f2p = json.loads(private["FAIL_TO_PASS"]) if isinstance(private.get("FAIL_TO_PASS"), str) else private.get("FAIL_TO_PASS", [])
            test_paths = pytest_paths(family, version, f2p, patch_paths(test_patch))
            root_path = "testing" if family == "pytest-dev" else ("tests" if family == "sphinx-doc" else ("sklearn" if family == "scikit-learn" else "sympy"))
            collection = await run_pytest(baseline_image, ["--collect-only", "-q", root_path], task_out / "collection", timeout=1800)
            col = collection.get("receipt", {}); ids = col.get("collected", [])
            base = await run_pytest(baseline_image, ["-q", "--tb=short"] + test_paths, task_out / "baseline", timeout=900)
            good = await run_pytest(good_image, ["-q", "--tb=short"] + test_paths, task_out / "known-good", timeout=900, archive_name="known-good.tar.gz")
            base_outcomes = outcomes(base.get("receipt", {})); good_outcomes = outcomes(good.get("receipt", {}))
            missing = [n for n in test_paths if n not in base_outcomes]
            base_ok = bool(test_paths) and not missing and all(base_outcomes.get(n) == "failed" for n in test_paths) and base.get("cleanup_verified") is True
            good_ok = not [n for n in test_paths if good_outcomes.get(n) != "passed"] and good.get("cleanup_verified") is True
            row.update(python_version=(col.get("python") or None), pytest_version=col.get("pytest_version"),
                collection={"status": "ready" if collection.get("execution", {}).get("exit_code") == 0 and ids else "invalid_env",
                    "count": len(ids), "hash": sha(json.dumps(ids).encode()), "nodeids": ids,
                    "receipt_ref": str(task_out / "collection/evidence.json"), "collection_errors": col.get("collection_errors")},
                baseline={"status": "baseline_fail" if base_ok else "baseline_invalid", "failure_nodeids": test_paths,
                    "outcomes": base_outcomes, "missing_exact_nodeids": missing, "receipt_ref": str(task_out / "baseline/evidence.json")},
                grader={"status": "pending_full_repo_grader", "known_good": "pass" if good_ok else "fail", "known_good_outcomes": good_outcomes},
                cleanup_verified=collection.get("cleanup_verified") is True and base.get("cleanup_verified") is True and good.get("cleanup_verified") is True,
                dependencies="see image pip freeze receipt")
            row["status"] = "baseline_ready" if base_ok and good_ok and row["cleanup_verified"] and row['collection']['status'] == 'ready' else "invalid_env"
        row["reason"] = "environment_collection_baseline_verified_grader_pending" if row["status"] == "baseline_ready" else "environment_or_baseline_gate_failed"
    except Exception as exc:
        row["reason"] = "environment_or_baseline_preflight_failed"; row["error"] = type(exc).__name__ + ": " + str(exc)
    save(task_out / "receipt.json", row)
    print(json.dumps({"task_id": tid, "status": row["status"], "reason": row.get("reason")}), flush=True)
    return row


async def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--only-task", action="append", default=[])
    ap.add_argument("--jobs", type=int, default=1)
    ap.add_argument('--runtime-receipt', type=Path)
    ap.add_argument('--runtime-kind', choices=['baseline', 'known-good'], default='baseline')
    ap.add_argument('--runtime-django', action='store_true')
    ap.add_argument('--runtime-arg', action='append', default=[])
    ap.add_argument('--memory-sources', action='store_true')
    ap.add_argument('--source-root', type=Path, default=SOURCE_ROOT)
    ap.add_argument('--transport-root', type=Path, default=TRANSPORT_ROOT)
    args = ap.parse_args(); output = args.output.resolve(); output.mkdir(parents=True, exist_ok=False)
    save(output / 'implementation-binding.json', {'scripts': {
        str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in
        [Path(__file__), ROOT / 'scripts/a5_django_observer.py', ROOT / 'src/execution/docker.py', ROOT / 'src/eval/a5_image_tree.py']}})
    if args.runtime_receipt:
        prior = load(args.runtime_receipt)
        image = prior['baseline_image_digest' if args.runtime_kind == 'baseline' else 'known_good_image_digest']
        save(output / 'input-binding.json', dict(receipt=str(args.runtime_receipt.resolve()),
            sha256=sha(args.runtime_receipt.read_bytes()), image=image, kind=args.runtime_kind))
        result = await run_pytest(image, args.runtime_arg, output / 'runtime', django=args.runtime_django)
        print(json.dumps(dict(task_id=prior['task_id'], exit_code=result.get('execution', {}).get('exit_code'),
            outcomes=outcomes(result.get('receipt', {})), cleanup=result.get('cleanup_verified'))), flush=True)
        return
    cbytes, pbytes = CANONICAL.read_bytes(), PROJECTION.read_bytes()
    if sha(cbytes) != CANONICAL_SHA or sha(pbytes) != PROJECTION_SHA:
        raise ValueError("canonical input drift")
    c, projection = json.loads(cbytes), json.loads(pbytes)
    tasks = ([{**task, "role": "memory_source"} for task in c["memory_build_source_pool"]]
             if args.memory_sources else c["target_tasks"] + c["preflight_history_candidates"])
    carried = {} if args.memory_sources else carried_rows()
    selected = set(args.only_task) if args.only_task else {t["canonical_id"] for t in tasks}
    semaphore = asyncio.Semaphore(args.jobs)
    async def run_one(task):
        tid = task["canonical_id"]
        if tid not in selected:
            return None
        if tid in carried and not args.only_task:
            save(output / "tasks" / tid / "receipt.json", carried[tid]); print(tid + ": baseline_ready (carried)", flush=True)
            return carried[tid]
        async with semaphore:
            return await task_preflight(task, args.source_root.resolve(), output, args.transport_root.resolve())
    rows = [r for r in await asyncio.gather(*(run_one(t) for t in tasks)) if r is not None]
    # Merge carried rows for the complete 24 denominator unless this is a narrow retry.
    if not args.only_task:
        rows_by = {r["task_id"]: r for r in rows}
        rows = [rows_by[t["canonical_id"]] for t in tasks]
    counts = {s: sum(r.get("status") == s for r in rows) for s in sorted({r.get("status") for r in rows})}
    save(output / "manifest.json", {"schema": "a5.repo-baseline-preflight.v1", "attempt": 25,
        "created_at": datetime.now(timezone.utc).isoformat(), "canonical_sha256": CANONICAL_SHA,
        "projection_sha256": PROJECTION_SHA, "assigned": len(rows), "full_denominator": len(tasks),
        "carried_ready_rows": sorted(carried), "model_calls": 0, "paid": False,
        "repo_families": sorted({t["expected_repo"].split("/", 1)[0] for t in tasks})})
    save(output / "receipts.json", {"schema": "a5.repo-baseline-preflight.receipts.v1", "rows": rows})
    save(output / "readiness.json", {"status": "baseline_ready" if len(rows) == len(tasks) and all(r.get("status") == "baseline_ready" for r in rows) else "blocked",
        "assigned": len(rows), "full_denominator": len(tasks), "status_counts": counts,
        "environment_baseline_ready": sum(r.get("status") == "baseline_ready" for r in rows),
        "grader_ready": 0, "model_calls": 0, "paid": False, "paid_build_started": False, "paid_pilot_started": False,
        "memory_build_eligible": False, "next_gate": "independent_grader_calibration_and_shared_gates"})
    save(output / "failure-retry-ledger.json", {"schema": "a5.failure-retry-ledger.v1", "attempt": 25,
        "entries": [{"task_id": r["task_id"], "status": r.get("status"), "reason": r.get("reason"), "error": r.get("error")} for r in rows],
        "model_calls": 0, "model_reservations": 0, "paid": False})
    save(output / "artifact-manifest.json", {p.relative_to(output).as_posix(): sha(p.read_bytes()) for p in sorted(output.rglob("*")) if p.is_file()})
    print(json.dumps(counts, sort_keys=True))


if __name__ == "__main__":
    asyncio.run(main())
