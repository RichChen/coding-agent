"""工具子系统：抽象基类、注册表、执行上下文。

English: Tool ABC, ToolRegistry, ToolContext — every tool goes policy → execute → observation.

智能体调用的每个工具都经过：
  1. 策略检查（是否允许）
  2. 在 workspace 上下文中执行
  3. 将 ToolResult 转写为 OpenAI 的 tool 消息写回对话
"""

from __future__ import annotations

import enum
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class ToolStatus(str, enum.Enum):
    """Execution outcome aligned with shared contract semantics."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"
    BLOCKED = "blocked"
    OUTCOME_UNKNOWN = "outcome_unknown"


class SideEffectClass(str, enum.Enum):
    """Declared side-effect class for retry / recovery policy."""

    READ_ONLY = "read_only"
    IDEMPOTENT_WRITE = "idempotent_write"
    NON_IDEMPOTENT = "non_idempotent"


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
    call_id: str = ""  # host-assigned tool_call id; not part of model arguments
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolResult:
    call_id: str
    name: str
    success: bool
    output: str
    error: str | None = None
    status: ToolStatus | None = None
    error_kind: str | None = None
    # Structured execution metadata (commands); host-only, mirrored into observation.
    exit_code: int | None = None
    cleanup_state: str | None = None
    cleanup_elapsed_s: float | None = None
    truncated: bool | None = None
    bytes_seen: int | None = None
    bytes_kept: int | None = None

    def __post_init__(self) -> None:
        if self.status is None:
            self.status = ToolStatus.SUCCEEDED if self.success else ToolStatus.FAILED
        else:
            # Keep legacy success flag aligned with status for callers that only check bool.
            if self.status == ToolStatus.SUCCEEDED:
                self.success = True
            elif self.success and self.status != ToolStatus.SUCCEEDED:
                self.success = False

    def to_message(self) -> dict[str, Any]:
        """转为 OpenAI 兼容的 tool 角色消息（tool_call_id + content）。

        Failed/timeout/cancelled still include safe partial stdout/stderr so the
        model can observe truncated output; never drop useful observation text.
        When truncating for model context, exit/truncation markers stay in content.
        """
        if self.status == ToolStatus.SUCCEEDED and self.success:
            content = self.output
        else:
            parts: list[str] = []
            if self.output:
                parts.append(self.output)
            if self.error:
                parts.append(f"Error: {self.error}")
            elif self.status is not None:
                parts.append(f"Error: status={self.status.value}")
            content = "\n".join(parts) if parts else "Error: unknown"
        return {
            "role": "tool",
            "tool_call_id": self.call_id,
            "content": content,
        }


class Tool(ABC):
    """所有工具的抽象基类（name / description / parameters 供 LLM 使用）。"""

    name: str = ""
    description: str = ""
    parameters: dict[str, Any] = {}
    # Undeclared write tools are treated conservatively as non-idempotent.
    side_effect: SideEffectClass = SideEffectClass.NON_IDEMPOTENT

    @abstractmethod
    async def execute(self, params: dict[str, Any], ctx: ToolContext) -> ToolResult:
        """执行工具。

        Args:
            params: 已通过 schema 校验的模型参数（不含宿主 `_call_id`）。
            ctx: 含 workspace_root、sandbox 与 host call_id。

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

    def resolve_call_id(self, params: dict[str, Any], ctx: ToolContext) -> str:
        """Prefer host ToolContext.call_id; legacy params `_call_id` is fallback only."""
        if ctx.call_id:
            return ctx.call_id
        legacy = params.get("_call_id")
        return legacy if isinstance(legacy, str) else ""
