"""Capture/compare an explicit source allowlist; never archives a whole workspace."""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["capture", "compare"])
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    manifest = json.loads((ROOT / "docs/upgrade/planning-source-manifest.json").read_text())
    if args.mode == "capture":
        entries = []
        for item in manifest["files"]:
            path = ROOT / item["path"]
            if path.is_symlink() or not path.resolve().is_relative_to(ROOT):
                raise ValueError("unsafe snapshot path")
            data = path.read_bytes()
            if hashlib.sha256(data).hexdigest() != item["sha256"]:
                raise ValueError(f"baseline changed: {item['path']}")
            entries.append((item["path"], data))
        args.archive.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(args.archive, "x", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, data in entries:
                archive.writestr(name, data)
            archive.writestr("baseline-manifest.json", json.dumps(manifest, indent=2))
        print(
            json.dumps(
                {
                    "files": len(entries),
                    "archive": str(args.archive),
                    "sha256": hashlib.sha256(args.archive.read_bytes()).hexdigest(),
                }
            )
        )
        return
    if args.output is None:
        parser.error("compare requires --output")
    args.output.mkdir(parents=True, exist_ok=False)
    diffs, rows = [], []
    with zipfile.ZipFile(args.archive) as archive:
        old_names = set(archive.namelist()) - {"baseline-manifest.json"}
        new_names = {
            p.relative_to(ROOT).as_posix()
            for folder in ("reposkill_agent", "tests", "scripts", "configs")
            for p in (ROOT / folder).rglob("*")
            if p.is_file() and p.suffix in {".py", ".md", ".json", ".yaml", ".toml"}
        }
        for name in sorted(old_names | new_names):
            before = archive.read(name) if name in old_names else b""
            after = (ROOT / name).read_bytes() if (ROOT / name).is_file() else b""
            if before == after:
                continue
            rows.append(
                {
                    "path": name,
                    "before_sha256": hashlib.sha256(before).hexdigest(),
                    "after_sha256": hashlib.sha256(after).hexdigest(),
                }
            )
            diffs.extend(
                difflib.unified_diff(
                    before.decode("utf-8").splitlines(True),
                    after.decode("utf-8").splitlines(True),
                    fromfile=f"a/{name}",
                    tofile=f"b/{name}",
                )
            )
    (args.output / "changes.diff").write_text("".join(diffs), encoding="utf-8")
    (args.output / "manifest.json").write_text(
        json.dumps({"created_at": datetime.now(UTC).isoformat(), "changes": rows}, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({"changed_files": len(rows), "output": str(args.output)}))


if __name__ == "__main__":
    main()
