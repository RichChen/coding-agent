"""Tests for file tools and search_replace."""

import pytest

from src.policy.sandbox import Sandbox
from src.tools.base import ToolContext
from src.tools.files import ListDirTool, ReadFileTool, WriteFileTool
from src.tools.patch import SearchReplaceTool
from src.tools.search import SearchCodeTool


class TestFileTools:
    @pytest.fixture
    def ctx(self, tmp_path):
        sandbox = Sandbox(workspace_root=tmp_path)
        return ToolContext(workspace_root=tmp_path, sandbox=sandbox)

    @pytest.mark.asyncio
    async def test_write_and_read(self, ctx):
        write_tool = WriteFileTool()
        result = await write_tool.execute(
            {"path": "test.txt", "content": "hello world", "_call_id": "c1"}, ctx
        )
        assert result.success
        assert "Wrote" in result.output

        read_tool = ReadFileTool()
        result = await read_tool.execute(
            {"path": "test.txt", "_call_id": "c2"}, ctx
        )
        assert result.success
        assert result.output == "1|hello world"

    @pytest.mark.asyncio
    async def test_read_nonexistent(self, ctx):
        tool = ReadFileTool()
        result = await tool.execute({"path": "nope.txt", "_call_id": "c1"}, ctx)
        assert not result.success
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_list_dir(self, ctx):
        write = WriteFileTool()
        await write.execute({"path": "a.txt", "content": "a", "_call_id": "c1"}, ctx)
        await write.execute({"path": "b.txt", "content": "b", "_call_id": "c2"}, ctx)
        (ctx.workspace_root / "sub").mkdir()

        tool = ListDirTool()
        result = await tool.execute({"path": ".", "_call_id": "c3"}, ctx)
        assert result.success
        assert "[F] a.txt" in result.output
        assert "[F] b.txt" in result.output
        assert "[D] sub" in result.output

    @pytest.mark.asyncio
    async def test_path_blocked_by_sandbox(self, ctx):
        tool = ReadFileTool()
        result = await tool.execute({"path": "/etc/passwd", "_call_id": "c1"}, ctx)
        assert not result.success
        assert "denied" in result.error.lower()

    @pytest.mark.asyncio
    async def test_write_create_parent_dirs(self, ctx):
        tool = WriteFileTool()
        result = await tool.execute(
            {"path": "deep/nested/file.txt", "content": "data", "_call_id": "c1"}, ctx
        )
        assert result.success
        assert (ctx.workspace_root / "deep" / "nested" / "file.txt").exists()


class TestSearchReplace:
    @pytest.fixture
    def ctx(self, tmp_path):
        sandbox = Sandbox(workspace_root=tmp_path)
        return ToolContext(workspace_root=tmp_path, sandbox=sandbox)

    @pytest.mark.asyncio
    async def test_simple_replace(self, ctx):
        write = WriteFileTool()
        await write.execute(
            {"path": "code.py", "content": "x = 1\ny = 2", "_call_id": "c1"}, ctx
        )

        tool = SearchReplaceTool()
        result = await tool.execute(
            {"path": "code.py", "search": "x = 1", "replace": "x = 42", "_call_id": "c2"},
            ctx,
        )
        assert result.success

        content = (ctx.workspace_root / "code.py").read_text()
        assert content == "x = 42\ny = 2"

    @pytest.mark.asyncio
    async def test_duplicate_search_blocked(self, ctx):
        write = WriteFileTool()
        await write.execute(
            {"path": "dup.py", "content": "x = 1\nx = 1", "_call_id": "c1"}, ctx
        )

        tool = SearchReplaceTool()
        result = await tool.execute(
            {"path": "dup.py", "search": "x = 1", "replace": "y = 2", "_call_id": "c2"},
            ctx,
        )
        assert not result.success
        assert "2 times" in result.error

    @pytest.mark.asyncio
    async def test_search_not_found(self, ctx):
        write = WriteFileTool()
        await write.execute(
            {"path": "f.py", "content": "hello", "_call_id": "c1"}, ctx
        )

        tool = SearchReplaceTool()
        result = await tool.execute(
            {"path": "f.py", "search": "nonexistent", "replace": "x", "_call_id": "c2"},
            ctx,
        )
        assert not result.success
        assert "not found" in result.error.lower()


