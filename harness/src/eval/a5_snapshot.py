"""A5 large-repository snapshot transport primitives.

Runtime Docker transfer remains bounded at 8 MiB/2048 files.  A complete
source tree larger than that is therefore an image-build input; a stopped
agent returns only a content-addressed delta against the frozen image source.
No file is silently omitted or truncated.
"""
from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Iterable

from src.execution.docker import MAX_FILES, TRANSFER_LIMIT

CHUNK_BYTES = 7 * 1024 * 1024
SCHEMA = "a5.snapshot.manifest.v1"
DELTA_SCHEMA = "a5.snapshot.delta.v1"


def _path(name: str) -> None:
    p = PurePosixPath(name)
    if (not isinstance(name, str) or not name or str(p) != name or p.is_absolute()
            or ".." in p.parts or "\\" in name or ":" in name or "\x00" in name):
        raise ValueError(f"unsafe snapshot path: {name!r}")


def _files(files: dict[str, bytes], *, enforce_runtime=False) -> dict[str, bytes]:
    if not isinstance(files, dict) or not files:
        raise ValueError("complete snapshot must contain files")
    if enforce_runtime and len(files) > MAX_FILES:
        raise ValueError("runtime file-count quota exceeded")
    total = 0
    result = {}
    for name, data in files.items():
        _path(name)
        if not isinstance(data, bytes):
            raise ValueError(f"snapshot content is not bytes: {name}")
        # A complete image-backed source tree is allowed to contain a file
        # larger than the runtime transfer envelope.  The envelope is applied
        # only when the files are sent directly to a live container.
        if enforce_runtime and len(data) > TRANSFER_LIMIT:
            raise ValueError(f"single file exceeds transfer quota: {name}")
        total += len(data)
        result[name] = data
    if enforce_runtime and total > TRANSFER_LIMIT:
        raise ValueError("runtime snapshot transfer quota exceeded")
    return result


def tree_hash(files: dict[str, bytes]) -> str:
    """Hash the complete tree without applying the runtime 8 MiB quota."""
    files = _files(files)
    h = hashlib.sha256()
    for name in sorted(files):
        encoded = name.encode("utf-8")
        h.update(len(encoded).to_bytes(8, "big"))
        h.update(encoded)
        h.update(len(files[name]).to_bytes(8, "big"))
        h.update(files[name])
    return h.hexdigest()


def chunk_bytes(data: bytes, *, chunk_bytes: int = CHUNK_BYTES) -> list[bytes]:
    if not isinstance(data, bytes) or type(chunk_bytes) is not int or not 0 < chunk_bytes <= CHUNK_BYTES:
        raise ValueError("invalid chunk input")
    return [data[i:i + chunk_bytes] for i in range(0, len(data), chunk_bytes)] or [b""]


def _canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


@dataclass(frozen=True)
class SnapshotManifest:
    task_id: str
    repo: str
    base_revision: str
    source_tree_hash: str
    file_count: int
    total_bytes: int
    files: dict[str, dict[str, object]]
    archive_sha256: str | None
    archive_bytes: int | None
    chunks: tuple[dict[str, object], ...]
    transport_mode: str
    schema: str = SCHEMA

    def __post_init__(self):
        if self.schema != SCHEMA or not self.task_id or not self.repo or not self.base_revision:
            raise ValueError("invalid snapshot manifest identity")
        if self.file_count != len(self.files) or self.file_count <= 0:
            raise ValueError("manifest file count mismatch")
        if self.total_bytes < 0 or len(self.source_tree_hash) != 64:
            raise ValueError("invalid manifest sizes/hash")
        if self.transport_mode not in ("runtime_full", "image_backed_base_plus_delta"):
            raise ValueError("unsupported snapshot transport mode")
        if self.transport_mode == "image_backed_base_plus_delta" and not self.chunks:
            raise ValueError("large source requires archive chunks")
        if self.chunks and (self.archive_sha256 is None or self.archive_bytes is None):
            raise ValueError("archive chunks require archive identity")
        if self.archive_bytes is not None and self.archive_bytes < 0:
            raise ValueError("invalid archive size")
        metadata_total = 0
        for name, meta in self.files.items():
            _path(name)
            if not isinstance(meta, dict) or type(meta.get("size")) is not int or meta["size"] < 0:
                raise ValueError("invalid file manifest metadata")
            if not isinstance(meta.get("sha256"), str) or len(meta["sha256"]) != 64:
                raise ValueError("invalid file manifest hash")
            metadata_total += meta["size"]
        if metadata_total != self.total_bytes:
            raise ValueError("manifest byte count mismatch")

    def to_dict(self):
        return {
            "schema": self.schema, "task_id": self.task_id, "repo": self.repo,
            "base_revision": self.base_revision, "source_tree_hash": self.source_tree_hash,
            "file_count": self.file_count, "total_bytes": self.total_bytes,
            "files": self.files, "archive_sha256": self.archive_sha256,
            "archive_bytes": self.archive_bytes, "chunks": list(self.chunks),
            "transport_mode": self.transport_mode,
        }


