"""Map harness grader scores onto memory-card verification labels.

The expected file is ``memory-source-verification.json`` from coding-harness.
Missing file, unknown source, or any status other than pass/partial/fail
becomes ``unverified``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

VerificationStatus = Literal[
    "validated_fix", "partial_attempt", "failed_attempt", "unverified"
]

_STATUS = {
    "pass": "validated_fix",
    "partial": "partial_attempt",
    "fail": "failed_attempt",
}


def map_grader_status(raw: str) -> VerificationStatus:
    mapped = _STATUS.get(raw)
    if mapped is None:
        return "unverified"
    return mapped  # type: ignore[return-value]


def load_source_verification(path: Path, source_ids: tuple[str, ...]) -> dict[str, VerificationStatus]:
    labels: dict[str, VerificationStatus] = {source_id: "unverified" for source_id in source_ids}
    if not path.is_file():
        return labels
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = _rows(payload)
    for row in rows:
        source_id = str(row.get("source_id", ""))
        if source_id not in labels:
            continue
        labels[source_id] = map_grader_status(str(row.get("status", "")))
    return labels


def _rows(payload: object) -> list[dict]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("results", "records", "sources"):
        value = payload.get(key)
        if isinstance(value, list):
            return [row for row in value if isinstance(row, dict)]
    if payload and all(isinstance(value, str) for value in payload.values()):
        return [{"source_id": key, "status": value} for key, value in payload.items()]
    return []
