"""工具子系统：抽象基类、注册表、执行上下文。

English: Tool ABC, ToolRegistry, ToolContext — every tool goes policy → execute → observation.

智能体调用的每个工具都经过：
  1. 策略检查（是否允许）
  2. 在 workspace 上下文中执行
  3. 将 ToolResult 转写为 OpenAI 的 tool 消息写回对话
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ToolContext:
    """每次工具调用携带的上下文。

    workspace_root 即「逻辑 chroot」边界：工具不得访问该目录之外的路径
    （具体由 Sandbox.resolve 执行）。
    """

    workspace_root: Path
    sandbox: Any = None  # Sandbox instance for path resolution
    file_size_limit_bytes: int | None = None  # max bytes for read/write; None = unlimited
    tool_output_max_chars: int | None = None  # max chars for tool output; None = unlimited
    read_file_max_lines: int | None = None  # max lines for read_file; None = unlimited
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolResult:
    call_id: str
    name: str
    success: bool
    output: str
    error: str | None = None

    def to_message(self) -> dict[str, Any]:
        """转为 OpenAI 兼容的 tool 角色消息（tool_call_id + content）。"""
        return {
            "role": "tool",
            "tool_call_id": self.call_id,
            "content": self.output if self.success else f"Error: {self.error}",
        }


class Tool(ABC):
    """所有工具的抽象基类（name / description / parameters 供 LLM 使用）。"""

    name: str = ""
    description: str = ""
    parameters: dict[str, Any] = {}

    @abstractmethod
    async def execute(self, params: dict[str, Any], ctx: ToolContext) -> ToolResult:
        """执行工具。

        Args:
            params: 模型给出的参数字典（可能含内部注入的 `_call_id`）。
            ctx: 含 workspace_root 与 sandbox。

        Returns:
            ToolResult：成功则 output 为模型可见文本，失败则 error 非空。
        """

    def to_schema(self) -> dict[str, Any]:
        """生成 OpenAI tools 数组中的单条 function schema。"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
