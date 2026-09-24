"""Drop noise that only existed in the old offline transport image.

Kept out of the model-facing card, and tagged legacy_env_artifact:
- pip install / pip download, and missing third-party modules the image lacked
  (six, pluggy, attr, py, more_itertools, numpy, mpmath, packaging, pytz, sqlparse)
- git not found, network failures, and `find /` whole-filesystem searches
- handwritten stub trees under /tmp/stubs

Repository facts stay: test layout, runtests.py, and modules that must change together.
"""

from __future__ import annotations

import re

_LEGACY = re.compile(
    r"(?i)(?:"
    r"\bpip3?\s+(?:install|download|show)\b"
    r"|no module named ['\"]?(?:six|pluggy|attr|py|more_itertools|numpy|mpmath|packaging|pytz|sqlparse)\b"
    r"|git:\s*not found"
    r"|\bfind\s+/"
    r"|/tmp/stubs"
    r"|network is unreachable"
    r"|temporary failure in name resolution"
    r"|could not fetch url"
    r"|no matching distribution"
    r"|connection refused"
    r")"
)


def is_legacy_env_artifact(text: str) -> bool:
    return bool(_LEGACY.search(text))


def split_legacy(items: tuple[str, ...]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    kept, legacy = [], []
    for item in items:
        if is_legacy_env_artifact(item):
            legacy.append(item)
        else:
            kept.append(item)
    return tuple(kept), tuple(legacy)
