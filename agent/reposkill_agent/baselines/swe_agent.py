"""Optional SWE-agent external baseline — skip when CLI unavailable."""

from __future__ import annotations

import shutil

from reposkill_agent.baselines.contracts import BaselineRunRequest, BaselineRunResult
from reposkill_agent.baselines.external_command import ExternalCommandBaseline


def _swe_agent_available() -> tuple[bool, str]:
    if shutil.which("sweagent") is None:
        return False, "sweagent CLI not found on PATH; install SWE-agent separately (not vendored)"
    return True, ""


def _build_swe_agent_command(workspace, request: BaselineRunRequest) -> str:
    issue = request.issue.replace('"', "'")
    return (
        f'sweagent --repo "{workspace}" --issue "{issue}" '
        f"--output_dir {workspace / '.sweagent_out'}"
    )


class SweAgentBaseline(ExternalCommandBaseline):
    """SWE-agent CLI baseline with skip-when-missing."""

    def __init__(self) -> None:
        super().__init__(
            name="swe_agent",
            command_builder=_build_swe_agent_command,
            timeout_seconds=600,
            availability_check=_swe_agent_available,
        )

    def run(self, request: BaselineRunRequest) -> BaselineRunResult:
        return super().run(request)
