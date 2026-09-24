"""Strict tool-argument parsing, schema validation, and batch dispatch gate.

English: validate completeness/JSON/object/schema/enabled before any tool execute.
"""

from __future__ import annotations

import enum
import json
from dataclasses import dataclass, field
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError

from src.tools.base import Tool, ToolResult, ToolStatus
from src.tools.registry import ToolRegistry

DEFAULT_MAX_ARGUMENT_BYTES = 64 * 1024
RESERVED_ARGUMENT_KEYS = frozenset({"_call_id"})


class ToolValidationErrorKind(str, enum.Enum):
    MISSING_ID = "missing_id"
    MISSING_FUNCTION = "missing_function"
    MISSING_NAME = "missing_name"
    MISSING_ARGUMENTS = "missing_arguments"
    INVALID_JSON = "invalid_json"
    NOT_OBJECT = "not_object"
    TOO_LARGE = "too_large"
    RESERVED_FIELD = "reserved_field"
    SCHEMA = "schema"
    UNKNOWN_TOOL = "unknown_tool"
    TOOL_DISABLED = "tool_disabled"
    TOOL_CONSTRAINT = "tool_constraint"


@dataclass(frozen=True)
class ToolValidationFailure:
    call_id: str
    name: str
    kind: ToolValidationErrorKind
    message: str
    path: str | None = None

    def safe_summary(self) -> str:
        parts = [f"kind={self.kind.value}"]
        if self.path:
            parts.append(f"path={self.path}")
        parts.append(self.message)
        return "; ".join(parts)


@dataclass
class ParsedToolArguments:
    """Result of strict raw-argument parsing (no schema yet)."""

    arguments: dict[str, Any] | None = None
    raw: str = ""
    error: ToolValidationFailure | None = None


@dataclass
class ValidatedToolCall:
    call_id: str
    name: str
    arguments: dict[str, Any]
    tool: Tool
    raw_arguments: str = ""


@dataclass
class BatchValidationResult:
    ok: bool
    validated: list[ValidatedToolCall] = field(default_factory=list)
    failures: list[ToolValidationFailure] = field(default_factory=list)
    offending_ids: list[str] = field(default_factory=list)


def parse_tool_arguments_json(
    *,
    call_id: str,
    name: str,
    raw_arguments: Any,
    max_argument_bytes: int = DEFAULT_MAX_ARGUMENT_BYTES,
) -> ParsedToolArguments:
    """Parse a provider arguments JSON string into an object, or return a failure."""
    if raw_arguments is None:
        return ParsedToolArguments(
            error=ToolValidationFailure(
                call_id=call_id,
                name=name,
                kind=ToolValidationErrorKind.MISSING_ARGUMENTS,
                message="tool call arguments are missing",
            )
        )
    if not isinstance(raw_arguments, str):
        return ParsedToolArguments(
            error=ToolValidationFailure(
                call_id=call_id,
                name=name,
                kind=ToolValidationErrorKind.INVALID_JSON,
                message="tool call arguments must be a JSON string",
            )
        )

    raw = raw_arguments
    size = len(raw.encode("utf-8"))
    if size > max_argument_bytes:
        return ParsedToolArguments(
            raw=raw,
            error=ToolValidationFailure(
                call_id=call_id,
                name=name,
                kind=ToolValidationErrorKind.TOO_LARGE,
                message=(
                    f"tool arguments exceed max size "
                    f"({size} > {max_argument_bytes} bytes)"
                ),
            ),
        )

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        return ParsedToolArguments(
            raw=raw,
            error=ToolValidationFailure(
                call_id=call_id,
                name=name,
                kind=ToolValidationErrorKind.INVALID_JSON,
                message=f"invalid JSON arguments: {exc.msg}",
                path=f"line {exc.lineno} col {exc.colno}",
            ),
        )

    if not isinstance(parsed, dict):
        return ParsedToolArguments(
            raw=raw,
            error=ToolValidationFailure(
                call_id=call_id,
                name=name,
                kind=ToolValidationErrorKind.NOT_OBJECT,
                message=f"tool arguments must be a JSON object, got {type(parsed).__name__}",
            ),
        )

    return ParsedToolArguments(arguments=parsed, raw=raw)


def _json_pointer(path: list[Any]) -> str:
    if not path:
        return "/"
    parts: list[str] = []
    for part in path:
        if isinstance(part, int):
            parts.append(str(part))
        else:
            text = str(part).replace("~", "~0").replace("/", "~1")
            parts.append(text)
    return "/" + "/".join(parts)


def validate_against_schema(
    *,
    call_id: str,
    name: str,
    arguments: dict[str, Any],
    schema: dict[str, Any],
) -> ToolValidationFailure | None:
    """Validate arguments against a tool's JSON Schema. Does not inject defaults."""
    for key in RESERVED_ARGUMENT_KEYS:
        if key in arguments:
            return ToolValidationFailure(
                call_id=call_id,
                name=name,
                kind=ToolValidationErrorKind.RESERVED_FIELD,
                message=f"reserved argument field '{key}' is not allowed from the model",
                path=f"/{key}",
            )

    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(arguments), key=lambda e: list(e.path))
    if not errors:
        return None

    err: JsonSchemaValidationError = errors[0]
    path = _json_pointer(list(err.absolute_path))
    return ToolValidationFailure(
        call_id=call_id,
        name=name,
        kind=ToolValidationErrorKind.SCHEMA,
        message=err.message,
        path=path,
    )


