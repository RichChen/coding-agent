"""文件类工具：read_file / write_file / list_dir。

English: file tools — all paths go through Sandbox.resolve under workspace_root.
"""

from __future__ import annotations

from src.policy.limits import check_content_size, check_file_size
from src.tools.base import SideEffectClass, Tool, ToolContext, ToolResult


def format_file_view(text: str, *, offset: int | None, limit: int | None, max_chars: int | None) -> str:
    """Numbered slice of a file. Truncation keeps whole lines and tells the model how to continue."""
    lines = text.split("\n")
    total = len(lines)
    start = 1 if not isinstance(offset, int) or offset < 1 else offset
    if start > total:
        return f"[showing lines {start}-{max(start - 1, 0)} of {total}; call read_file with offset=1 to continue]"
    end = total if not isinstance(limit, int) or limit < 1 else min(total, start - 1 + limit)
    numbered = [f"{start + i}|{line}" for i, line in enumerate(lines[start - 1:end])]
    cut_for_chars = False
    if max_chars is not None:
        kept: list[str] = []
        used = 0
        for line in numbered:
            extra = len(line) + (1 if kept else 0)
            if kept and used + extra > max_chars:
                cut_for_chars = True
                break
            if not kept and len(line) > max_chars:
                kept.append(line[:max_chars])
                cut_for_chars = True
                break
            kept.append(line)
            used += extra
        if len(kept) < len(numbered):
            end = start + len(kept) - 1 if kept else start - 1
            numbered = kept
    body = "\n".join(numbered)
    if end < total or cut_for_chars:
        hint = f"[showing lines {start}-{end} of {total}; call read_file with offset={end + 1} to continue]"
        body = f"{body}\n{hint}" if body else hint
    return body


class ReadFileTool(Tool):
    name = "read_file"
    description = "Read a file in the workspace. Lines are numbered. Use offset to continue a truncated read."
    side_effect = SideEffectClass.READ_ONLY
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Relative path to the file within the workspace.",
            },
            "offset": {
                "type": "integer",
                "description": "First line to return, starting at 1.",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of lines to return.",
            },
        },
        "required": ["path"],
        "additionalProperties": False,
    }

    async def execute(self, params: dict, ctx: ToolContext) -> ToolResult:
        call_id = self.resolve_call_id(params, ctx)
        raw_path = params.get("path", "")
        model_limit = params.get("limit")
        offset = params.get("offset")
        sandbox = ctx.sandbox
        resolved = sandbox.resolve(raw_path) if sandbox else ctx.workspace_root / raw_path

        if resolved is None:
            return ToolResult(
                call_id=call_id,
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
                    call_id=call_id,
                    name=self.name,
                    success=False,
                    output="",
                    error=err,
                )

        try:
            content = resolved.read_text(encoding="utf-8")
        except FileNotFoundError:
            return ToolResult(
                call_id=call_id,
                name=self.name,
                success=False,
                output="",
                error=f"File not found: {raw_path}",
            )
        except Exception as e:
            return ToolResult(
                call_id=call_id,
                name=self.name,
                success=False,
                output="",
                error=str(e),
            )

        effective_limit: int | None = None
        if isinstance(model_limit, int):
            effective_limit = model_limit
        if ctx.read_file_max_lines is not None:
            if effective_limit is None or ctx.read_file_max_lines < effective_limit:
                effective_limit = ctx.read_file_max_lines
        content = format_file_view(
            content,
            offset=offset if isinstance(offset, int) else None,
            limit=effective_limit,
            max_chars=ctx.tool_output_max_chars,
        )

        return ToolResult(
            call_id=call_id,
            name=self.name,
            success=True,
            output=content,
        )


class WriteFileTool(Tool):
    name = "write_file"
    description = "Write content to a file in the workspace. Creates parent directories if needed."
    side_effect = SideEffectClass.IDEMPOTENT_WRITE
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
        "additionalProperties": False,
    }

    async def execute(self, params: dict, ctx: ToolContext) -> ToolResult:
        call_id = self.resolve_call_id(params, ctx)
        raw_path = params.get("path", "")
        content = params.get("content", "")
        sandbox = ctx.sandbox
        resolved = sandbox.resolve(raw_path) if sandbox else ctx.workspace_root / raw_path

        if resolved is None:
            return ToolResult(
                call_id=call_id,
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
                    call_id=call_id,
                    name=self.name,
                    success=False,
                    output="",
                    error=err,
                )

        try:
            resolved.parent.mkdir(parents=True, exist_ok=True)
            from src.tracing.artifacts import atomic_replace
            from src.runtime.recovery import file_hash
            proof = ctx.extra.get("replacement_proof")
            if proof and file_hash(resolved) != proof["before"]:
                raise ValueError("file changed after intent; refusing replacement")
            atomic_replace(resolved, content.encode("utf-8"))
        except Exception as e:
            return ToolResult(
                call_id=call_id,
                name=self.name,
                success=False,
                output="",
                error=str(e),
            )

        return ToolResult(
            call_id=call_id,
            name=self.name,
            success=True,
            output=f"Wrote {len(content)} bytes to {raw_path}",
        )


class ListDirTool(Tool):
    name = "list_dir"
    description = "List files and directories in the workspace."
    side_effect = SideEffectClass.READ_ONLY
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Relative path to a directory within the workspace. Use '.' for root.",
            },
        },
        "required": ["path"],
        "additionalProperties": False,
    }

    async def execute(self, params: dict, ctx: ToolContext) -> ToolResult:
        call_id = self.resolve_call_id(params, ctx)
        raw_path = params.get("path", ".")
        sandbox = ctx.sandbox
        resolved = sandbox.resolve(raw_path) if sandbox else ctx.workspace_root / raw_path

        if resolved is None:
            return ToolResult(
                call_id=call_id,
                name=self.name,
                success=False,
                output="",
                error=f"Path denied by sandbox: {raw_path}",
            )

        if not resolved.is_dir():
            return ToolResult(
                call_id=call_id,
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
                call_id=call_id,
                name=self.name,
                success=False,
                output="",
                error=str(e),
            )

        return ToolResult(
            call_id=call_id,
            name=self.name,
            success=True,
            output=output,
        )
