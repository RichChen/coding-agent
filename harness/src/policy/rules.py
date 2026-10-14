"""Shell 命令策略：黑名单 +（宽松模式或前缀白名单）。

English: command policy — blocklist first, then allow_all or prefix whitelist.

两种模式：
  - allow_all=True：基线模式，除危险模式外放行。
  - allow_all=False：仅允许以 allowed_prefixes 中前缀开头的命令。
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass


@dataclass
class PolicyDecision:
    allowed: bool
    reason: str


class CommandPolicy:
    def __init__(
        self,
        allow_all: bool = True,
        allowed_prefixes: list[str] | None = None,
        blocked_patterns: list[str] | None = None,
    ):
        self.allow_all = allow_all
        self.allowed_prefixes = allowed_prefixes or []
        self.blocked_patterns = blocked_patterns or []
        self._compiled_blocked = [re.compile(p, re.IGNORECASE) for p in self.blocked_patterns]

    def check(self, command: str) -> PolicyDecision:
        """判断是否允许执行该命令。

        判定顺序：黑名单 → allow_all / 白名单前缀。
        """
        cmd_stripped = command.strip()

        if not cmd_stripped:
            return PolicyDecision(allowed=False, reason="Empty command.")

        # 黑名单优先（两种模式都生效）
        for pat in self._compiled_blocked:
            if pat.search(cmd_stripped):
                return PolicyDecision(
                    allowed=False,
                    reason=f"Command matches blocked pattern: '{pat.pattern}'",
                )

        if self.allow_all:
            return PolicyDecision(allowed=True, reason="allow_all mode")

        # 白名单：整行 strip 后以某前缀开头，或首个 token 等于某前缀（兼容 "python script.py"）
        for prefix in self.allowed_prefixes:
            if cmd_stripped.startswith(prefix) or cmd_stripped.split(None, 1)[0] == prefix:
                return PolicyDecision(allowed=True, reason=f"Matches allowed prefix: '{prefix}'")

        return PolicyDecision(
            allowed=False,
            reason=f"Command '{cmd_stripped[:60]}' does not match any allowed prefix. "
                   f"Allowed: {self.allowed_prefixes[:10]}",
        )

    def check_argv(self, argv: list[str]) -> PolicyDecision:
        """Argv-mode policy: blocklist on joined argv, whitelist matches argv[0] basename only."""
        if not argv:
            return PolicyDecision(allowed=False, reason="Empty argv.")

        joined = " ".join(argv)
        for pat in self._compiled_blocked:
            if pat.search(joined):
                return PolicyDecision(
                    allowed=False,
                    reason=f"Command matches blocked pattern: '{pat.pattern}'",
                )

        if self.allow_all:
            return PolicyDecision(allowed=True, reason="allow_all mode")

        program = argv[0]
        basename = os.path.basename(program.replace("\\", "/"))
        for prefix in self.allowed_prefixes:
            if program == prefix or basename == prefix:
                return PolicyDecision(allowed=True, reason=f"Matches allowed prefix: '{prefix}'")

        return PolicyDecision(
            allowed=False,
            reason=f"Program '{basename}' does not match any allowed prefix. "
                   f"Allowed: {self.allowed_prefixes[:10]}",
        )