def build_manifest(files: dict[str, bytes], *, task_id: str, repo: str, base_revision: str,
                   archive: bytes | None = None) -> SnapshotManifest:
    files = _files(files)
    if archive is not None and not isinstance(archive, bytes):
        raise ValueError("archive must be bytes")
    chunks = []
    if archive is not None:
        for index, chunk in enumerate(chunk_bytes(archive)):
            chunks.append({"index": index, "size": len(chunk), "sha256": hashlib.sha256(chunk).hexdigest()})
    total = sum(map(len, files.values()))
    mode = "runtime_full" if total <= TRANSFER_LIMIT and len(files) <= MAX_FILES else "image_backed_base_plus_delta"
    if mode == "image_backed_base_plus_delta" and archive is None:
        raise ValueError("large source requires immutable archive for image build")
    return SnapshotManifest(task_id, repo, base_revision, tree_hash(files), len(files), total,
        {n: {"size": len(b), "sha256": hashlib.sha256(b).hexdigest()} for n, b in sorted(files.items())},
        hashlib.sha256(archive).hexdigest() if archive is not None else None,
        len(archive) if archive is not None else None, tuple(chunks), mode)


def verify_archive(manifest: SnapshotManifest, archive: bytes) -> list[bytes]:
    if manifest.archive_sha256 != hashlib.sha256(archive).hexdigest() or manifest.archive_bytes != len(archive):
        raise ValueError("source archive hash/size mismatch")
    chunks = chunk_bytes(archive)
    if len(chunks) != len(manifest.chunks):
        raise ValueError("source archive chunk count mismatch")
    for index, (expected, chunk) in enumerate(zip(manifest.chunks, chunks)):
        if expected != {"index": index, "size": len(chunk), "sha256": hashlib.sha256(chunk).hexdigest()}:
            raise ValueError("source archive chunk mismatch")
    return chunks


def make_delta(base: dict[str, bytes], candidate: dict[str, bytes], *, allowed_paths: Iterable[str]) -> dict:
    base, candidate = _files(base), _files(candidate)
    allowed = set(allowed_paths)
    for name in allowed:
        _path(name)
    changed = sorted(name for name in base.keys() | candidate.keys() if base.get(name) != candidate.get(name))
    if set(changed) - allowed:
        raise ValueError("candidate changed path outside A5 editable allowlist")
    if len(changed) > MAX_FILES:
        raise ValueError("candidate delta file-count quota exceeded")
    delta = {
        "schema": DELTA_SCHEMA, "base_tree_hash": tree_hash(base), "candidate_tree_hash": tree_hash(candidate),
        "changed": {name: base64.b64encode(candidate[name]).decode("ascii") for name in changed if name in candidate},
        "deleted": [name for name in changed if name not in candidate],
    }
    if len(_canonical(delta)) > TRANSFER_LIMIT:
        raise ValueError("candidate delta exceeds runtime transfer quota")
    return delta


def apply_delta(base: dict[str, bytes], delta: dict, *, allowed_paths: Iterable[str]) -> dict[str, bytes]:
    base = _files(base)
    if not isinstance(delta, dict) or delta.get("schema") != DELTA_SCHEMA:
        raise ValueError("invalid snapshot delta schema")
    if delta.get("base_tree_hash") != tree_hash(base):
        raise ValueError("delta base tree hash mismatch")
    allowed = set(allowed_paths)
    changed = delta.get("changed")
    deleted = delta.get("deleted")
    if not isinstance(changed, dict) or not isinstance(deleted, list) or set(changed) & set(deleted):
        raise ValueError("invalid delta changes")
    if len(changed) + len(deleted) > MAX_FILES:
        raise ValueError("candidate delta file-count quota exceeded")
    if (set(changed) | set(deleted)) - allowed:
        raise ValueError("delta contains unassigned path")
    if len(_canonical(delta)) > TRANSFER_LIMIT:
        raise ValueError("candidate delta exceeds runtime transfer quota")
    result = dict(base)
    for name, encoded in changed.items():
        _path(name)
        result[name] = base64.b64decode(encoded, validate=True)
    for name in deleted:
        _path(name)
        result.pop(name, None)
    _files(result)
    if delta.get("candidate_tree_hash") != tree_hash(result):
        raise ValueError("delta candidate tree hash mismatch")
    return result