class TestFileSizeLimit:
    @pytest.fixture
    def ctx(self, tmp_path):
        from src.policy.sandbox import Sandbox
        sandbox = Sandbox(workspace_root=tmp_path)
        return ToolContext(workspace_root=tmp_path, sandbox=sandbox, file_size_limit_bytes=100)

    @pytest.mark.asyncio
    async def test_read_exceeds_limit(self, ctx):
        # Write a file larger than 100 bytes
        big_content = "x" * 200
        (ctx.workspace_root / "big.txt").write_text(big_content)

        tool = ReadFileTool()
        result = await tool.execute({"path": "big.txt", "_call_id": "c1"}, ctx)
        assert not result.success
        assert "exceeds limit" in result.error.lower()

    @pytest.mark.asyncio
    async def test_read_within_limit(self, ctx):
        small_content = "x" * 50
        (ctx.workspace_root / "small.txt").write_text(small_content)

        tool = ReadFileTool()
        result = await tool.execute({"path": "small.txt", "_call_id": "c1"}, ctx)
        assert result.success
        assert result.output == "1|" + small_content

    @pytest.mark.asyncio
    async def test_write_exceeds_limit(self, ctx):
        tool = WriteFileTool()
        big_content = "x" * 200
        result = await tool.execute(
            {"path": "big.txt", "content": big_content, "_call_id": "c1"}, ctx
        )
        assert not result.success
        assert "exceeds limit" in result.error.lower()

    @pytest.mark.asyncio
    async def test_write_within_limit(self, ctx):
        tool = WriteFileTool()
        small_content = "x" * 50
        result = await tool.execute(
            {"path": "small.txt", "content": small_content, "_call_id": "c1"}, ctx
        )
        assert result.success

    @pytest.mark.asyncio
    async def test_no_limit_when_none(self, tmp_path):
        from src.policy.sandbox import Sandbox
        sandbox = Sandbox(workspace_root=tmp_path)
        ctx = ToolContext(workspace_root=tmp_path, sandbox=sandbox, file_size_limit_bytes=None)

        big_content = "x" * 200
        (tmp_path / "big.txt").write_text(big_content)

        tool = ReadFileTool()
        result = await tool.execute({"path": "big.txt", "_call_id": "c1"}, ctx)
        assert result.success


class TestOutputTruncation:
    @pytest.fixture
    def ctx(self, tmp_path):
        from src.policy.sandbox import Sandbox
        sandbox = Sandbox(workspace_root=tmp_path)
        return ToolContext(
            workspace_root=tmp_path,
            sandbox=sandbox,
            tool_output_max_chars=500,
            read_file_max_lines=10,
        )

    @pytest.mark.asyncio
    async def test_read_file_line_limit(self, ctx):
        content = "\n".join(f"line {i}" for i in range(30))
        (ctx.workspace_root / "many_lines.txt").write_text(content)

        tool = ReadFileTool()
        result = await tool.execute({"path": "many_lines.txt", "_call_id": "c1"}, ctx)
        assert result.success
        assert "[showing lines 1-10 of 30; call read_file with offset=11 to continue]" in result.output
        assert "1|line 0" in result.output
        assert "10|line 9" in result.output
        assert "line 10" not in result.output

    @pytest.mark.asyncio
    async def test_read_file_model_limit_takes_precedence(self, ctx):
        content = "\n".join(f"line {i}" for i in range(30))
        (ctx.workspace_root / "many_lines.txt").write_text(content)

        tool = ReadFileTool()
        # model requests 3 lines, which is stricter than server's 10
        result = await tool.execute(
            {"path": "many_lines.txt", "limit": 3, "_call_id": "c1"}, ctx
        )
        assert result.success
        assert "[showing lines 1-3 of 30; call read_file with offset=4 to continue]" in result.output
        assert "1|line 0" in result.output
        assert "3|line 2" in result.output
        assert "line 3" not in result.output

    @pytest.mark.asyncio
    async def test_read_file_char_truncation(self, ctx):
        # Create content > 500 chars
        content = "x" * 600
        (ctx.workspace_root / "big.txt").write_text(content)

        tool = ReadFileTool()
        result = await tool.execute({"path": "big.txt", "_call_id": "c1"}, ctx)
        assert result.success
        assert "call read_file with offset=" in result.output
        assert result.output.split("\n", 1)[0].startswith("1|")

    @pytest.mark.asyncio
    async def test_read_file_no_truncation_when_under_limit(self, ctx):
        content = "short file"
        (ctx.workspace_root / "short.txt").write_text(content)

        tool = ReadFileTool()
        result = await tool.execute({"path": "short.txt", "_call_id": "c1"}, ctx)
        assert result.success
        assert result.output == "1|short file"

    @pytest.mark.asyncio
    async def test_read_file_offset_continues(self, ctx):
        content = "\n".join(f"line {i}" for i in range(30))
        (ctx.workspace_root / "many_lines.txt").write_text(content)
        tool = ReadFileTool()
        result = await tool.execute(
            {"path": "many_lines.txt", "offset": 11, "limit": 2, "_call_id": "c1"}, ctx
        )
        assert result.success
        assert result.output.startswith("11|line 10\n12|line 11\n")
        assert "offset=13" in result.output

    @pytest.mark.asyncio
    async def test_command_output_truncation(self, ctx):
        from src.tools.command import RunCommandTool

        tool = RunCommandTool(timeout_seconds=10)
        # Generate 600 chars of output via echo
        padding = "x" * 600
        if ctx.sandbox:
            ctx.sandbox.deny_absolute = False  # allow echo which is in PATH
        result = await tool.execute(
            {"command": f"echo {padding}", "_call_id": "c1"}, ctx
        )
        # truncation applies regardless of success
        if result.success:
            assert "... (output truncated)" in result.output


