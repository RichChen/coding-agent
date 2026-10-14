"""Public task / private evaluation DTOs for H3.

PublicTask is the only task shape accepted by an agent-facing boundary. The
grader receives EvaluationSpec after the agent has stopped; the two objects are
intentionally not nested and cannot be serialized into one prompt payload.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from typing import Any


FORBIDDEN_PUBLIC_FIELDS = frozenset({
    "gold", "gold_patch", "hidden_tests", "hidden_test", "expected_files",
    "oracle", "answer", "future_solution", "benchmark_category", "expected", "evaluation_spec",
})


class ContractError(ValueError):
    pass


def _walk_forbidden(value: Any, path: str = "") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_PUBLIC_FIELDS:
                raise ContractError(f"forbidden public task field at {path}/{key}")
            _walk_forbidden(child, f"{path}/{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _walk_forbidden(child, f"{path}/{index}")


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":"), allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class PublicTask:
    task_id: str
    description: str
    repo_id: str | None = None
    base_revision: str | None = None
    workspace_profile: str = "docker_linux"
    budget: dict[str, Any] = field(default_factory=dict)
    public_context: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, raw: dict[str, Any]) -> "PublicTask":
        if not isinstance(raw, dict):
            raise ContractError("public task must be an object")
        _walk_forbidden(raw)
        allowed = {"id", "task_id", "description", "repo_id", "base_revision",
                   "workspace_profile", "budget", "public_context"}
        unknown = set(raw) - allowed
        if unknown:
            raise ContractError(f"unknown public task fields: {sorted(unknown)}")
        task_id = raw.get("task_id", raw.get("id"))
        if 'id' in raw and 'task_id' in raw and raw['id'] != raw['task_id']:
            raise ContractError('conflicting task identities')
        if not isinstance(task_id, str) or not task_id:
            raise ContractError("public task requires non-empty id")
        if not isinstance(raw.get("description"), str) or not raw["description"].strip():
            raise ContractError("public task requires description")
        return cls(task_id=task_id, description=raw["description"],
                   repo_id=raw.get("repo_id"), base_revision=raw.get("base_revision"),
                   workspace_profile=raw.get("workspace_profile", "docker_linux"),
                   budget=dict(raw.get("budget") or {}), public_context=dict(raw.get("public_context") or {}))

    def agent_payload(self) -> dict[str, Any]:
        return {"task_id": self.task_id, "description": self.description,
                "repo_id": self.repo_id, "base_revision": self.base_revision,
                "workspace_profile": self.workspace_profile, "budget": self.budget,
                "public_context": self.public_context}


@dataclass(frozen=True)
class TestCase:
    """Private black-box probe; expected JSON never enters the container."""
    __test__ = False
    case_id: str
    module_path: str
    function: str
    args: list
    expected: Any

    def __post_init__(self):
        from src.execution.docker import validate_files
        if not isinstance(self.case_id, str) or not self.case_id or not self.function.isidentifier():
            raise ContractError("case requires stable id and function identifier")
        validate_files({self.module_path: b""})
        if not self.module_path.endswith(".py") or not isinstance(self.args, list):
            raise ContractError("case requires Python module and JSON argument list")
        canonical_hash([self.args, self.expected])
        if len(json.dumps(self.expected, ensure_ascii=True).encode()) > 32768:
            raise ContractError("expected result exceeds comparison quota")


@dataclass(frozen=True)
class EvaluationSpec:
    task_id: str
    base_hash: str
    image: str
    editable_paths: tuple[str, ...]
    cases: tuple[TestCase, ...]
    timeout_seconds: float = 15.0

    def __post_init__(self):
        from src.execution.docker import image_is_pinned, validate_files
        if not self.task_id or not image_is_pinned(self.image):
            raise ContractError("task id and digest-pinned image required")
        if len(self.base_hash) != 64 or any(c not in '0123456789abcdef' for c in self.base_hash):
            raise ContractError("frozen base hash required")
        if not math.isfinite(self.timeout_seconds) or not 0 < self.timeout_seconds <= 120:
            raise ContractError("case timeout must be in (0, 120]")
        if not 0 < len(self.cases) <= 256 or len({c.case_id for c in self.cases}) != len(self.cases):
            raise ContractError("nonempty unique fixed test identities required (max 256)")
        validate_files({p: b"" for p in self.editable_paths})
        if any(p.rsplit('/', 1)[-1] in ('conftest.py', 'pytest.py', 'pytest.ini', 'pyproject.toml', 'setup.cfg', 'sitecustomize.py', 'usercustomize.py') for p in self.editable_paths):
            raise ContractError("test/config injection paths cannot be editable")

    @classmethod
    def from_mapping(cls, raw):
        raw = dict(raw)
        raw['cases'] = tuple(TestCase(**case) for case in raw['cases'])
        raw['editable_paths'] = tuple(raw['editable_paths'])
        return cls(**raw)

    def manifest(self):
        from dataclasses import asdict
        return dict(schema="h3.evaluation.v1", task_id=self.task_id, base_hash=self.base_hash,
                    image=self.image, editable_paths=list(self.editable_paths),
                    case_ids=[c.case_id for c in self.cases], private_spec_hash=canonical_hash(asdict(self)),
                    timeout_seconds=self.timeout_seconds, runner="isolated-python-function-v1")