def validate_run_command_constraint(
    *,
    call_id: str,
    name: str,
    arguments: dict[str, Any],
) -> ToolValidationFailure | None:
    """Enforce command/argv mutual exclusivity for run_command."""
    if name != "run_command":
        return None

    has_command = "command" in arguments and arguments["command"] not in (None, "")
    has_argv = "argv" in arguments and arguments["argv"] not in (None, [])

    if has_command and has_argv:
        return ToolValidationFailure(
            call_id=call_id,
            name=name,
            kind=ToolValidationErrorKind.TOOL_CONSTRAINT,
            message="run_command requires either command or argv, not both",
            path="/",
        )
    if not has_command and not has_argv:
        return ToolValidationFailure(
            call_id=call_id,
            name=name,
            kind=ToolValidationErrorKind.TOOL_CONSTRAINT,
            message="run_command requires either command or argv",
            path="/",
        )
    return None


def validate_single_tool_call(
    *,
    call_id: str,
    name: str,
    arguments: dict[str, Any],
    registry: ToolRegistry,
    enabled_tools: list[str] | None,
) -> tuple[ValidatedToolCall | None, ToolValidationFailure | None]:
    """Validate one already-parsed tool call against registry/enabled/schema."""
    tool = registry.get(name)
    if tool is None:
        return None, ToolValidationFailure(
            call_id=call_id,
            name=name,
            kind=ToolValidationErrorKind.UNKNOWN_TOOL,
            message=f"unknown tool: {name}",
        )

    if enabled_tools is not None and name not in enabled_tools:
        return None, ToolValidationFailure(
            call_id=call_id,
            name=name,
            kind=ToolValidationErrorKind.TOOL_DISABLED,
            message=f"tool is registered but not enabled: {name}",
        )

    schema_err = validate_against_schema(
        call_id=call_id,
        name=name,
        arguments=arguments,
        schema=tool.parameters,
    )
    if schema_err is not None:
        return None, schema_err

    constraint_err = validate_run_command_constraint(
        call_id=call_id,
        name=name,
        arguments=arguments,
    )
    if constraint_err is not None:
        return None, constraint_err

    return (
        ValidatedToolCall(
            call_id=call_id,
            name=name,
            arguments=dict(arguments),
            tool=tool,
        ),
        None,
    )


def validate_tool_call_batch(
    calls: list[Any],
    *,
    registry: ToolRegistry,
    enabled_tools: list[str] | None,
) -> BatchValidationResult:
    """Validate every call first; if any fails, none are dispatchable.

    ``calls`` items may be ``ToolCall``-like objects with
    ``id``, ``name``, ``arguments`` (dict|None), optional ``parse_error``.
    """
    validated: list[ValidatedToolCall] = []
    failures: list[ToolValidationFailure] = []

    for call in calls:
        call_id = getattr(call, "id", "") or ""
        name = getattr(call, "name", "") or ""
        parse_error = getattr(call, "parse_error", None)
        if parse_error is not None:
            failures.append(parse_error)
            continue

        arguments = getattr(call, "arguments", None)
        if arguments is None:
            failures.append(
                ToolValidationFailure(
                    call_id=call_id,
                    name=name,
                    kind=ToolValidationErrorKind.INVALID_JSON,
                    message="tool arguments were not successfully parsed",
                )
            )
            continue
        if not isinstance(arguments, dict):
            failures.append(
                ToolValidationFailure(
                    call_id=call_id,
                    name=name,
                    kind=ToolValidationErrorKind.NOT_OBJECT,
                    message="tool arguments must be an object",
                )
            )
            continue

        item, err = validate_single_tool_call(
            call_id=call_id,
            name=name,
            arguments=arguments,
            registry=registry,
            enabled_tools=enabled_tools,
        )
        if err is not None:
            failures.append(err)
        elif item is not None:
            raw = getattr(call, "raw_arguments", "") or ""
            item.raw_arguments = raw
            validated.append(item)

    if failures:
        return BatchValidationResult(
            ok=False,
            validated=[],
            failures=failures,
            offending_ids=[f.call_id for f in failures if f.call_id],
        )

    return BatchValidationResult(ok=True, validated=validated, failures=[], offending_ids=[])


def validation_failure_to_tool_result(failure: ToolValidationFailure) -> ToolResult:
    """Map a validation failure to a blocked ToolResult (legacy success=False)."""
    return ToolResult(
        call_id=failure.call_id,
        name=failure.name or "unknown",
        success=False,
        output="",
        error=failure.safe_summary(),
        status=ToolStatus.BLOCKED,
        error_kind=failure.kind.value,
    )
