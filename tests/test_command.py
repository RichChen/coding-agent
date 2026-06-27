import asyncio
import os

import pytest

from src.policy.rules import CommandPolicy
from src.tools.base import ToolContext
from src.tools.command import RunCommandTool


@pytest.fixture
def workspace(tmp_path):
    return tmp_path


class TestCommandPolicyArgv:
    def test_check_argv_allows_whitelisted_program(self):
        policy = CommandPolicy(allow_all=False, allowed_prefixes=["python"])
        assert policy.check_argv(["python", "-c", "print(1)"]).allowed

    def test_check_argv_blocks_unknown_program(self):
        policy = CommandPolicy(allow_all=False, allowed_prefixes=["python"])
        decision = policy.check_argv(["curl", "https://example.com"])
        assert not decision.allowed

    def test_check_argv_blocks_dangerous_joined_pattern(self):
        policy = CommandPolicy(
            allow_all=True,
            blocked_patterns=["rm -rf /"],
        )
        assert not policy.check_argv(["sh", "-c", "rm -rf /"]).allowed

    def test_check_argv_rejects_empty(self):
        policy = CommandPolicy()
        assert not policy.check_argv([]).allowed


class TestRunCommandToolArgv:
    def test_argv_execution_success(self, workspace):
        tool = RunCommandTool(
            command_policy=CommandPolicy(allow_all=False, allowed_prefixes=["python"]),
        )
        result = asyncio.run(
            tool.execute(
                {"argv": ["python", "-c", "print('argv_ok')"]},
                ToolContext(workspace_root=workspace),
            )
        )
        assert result.success is True
        assert "argv_ok" in result.output
        assert "exit_code=0" in result.output

    def test_argv_blocked_by_policy(self, workspace):
        tool = RunCommandTool(
            command_policy=CommandPolicy(allow_all=False, allowed_prefixes=["python"]),
        )
        result = asyncio.run(
            tool.execute(
                {"argv": ["curl", "https://example.com"]},
                ToolContext(workspace_root=workspace),
            )
        )
        assert result.success is False
        assert "blocked by policy" in (result.error or "")

    def test_env_whitelist_hides_secret_variable(self, workspace, monkeypatch):
        monkeypatch.setenv("HARNESS_SECRET_TOKEN", "super-secret")
        tool = RunCommandTool(
            command_policy=CommandPolicy(allow_all=True),
            env_whitelist=["PATH"],
        )
        script = (
            "import os\n"
            "print(os.environ.get('HARNESS_SECRET_TOKEN', 'MISSING'))"
        )
        result = asyncio.run(
            tool.execute(
                {"argv": ["python", "-c", script]},
                ToolContext(workspace_root=workspace),
            )
        )
        assert result.success is True
        assert "MISSING" in result.output

    def test_shell_path_still_works(self, workspace):
        tool = RunCommandTool(command_policy=CommandPolicy(allow_all=True))
        result = asyncio.run(
            tool.execute(
                {"command": "python -c \"print('shell_ok')\""},
                ToolContext(workspace_root=workspace),
            )
        )
        assert result.success is True
        assert "shell_ok" in result.output