class TestEditFile:
    @pytest.fixture
    def ctx(self, tmp_path):
        from src.policy.sandbox import Sandbox
        sandbox = Sandbox(workspace_root=tmp_path)
        return ToolContext(workspace_root=tmp_path, sandbox=sandbox)

    @pytest.mark.asyncio
    async def test_single_replace(self, ctx):
        from src.tools.edit import EditFileTool

        (ctx.workspace_root / "code.py").write_text("x = 1\ny = 2\nz = 3")

        tool = EditFileTool()
        result = await tool.execute(
            {"path": "code.py", "old_string": "x = 1", "new_string": "x = 42", "_call_id": "c1"},
            ctx,
        )
        assert result.success
        assert "Replaced 1 occurrence" in result.output
        assert (ctx.workspace_root / "code.py").read_text() == "x = 42\ny = 2\nz = 3"

    @pytest.mark.asyncio
    async def test_replaces_first_only(self, ctx):
        from src.tools.edit import EditFileTool

        (ctx.workspace_root / "dup.py").write_text("x = 1\nx = 1\nx = 1")

        tool = EditFileTool()
        result = await tool.execute(
            {"path": "dup.py", "old_string": "x = 1", "new_string": "y = 2", "_call_id": "c1"},
            ctx,
        )
        assert result.success
        # Only first occurrence replaced
        assert (ctx.workspace_root / "dup.py").read_text() == "y = 2\nx = 1\nx = 1"

    @pytest.mark.asyncio
    async def test_not_found(self, ctx):
        from src.tools.edit import EditFileTool

        (ctx.workspace_root / "f.py").write_text("hello")

        tool = EditFileTool()
        result = await tool.execute(
            {"path": "f.py", "old_string": "nonexistent", "new_string": "x", "_call_id": "c1"},
            ctx,
        )
        assert not result.success
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_path_blocked(self, ctx):
        from src.tools.edit import EditFileTool

        tool = EditFileTool()
        result = await tool.execute(
            {"path": "/etc/hosts", "old_string": "a", "new_string": "b", "_call_id": "c1"},
            ctx,
        )
        assert not result.success
        assert "denied" in result.error.lower()


class TestSearchCode:
    @pytest.fixture
    def ctx(self, tmp_path):
        sandbox = Sandbox(workspace_root=tmp_path)
        return ToolContext(workspace_root=tmp_path, sandbox=sandbox)

    @pytest.mark.asyncio
    async def test_search_returns_path_line_and_caps(self, ctx):
        (ctx.workspace_root / "a.py").write_text("keep\nneedle here\n")
        (ctx.workspace_root / "b.txt").write_text("needle\n")
        tool = SearchCodeTool()
        result = await tool.execute(
            {"pattern": "needle", "glob": "*.py", "max_results": 1, "_call_id": "c1"}, ctx
        )
        assert result.success, result.error
        assert result.output.splitlines()[0] == "a.py:2: needle here"
        assert "b.txt" not in result.output
