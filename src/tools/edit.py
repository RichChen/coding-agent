"""edit_file 工具：单次文本替换（不要求唯一匹配）。

English: single-occurrence replace — replaces the first match of old_string
with new_string. Unlike search_replace, it does NOT require exactly one match.
"""

from __future__ import annotations

from src.tools.base import Tool, ToolContext, ToolResult


class EditFileTool(Tool):
    name = "edit_file"
    description = (
        "Replace the first occurrence of old_string with new_string in a file. "
        "Does NOT require the match to be unique."
    )
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Relative path to the file within the workspace.",
            },
            "old_string": {
                "type": "string",
                "description": "The exact text to replace (first occurrence only).",
            },
            "new_string": {
                "type": "string",
                "description": "The text to insert in place of old_string.",
            },
        },
        "required": ["path", "old_string", "new_string"],
    }

    async def execute(self, params: dict, ctx: ToolContext) -> ToolResult:
        raw_path = params.get("path", "")
        old_str = params.get("old_string", "")
        new_str = params.get("new_string", "")
        call_id = params.get("_call_id", "")

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

        if old_str not in content:
            return ToolResult(
                call_id=call_id,
                name=self.name,
                success=False,
                output="",
                error=f"old_string not found in {raw_path}",
            )

        new_content = content.replace(old_str, new_str, 1)

        try:
            resolved.write_text(new_content, encoding="utf-8")
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
            output=f"Replaced 1 occurrence in {raw_path}",
        )
