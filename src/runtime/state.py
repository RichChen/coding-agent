"""Agent 状态机：记录循环阶段与简单失败信息。

English: loop phase enum + mutable AgentState holder.
"""

from __future__ import annotations

import enum


class LoopPhase(enum.Enum):
    INIT = "init"
    THINKING = "thinking"      # 等待 LLM 返回
    ACTING = "acting"          # 执行 tool_calls
    OBSERVING = "observing"    # 汇总工具结果、写 trace（语义上紧接下一轮 THINKING）
    DONE = "done"
    FAILED = "failed"


class AgentState:
    """循环内可变状态（当前实现里 phase 由 loop 驱动更新）。"""

    def __init__(self):
        self.phase = LoopPhase.INIT
        self.step_number = 0
        self.history: list[dict] = []
        self.failure_reason: str | None = None

    def transition(self, phase: LoopPhase) -> None:
        self.phase = phase

    def record_failure(self, reason: str) -> None:
        self.failure_reason = reason
        self.phase = LoopPhase.FAILED
