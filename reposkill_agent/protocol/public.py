"""Strict public DTOs; data validation is not an operating-system sandbox."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import PurePosixPath
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
ProtocolMode = Literal["realistic", "diagnostic_oracle"]
FORBIDDEN = frozenset(
    {
        "expectedfiles",
        "tags",
        "gold",
        "goldpatch",
        "hiddentests",
        "hiddentest",
        "category",
        "benchmarkcategory",
        "futuretrajectory",
        "evaluationspec",
    }
)


def digest(data: bytes | str) -> str:
    return hashlib.sha256(data.encode() if isinstance(data, str) else data).hexdigest()


def canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def safe_relative(value: str) -> str:
    """Reject ambiguous paths, credentials and Windows aliases on every platform."""
    if not value or "\\" in value or ":" in value or "\x00" in value:
        raise ValueError("unsafe_relative_path")
    parts = value.split("/")
    reserved = {
        "con",
        "prn",
        "aux",
        "nul",
        *(f"com{i}" for i in range(1, 10)),
        *(f"lpt{i}" for i in range(1, 10)),
    }
    for part in parts:
        lower = part.lower()
        if (
            part in {"", ".", ".."}
            or part.endswith((" ", "."))
            or lower.split(".")[0] in reserved
            or lower in {".git", ".env", ".ssh", ".codex", ".agents", "__pycache__"}
            or lower.startswith(".env.")
            or lower.endswith((".pem", ".key", ".pyc"))
        ):
            raise ValueError("unsafe_relative_path")
    if PurePosixPath(value).is_absolute():
        raise ValueError("unsafe_relative_path")
    return value


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, validate_default=True)


class Versioned(StrictModel):
    schema_version: str = "1.0"

    @field_validator("schema_version")
    @classmethod
    def supported(cls, value: str) -> str:
        if not re.fullmatch(r"1\.\d+", value):
            raise ValueError("unsupported_schema_major")
        return value


class ArtifactRef(StrictModel):
    logical_id: str = Field(min_length=1)
    sha256: Digest
    size_bytes: int = Field(ge=0)
    media_type: str = "text/plain"
    run_id: str = Field(min_length=1)
    relative_path: str
    sensitivity: Literal["public_observation"] = "public_observation"

    _path = field_validator("relative_path")(safe_relative)


class RepoRef(StrictModel):
    repo_id: str = Field(min_length=1)
    revision: str = Field(min_length=1)
    revision_kind: Literal["commit", "snapshot"] = "snapshot"


class Budget(StrictModel):
    wall_seconds: int = Field(gt=0)
    model_calls: int = Field(ge=0)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    tool_calls: int = Field(ge=0)
    retry_limit: int = Field(default=0, ge=0)
    max_cost: float | None = Field(default=None, ge=0)
    currency: str | None = None

    @model_validator(mode="after")
    def money_pair(self):
        if (self.max_cost is None) != (self.currency is None):
            raise ValueError("budget_currency_required_with_cost")
        return self


class PublicContext(StrictModel):
    reproduction: tuple[str, ...] = ()
    public_test_commands: tuple[str, ...] = ()
    observations: tuple[ArtifactRef, ...] = ()


class PublicTask(Versioned):
    task_id: str = Field(min_length=1)
    task_family: Literal["code_repair"] = "code_repair"
    issue_text: str = Field(min_length=1, max_length=20000)
    repo_ref: RepoRef
    public_context: PublicContext = Field(default_factory=PublicContext)
    workspace_id: str = Field(min_length=1)
    allowed_tools: tuple[Literal["read", "search", "patch", "public_test"], ...]
    execution_profile_ref: str = Field(min_length=1)
    budget: Budget
    protocol_mode: ProtocolMode = "realistic"
    seed: int | None = None
    repeat_id: int = Field(default=0, ge=0)


class BoundaryError(ValueError):
    """Safe public diagnostic: never includes rejected values or private filenames."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def reject_oracle(value: object) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = re.sub(r"[^a-z]", "", str(key).lower())
            if normalized in FORBIDDEN:
                raise BoundaryError("oracle_field_present")
            reject_oracle(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            reject_oracle(child)


def decode_public_task(payload: dict) -> tuple[PublicTask, tuple[str, ...]]:
    """Accept newer minor top-level extensions, never feed them into strategy state."""
    reject_oracle(payload)
    version = payload.get("schema_version", "1.0")
    if not isinstance(version, str) or not re.fullmatch(r"1\.\d+", version):
        raise BoundaryError("unsupported_schema_major")
    extras = set(payload) - set(PublicTask.model_fields)
    if extras and version == "1.0":
        raise BoundaryError("unknown_public_field")
    projected = {k: v for k, v in payload.items() if k in PublicTask.model_fields}
    projected["schema_version"] = "1.0"
    try:
        task = PublicTask.model_validate(projected)
    except ValidationError:
        raise BoundaryError("invalid_public_task") from None
    # Do not expose extension names/values, which may themselves contain private data.
    return task, (("minor_extensions_ignored",) if extras else ())
