"""Private-side preparation of ONE synthetic task for a future H4 smoke run.

No harness import, Docker, model call, or private grader execution occurs here.
Only public-workspace/ may be mounted as the agent workspace.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from pydantic import Field

from reposkill_agent.eval.public_export import checked_path
from reposkill_agent.integrations.harness_h4 import RepoSkillH4Plugin, harness_public_task
from reposkill_agent.protocol.evaluation import EvaluationSpec
from reposkill_agent.protocol.public import (
    Budget,
    PublicContext,
    PublicTask,
    RepoRef,
    StrictModel,
    canonical,
    digest,
)

TASK_ID = "public-settings-001"
SEED = {
    "settings.py": (
        '"""Read line-based application settings."""\n\n'
        "def parse_settings(text):\n"
        '    return dict(line.split("=") for line in text.splitlines())\n'
    ),
    "public_checks.py": (
        '"""Small public reproduction; no private grader material."""\n'
        "from settings import parse_settings\n\n"
        'assert parse_settings("name=demo\\n\\n") == {"name": "demo"}\n'
    ),
}


class H3Case(StrictModel):
    case_id: str
    module_path: str = "settings.py"
    function: str = "parse_settings"
    args: list[str]
    expected: dict[str, str]


class H3EvaluationSpec(StrictModel):
    """Private fixture projection of the H3 evaluator's actual JSON shape."""

    task_id: str
    base_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    image: str = Field(pattern=r"^[^\s@]+@sha256:[0-9a-f]{64}$")
    editable_paths: tuple[str, ...] = ("settings.py",)
    cases: tuple[H3Case, ...]
    timeout_seconds: float = 15.0


def prepare_h4_fixture(output: Path, *, image: str) -> dict:
    """Write a new, bounded bundle; refuse replacement of an earlier run."""
    # Same tree hash algorithm as harness src/eval/grader.py: hash a canonical
    # path->content-SHA256 mapping. This is distinct from our export audit hash.
    files = {path: digest(text) for path, text in SEED.items()}
    base_hash = digest(canonical(files))
    task = PublicTask(
        task_id=TASK_ID,
        issue_text=(
            "parse_settings fails when settings contain blank lines or an '=' inside a value. "
            "Ignore empty/whitespace-only lines, split each setting at its first '=', and trim "
            "spaces around names and values. Empty input returns an empty mapping. "
            "Use public_checks.py to reproduce the blank-line failure."
        ),
        repo_ref=RepoRef(repo_id="public-settings-fixture", revision=base_hash),
        workspace_id="public-settings-workspace",
        allowed_tools=("read", "search", "patch", "public_test"),
        execution_profile_ref="docker_linux",
        public_context=PublicContext(public_test_commands=("python public_checks.py",)),
        budget=Budget(
            wall_seconds=120,
            model_calls=4,
            input_tokens=12000,
            output_tokens=4000,
            tool_calls=8,
        ),
    )
    evaluation = H3EvaluationSpec(
        task_id=TASK_ID,
        base_hash=base_hash,
        image=image,
        cases=(
            H3Case(case_id="private-empty", args=["\n \t\n"], expected={}),
            H3Case(case_id="private-separator", args=["token=a=b=c"], expected={"token": "a=b=c"}),
            H3Case(
                case_id="PRIVATE_H4_CANARY_7f2c",
                args=[" x = z \n\ny= q \n"],
                expected={"x": "z", "y": "q"},
            ),
            H3Case(case_id="private-basic", args=["a=1\nb=2"], expected={"a": "1", "b": "2"}),
        ),
    )
    index = EvaluationSpec(
        task_id=TASK_ID,
        hidden_test_refs=("private/evaluation-spec.json",),
    )
    h3_public = harness_public_task(task)
    description = json.dumps(h3_public, ensure_ascii=False)
    public_message = {"role": "user", "content": description}
    policy_input = {
        "schema_version": "0.1",
        "task": {"task_id": task.task_id, "issue_text": description},
        "repo_revision": base_hash,
        "observations": [{"role": "user", "sha256": digest(canonical(public_message))}],
        "budget": {},
        "state": {},
    }
    plugin_on = asyncio.run(RepoSkillH4Plugin(task, tuple(SEED)).decide(policy_input))
    plugin_off = asyncio.run(
        RepoSkillH4Plugin(task, tuple(SEED), enabled=False).decide(policy_input)
    )
    documents = {
        "agent-public-task.json": task.model_dump(mode="json"),
        "public-task.json": h3_public,
        "private/evaluation-spec.json": evaluation.model_dump(mode="json"),
        "private/agent-evaluation-index.json": index.model_dump(mode="json"),
        "fixture/policy-input.json": policy_input,
        "fixture/raw-messages.json": [public_message],
        "fixture/plugin-on-decision.json": plugin_on,
        "fixture/plugin-off-decision.json": plugin_off,
    }
    artifacts = {f"public-workspace/{path}": text.encode() for path, text in SEED.items()}
    artifacts.update({p: (canonical(d) + "\n").encode() for p, d in documents.items()})
    manifest = {
        "schema_version": "1.0",
        "kind": "h4-preparation-only",
        "task_id": TASK_ID,
        "protocol_mode": "realistic",
        "policy_wire": "0.1",
        "base_hash": base_hash,
        "public_files": files,
        "artifacts": {p: digest(b) for p, b in artifacts.items()},
        "external_model_calls": 0,
        "tool_calls_executed": 0,
        "actual_model_injection": False,
        "repair_success": None,
        "memory_snapshot": "empty",
        "image_availability": "not_checked",
        "host_budget_requirements": {
            "max_model_calls": 4,
            "max_tokens": 16000,
            "max_steps": 8,
            "total_timeout_seconds": 120,
            "step_timeout_seconds": 30,
            "model_max_output_tokens": 4000,
            "max_injection_bytes": 4096,
            "context_strategy": "none",
            "context_max_tokens": 24000,
            "cost_cap": "freeze_with_provider_price_before_real_api",
        },
        "real_api_ready": False,
        "pending": [
            "harness_real_run_success_evidence",
            "host_custom_plugin_registration_and_persistent_fingerprint",
            "fixed_model_price_and_cost_cap",
            "verify_pinned_image_available",
        ],
        "limitations": [
            "H4 observations contain hashes only; no content resolver",
            "H4 rejects action proposals with dispatcher_not_enabled",
            "H4 prepared-view injection is not model-operation receipt",
        ],
    }
    artifacts["manifest.json"] = (canonical(manifest) + "\n").encode()
    output = output.absolute()
    for parent in output.parents:
        if parent.exists():
            checked_path(parent, "h4-output-check")
            break
    output.mkdir(parents=True, exist_ok=False)
    for relative, data in artifacts.items():
        path = output / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(data)
    return manifest
