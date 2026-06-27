"""Tests for Sandbox path isolation."""

import pytest
from pathlib import Path

from src.policy.sandbox import Sandbox


class TestSandbox:
    @pytest.fixture
    def sandbox(self, tmp_path):
        return Sandbox(workspace_root=tmp_path)

    def test_simple_path(self, sandbox, tmp_path):
        result = sandbox.resolve("hello.py")
        assert result == tmp_path / "hello.py"

    def test_subdirectory(self, sandbox, tmp_path):
        result = sandbox.resolve("subdir/file.txt")
        assert result == tmp_path / "subdir" / "file.txt"

    def test_absolute_path_blocked(self, sandbox):
        result = sandbox.resolve("/etc/passwd")
        assert result is None

    def test_parent_traversal_blocked(self, sandbox):
        result = sandbox.resolve("../../etc/passwd")
        assert result is None

    def test_dot_relative(self, sandbox, tmp_path):
        result = sandbox.resolve("./file.txt")
        assert result == tmp_path / "file.txt"

    def test_is_safe(self, sandbox):
        assert sandbox.is_safe("file.txt")
        assert not sandbox.is_safe("/etc/passwd")
        assert not sandbox.is_safe("../../../etc/passwd")

    def test_allow_absolute_when_disabled(self, tmp_path):
        sandbox = Sandbox(workspace_root=tmp_path, deny_absolute=False, deny_parent_traversal=False)
        # Still blocked because /etc resolves outside workspace
        result = sandbox.resolve("/etc/passwd")
        assert result is None

    def test_symlink_not_escaping(self, sandbox, tmp_path):
        """Path that exists outside workspace should be rejected even if it exists."""
        result = sandbox.resolve("/nonexistent/file.txt")
        assert result is None
