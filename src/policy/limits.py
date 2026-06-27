"""文件大小限制检查。

English: file size limit enforcement — reject reads/writes above the configured byte cap.
"""

from __future__ import annotations

from pathlib import Path


def check_file_size(path: Path, limit: int) -> str | None:
    """Check if a file exceeds the size limit. Returns error message or None."""
    try:
        size = path.stat().st_size
    except FileNotFoundError:
        return None  # let the caller handle missing files
    except OSError as e:
        return f"Cannot stat file: {e}"

    if size > limit:
        return (
            f"File size ({size} bytes) exceeds limit ({limit} bytes). "
            f"Use a smaller file or increase file_size_limit_bytes."
        )
    return None


def check_content_size(content: str, limit: int) -> str | None:
    """Check if content byte length exceeds the limit. Returns error message or None."""
    size = len(content.encode("utf-8"))
    if size > limit:
        return (
            f"Content size ({size} bytes) exceeds limit ({limit} bytes). "
            f"Reduce content size or increase file_size_limit_bytes."
        )
    return None
