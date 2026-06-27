"""Workspace 沙箱：不依赖 Docker 的路径级隔离。

English: path-based isolation — no absolute paths (optional), no `..` escape,
resolved paths must stay under workspace_root.

约束要点：
  - 可配置禁止绝对路径
  - 禁止父目录穿越（..）
  - 解析后的路径必须落在 workspace_root 之下
  - 通过 resolve 解析符号链接，降低「越狱」路径风险

工具执行安全性的基础层。
"""

from __future__ import annotations

from pathlib import Path


class Sandbox:
    """在 workspace 根目录内解析并校验相对路径。"""

    def __init__(
        self,
        workspace_root: Path,
        deny_absolute: bool = True,
        deny_parent_traversal: bool = True,
    ):
        self.workspace_root = workspace_root.resolve()
        self.deny_absolute = deny_absolute
        self.deny_parent_traversal = deny_parent_traversal

    def resolve(self, raw_path: str) -> Path | None:
        """将用户给出的相对路径解析为绝对路径。

        安全则返回 Path；若越权或非法则返回 None。
        """
        # 禁止绝对路径（由配置 deny_absolute 控制）
        if self.deny_absolute and Path(raw_path).is_absolute():
            return None

        # 禁止路径分量中出现 .. 穿越
        if self.deny_parent_traversal and ".." in Path(raw_path).parts:
            return None

        # resolve 后必须仍位于 workspace_root 之下（relative_to 校验）
        try:
            candidate = (self.workspace_root / raw_path).resolve()
        except (OSError, ValueError):
            return None

        # 确保解析结果包含于 workspace（越界则 ValueError）
        try:
            candidate.relative_to(self.workspace_root)
        except ValueError:
            return None

        return candidate

    def is_safe(self, path: str | Path) -> bool:
        return self.resolve(str(path)) is not None
