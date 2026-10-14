"""Optional Aider external baseline — skip when CLI unavailable."""

from __future__ import annotations

import os
import shutil

from reposkill_agent.baselines.contracts import BaselineRunRequest, BaselineRunResult
from reposkill_agent.baselines.external_command import ExternalCommandBaseline


def _aider_available() -> tuple[bool, str]:
    if shutil.which("aider") is None:
        return False, "aider CLI not found on PATH; install Aider separately (not vendored)"
    if not os.environ.get("LLM_API_KEY", "").strip():
        return False, "LLM_API_KEY not set for Aider baseline"
    return True, ""


def _build_aider_command(workspace, request: BaselineRunRequest) -> str:
    issue = request.issue.replace('"', "'")
    return f'aider --yes --message "{issue}" --no-git'


class AiderBaseline(ExternalCommandBaseline):
    """Aider CLI baseline with skip-when-missing."""

    def __init__(self) -> None:
        super().__init__(
            name="aider",
            command_builder=_build_aider_command,
            timeout_seconds=600,
            availability_check=_aider_available,
        )

    def run(self, request: BaselineRunRequest) -> BaselineRunResult:
        return super().run(request)
