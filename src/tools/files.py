"""文件类工具：read_file / write_file / list_dir。

English: file tools — all paths go through Sandbox.resolve under workspace_root.
"""

from __future__ import annotations

from pathlib import Path

from src.policy.limits import check_content_size, check_file_size
from src.tools.base import Tool, ToolContext, ToolResult


class ReadFileTool(Tool):
    name = "read_file"
    description = "Read the contents of a file in the workspace."
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Relative path to the file within the workspace.",
            },
            "limit": {
                "type": "integer",
                "description": "Optional max number of lines to return. Default: all lines.",
            },
        },
        "required": ["path"],
    }

    async def execute(self, params: dict, ctx: ToolContext) -> ToolResult:
        raw_path = params.get("path", "")
        model_limit = params.get("limit")  # model-requested line limit
        sandbox = ctx.sandbox
        resolved = sandbox.resolve(raw_path) if sandbox else ctx.workspace_root / raw_path

        if resolved is None:
            return ToolResult(
                call_id=params.get("_call_id", ""),
                name=self.name,
                success=False,
                output="",
                error=f"Path denied by sandbox: {raw_path}",
            )

        # 文件大小限制检查
        size_limit = ctx.file_size_limit_bytes
        if size_limit is not None:
            err = check_file_size(resolved, size_limit)
            if err:
                return ToolResult(
                    call_id=params.get("_call_id", ""),
                    name=self.name,
                    success=False,
                    output="",
                    error=err,
                )

        try:
            content = resolved.read_text(encoding="utf-8")
        except FileNotFoundError:
            return ToolResult(
                call_id=params.get("_call_id", ""),
                name=self.name,
                success=False,
                output="",
                error=f"File not found: {raw_path}",
            )
        except Exception as e:
            return ToolResult(
                call_id=params.get("_call_id", ""),
                name=self.name,
                success=False,
                output="",
                error=str(e),
            )

        # 行数截断：取 model_limit 与 read_file_max_lines 中的较小值
        effective_limit: int | None = None
        if model_limit is not None and isinstance(model_limit, int):
            effective_limit = model_limit
        if ctx.read_file_max_lines is not None:
            if effective_limit is None or ctx.read_file_max_lines < effective_limit:
                effective_limit = ctx.read_file_max_lines

        if effective_limit is not None:
            lines = content.split("\n")
            if len(lines) > effective_limit:
                truncated = "\n".join(lines[:effective_limit])
                content = f"{truncated}\n... ({len(lines) - effective_limit} more lines)"

        # 字符数截断（最后防线）
        if ctx.tool_output_max_chars is not None and len(content) > ctx.tool_output_max_chars:
            content = content[:ctx.tool_output_max_chars] + "\n... (output truncated)"

        return ToolResult(
            call_id=params.get("_call_id", ""),
            name=self.name,
            success=True,
            output=content,
        )


class WriteFileTool(Tool):
    name = "write_file"
    description = "Write content to a file in the workspace. Creates parent directories if needed."
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Relative path to the file within the workspace.",
            },
            "content": {
                "type": "string",
                "description": "Content to write to the file.",
            },
        },
        "required": ["path", "content"],
    }

    async def execute(self, params: dict, ctx: ToolContext) -> ToolResult:
        raw_path = params.get("path", "")
        content = params.get("content", "")
        sandbox = ctx.sandbox
        resolved = sandbox.resolve(raw_path) if sandbox else ctx.workspace_root / raw_path

        if resolved is None:
            return ToolResult(
                call_id=params.get("_call_id", ""),
                name=self.name,
                success=False,
                output="",
                error=f"Path denied by sandbox: {raw_path}",
            )

        # 内容大小限制检查
        limit = ctx.file_size_limit_bytes
        if limit is not None:
            err = check_content_size(content, limit)
            if err:
                return ToolResult(
                    call_id=params.get("_call_id", ""),
                    name=self.name,
                    success=False,
                    output="",
                    error=err,
                )

        try:
            resolved.parent.mkdir(parents=True, exist_ok=True)
            resolved.write_text(content, encoding="utf-8")
        except Exception as e:
            return ToolResult(
                call_id=params.get("_call_id", ""),
                name=self.name,
                success=False,
                output="",
                error=str(e),
            )

        return ToolResult(
            call_id=params.get("_call_id", ""),
            name=self.name,
            success=True,
            output=f"Wrote {len(content)} bytes to {raw_path}",
        )


class ListDirTool(Tool):
    name = "list_dir"
    description = "List files and directories in the workspace."
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Relative path to a directory within the workspace. Use '.' for root.",
            },
        },
        "required": ["path"],
    }

    async def execute(self, params: dict, ctx: ToolContext) -> ToolResult:
        raw_path = params.get("path", ".")
        sandbox = ctx.sandbox
        resolved = sandbox.resolve(raw_path) if sandbox else ctx.workspace_root / raw_path

        if resolved is None:
            return ToolResult(
                call_id=params.get("_call_id", ""),
                name=self.name,
                success=False,
                output="",
                error=f"Path denied by sandbox: {raw_path}",
            )

        if not resolved.is_dir():
            return ToolResult(
                call_id=params.get("_call_id", ""),
                name=self.name,
                success=False,
                output="",
                error=f"Not a directory: {raw_path}",
            )

        try:
            items = []
            for p in sorted(resolved.iterdir()):
                prefix = "[D]" if p.is_dir() else "[F]"
                items.append(f"{prefix} {p.name}")
            output = "\n".join(items) if items else "(empty directory)"
        except Exception as e:
            return ToolResult(
                call_id=params.get("_call_id", ""),
                name=self.name,
                success=False,
                output="",
                error=str(e),
            )

        return ToolResult(
            call_id=params.get("_call_id", ""),
            name=self.name,
            success=True,
            output=output,
        )
