"""Bind evidence and complete archives without repeatedly hashing extracted copies."""
import argparse
import hashlib
import json
import os
from pathlib import Path


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    files = {}
    for parent, dirs, names in os.walk(root):
        if Path(parent).name == 'staging':
            dirs[:] = []  # Full trees are bound by the archives, not omitted from them.
        for name in names:
            path = Path(parent) / name
            if name == 'artifact-manifest.json': continue
            files[path.relative_to(root).as_posix()] = digest(path)
    with (root / 'artifact-manifest.json').open('x', encoding='utf-8') as stream:
        json.dump(dict(schema='a5.archive-and-evidence-manifest.v1', files=files,
            extracted_copies='retained; canonical identity is in complete archives and typed-tree bindings'), stream, indent=2)
    print(json.dumps(dict(bound_artifacts=len(files), root=str(root))))


if __name__ == '__main__': main()
