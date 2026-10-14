"""Private-side, explicit allowlist export. The runtime must enforce mount isolation."""

from __future__ import annotations

import stat
from pathlib import Path

from pydantic import Field, field_validator

from reposkill_agent.protocol.evaluation import EvaluationSpec
from reposkill_agent.protocol.public import (
    BoundaryError,
    Digest,
    PublicTask,
    StrictModel,
    canonical,
    digest,
    safe_relative,
)


class ExportFile(StrictModel):
    path: str
    sha256: Digest
    public_test: bool = False

    _path = field_validator("path")(safe_relative)


class ExportManifest(StrictModel):
    repo_id: str
    revision: str
    reviewed_public: bool = False
    files: tuple[ExportFile, ...] = Field(min_length=1)


def checked_path(root: Path, relative: str) -> Path:
    """Reject links/reparse points in the entire selected path before reading."""
    safe_relative(relative)
    for parent in (root, *root.parents):
        if parent.is_symlink() or (
            parent.exists()
            and getattr(parent.lstat(), "st_file_attributes", 0)
            & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        ):
            raise BoundaryError("unsafe_export_path")
    candidate = root
    for part in (".", *relative.split("/")):
        candidate = candidate / part
        if candidate.is_symlink() or (
            candidate.exists()
            and getattr(candidate.lstat(), "st_file_attributes", 0)
            & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        ):
            raise BoundaryError("unsafe_export_path")
    if not candidate.resolve().is_relative_to(root.resolve()):
        raise BoundaryError("unsafe_export_path")
    return candidate


def export_public_workspace(
    source: Path,
    destination: Path,
    task: PublicTask,
    manifest: ExportManifest,
    evaluation: EvaluationSpec,
) -> dict:
    """Export only previously reviewed bytes to a new sibling task workspace.

    Arbitrary file contents cannot be classified as public automatically. The manifest
    is a trusted, private data-preparation artifact, not agent/model-generated input.
    """
    source = source.absolute()
    destination = destination.absolute()
    # Existing ancestors of the destination must not redirect writes through junctions.
    for parent in destination.parents:
        if parent.exists():
            checked_path(parent, "destination-check")
            break
    if (
        destination.exists()
        or source.resolve().is_relative_to(destination.resolve())
        or destination.resolve().is_relative_to(source.resolve())
    ):
        raise BoundaryError("unsafe_export_destination")
    if (
        not manifest.reviewed_public
        or evaluation.task_id != task.task_id
        or manifest.repo_id != task.repo_ref.repo_id
        or manifest.revision != task.repo_ref.revision
    ):
        raise BoundaryError("unreviewed_or_mismatched_manifest")
    private = {p.replace("\\", "/").casefold() for p in evaluation.hidden_test_refs}
    private.update(p.replace("\\", "/").casefold() for p in evaluation.future_trajectory_refs)
    seen, content = set(), []
    for item in manifest.files:
        is_private = any(
            item.path.casefold() == p or item.path.casefold().startswith(p + "/") for p in private
        )
        if item.path.casefold() in seen or is_private:
            raise BoundaryError("private_or_duplicate_export")
        seen.add(item.path.casefold())
        data = checked_path(source, item.path).read_bytes()
        if digest(data) != item.sha256:
            raise BoundaryError("export_content_changed")
        content.append((item.path, data))
    # Validate all files before any writes. Refuse existing output; never overwrite user data.
    destination.mkdir(parents=True, exist_ok=False)
    for relative, data in content:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as handle:
            handle.write(data)
    files = [{"path": p, "sha256": digest(b), "size_bytes": len(b)} for p, b in content]
    return {
        "protocol_mode": task.protocol_mode,
        "workspace_id": task.workspace_id,
        "files": files,
        "snapshot_hash": digest(canonical(files)),
        "audit": ["reviewed_allowlist_export"],
        "isolation": "data_export_only",
    }
