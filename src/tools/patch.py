"""search_replace：在单文件内做精确子串替换（命中次数须为 1）。

English: exact single-match search/replace for small edits.
"""

from __future__ import annotations

from src.tools.base import Tool, ToolContext, ToolResult


class SearchReplaceTool(Tool):
    name = "search_replace"
    description = (
        "Search for a string in a file and replace it. "
        "The search string must match exactly once; use for small targeted edits."
    )
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Relative path to the file within the workspace.",
            },
            "search": {
                "type": "string",
                "description": "Exact string to search for (must be unique in file).",
            },
            "replace": {
                "type": "string",
                "description": "Replacement string.",
            },
        },
        "required": ["path", "search", "replace"],
    }

    async def execute(self, params: dict, ctx: ToolContext) -> ToolResult:
        raw_path = params.get("path", "")
        search = params.get("search", "")
        replace = params.get("replace", "")
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

        count = content.count(search)
        if count == 0:
            return ToolResult(
                call_id=call_id,
                name=self.name,
                success=False,
                output="",
                error=f"Search string not found in {raw_path}",
            )
        if count > 1:
            return ToolResult(
                call_id=call_id,
                name=self.name,
                success=False,
                output="",
                error=f"Search string found {count} times — must be unique. Use more context.",
            )

        new_content = content.replace(search, replace, 1)
        resolved.write_text(new_content, encoding="utf-8")

        return ToolResult(
            call_id=call_id,
            name=self.name,
            success=True,
            output=f"Replaced 1 occurrence in {raw_path}",
        )
