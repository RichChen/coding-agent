"""Read-only: show a test-patch path inside baseline.tar.gz that is absent from original."""
import tarfile
from pathlib import Path

root = Path("docs/upgrade/evidence/A5-harness-preflight-57-remaining16-baseline/tasks/django__django-11039/staging")
rel = "tests/migrations/test_commands.py"
needle = "def test_sqlmigrate_for_non_transactional_databases"
original = (root / "original" / rel).read_text(encoding="utf-8", errors="replace")
with tarfile.open(root / "baseline.tar.gz", "r:gz") as archive:
    member = archive.extractfile(rel)
    if member is None:
        raise SystemExit("missing member")
    packed = member.read().decode("utf-8", errors="replace")
print("original_has_needle", needle in original)
print("baseline_tar_has_needle", needle in packed)
print("bytes_differ", original.encode("utf-8") != packed.encode("utf-8"))
print("tar_bytes", len(packed.encode("utf-8")))
