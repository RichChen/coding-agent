"""Predefined patches for tiny benchmark tasks (used by fake adapter baseline)."""

from __future__ import annotations

from reposkill_agent.core.contracts import PatchSpec

SCRIPTED_FIXES: dict[str, list[PatchSpec]] = {
    "fix_import_error": [
        PatchSpec(
            path="app/calculator.py",
            content=(
                '"""Simple calculator module."""\n\n\n'
                "def add(a: int, b: int) -> int:\n"
                "    return a + b\n\n\n"
                "def subtract(a: int, b: int) -> int:\n"
                "    return a - b\n"
            ),
        ),
    ],
    "fix_off_by_one": [
        PatchSpec(
            path="app/range_sum.py",
            content=(
                '"""Sum integers in a range (inclusive)."""\n\n\n'
                "def range_sum(start: int, end: int) -> int:\n"
                "    if start > end:\n"
                "        return 0\n"
                "    return sum(range(start, end + 1))\n"
            ),
        ),
    ],
    "add_greeting_function": [
        PatchSpec(
            path="app/greet.py",
            content=(
                '"""Greeting utilities."""\n\n\n'
                "def greet(name: str) -> str:\n"
                '    """Return a greeting for the given name."""\n'
                '    return f"Hello, {name}!"\n'
            ),
        ),
    ],
}
