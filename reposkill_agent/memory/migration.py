"""Explicit legacy import: no guessed provenance, never modifies the source."""

from datetime import UTC, datetime
from pathlib import Path

from reposkill_agent.memory.record_store import RecordStore
from reposkill_agent.memory.records import BuildUsage, MemoryRecord, contains_secret
from reposkill_agent.protocol.public import canonical, digest, reject_oracle


def import_legacy(source: Path, destination: RecordStore) -> list[dict]:
    import json

    if source.resolve() == destination.path.resolve():
        raise ValueError("migration_requires_new_store")
    audit = []
    for number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        reference = digest(line)
        try:
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("malformed_record")
            reject_oracle(raw)
            if contains_secret(line):
                raise ValueError("secret_content")
            text = raw.get("pattern") or raw.get("successful_pattern")
            if not isinstance(text, str) or not text.strip():
                raise ValueError("missing_procedure")
            record = MemoryRecord(
                memory_id="legacy-" + reference,
                kind="procedure",
                procedure=text,
                content_hash=digest(text),
                verification_recipe="requires_public_revalidation",
                source_repo_id="unknown",
                created_at=datetime.now(UTC),
                build_usage=BuildUsage(method="rule"),
            )
            destination.append(record, reason="legacy_unverified")
            audit.append(
                {
                    "line": number,
                    "source_hash": reference,
                    "status": "candidate",
                    "validity": "unknown",
                }
            )
        except (ValueError, TypeError):
            # No rejected content or filenames in public quarantine audit.
            audit.append(
                {
                    "line": number,
                    "source_hash": reference,
                    "status": "quarantined",
                    "reason": "unsafe_or_invalid_legacy",
                }
            )
    return json.loads(canonical(audit))
