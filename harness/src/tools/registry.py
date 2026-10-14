"""ToolRegistry：注册工具并生成发给 LLM 的 tools schema 列表。"""

from __future__ import annotations

from src.tools.base import Tool


class ToolRegistry:
    """工具容器：按名称索引；`schemas()` 产出 OpenAI tools 数组。"""

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' already registered")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def names(self) -> list[str]:
        return list(self._tools.keys())

    def tools(self) -> list[Tool]:
        return list(self._tools.values())

    def schemas(self, enabled: list[str] | None = None) -> list[dict]:
        """返回各工具的 OpenAI schema；enabled 非空时按名称过滤。"""
        tools = self._tools.values()
        if enabled is not None:
            enabled_set = set(enabled)
            tools = [t for t in tools if t.name in enabled_set]
        return [t.to_schema() for t in tools]


# 便于演示的全局注册表（生产代码可改为显式依赖注入）
default_registry = ToolRegistry()
