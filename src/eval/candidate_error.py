"""Missing grader ids caused by the candidate's own edit (e.g. an IndentationError it introduced).

Rule: take the grader receipt's runner_error and the tail of each collection-error traceback. If the innermost
frame that belongs to the project is in a file the candidate changed, the run is an ordinary
failure. Anything else stays a stop condition.
"""
from __future__ import annotations

import re

REPO_ROOT = "/workspace/"
FRAME = re.compile(r'File "([^"]+)", line \d+|^(?:E\s+)?([^\s"\']+\.py):\d+: in ', re.MULTILINE)


def project_path(path: str) -> str | None:
    """Repo-relative path, or None for stdlib, site-packages, runner scripts and frozen modules."""
    if path.startswith(REPO_ROOT):
        return path[len(REPO_ROOT):]
    if path.startswith(("/", "<")) or re.match(r"^[A-Za-z]:[\\/]", path):
        return None
    return path[2:] if path.startswith("./") else path


def innermost_project_frame(text: str) -> str | None:
    frames = [project_path(match.group(1) or match.group(2)) for match in FRAME.finditer(text or "")]
    frames = [frame for frame in frames if frame]
    return frames[-1] if frames else None


def tracebacks(evaluation: dict) -> list[tuple[str, str]]:
    sources = []
    if evaluation.get("runner_error"):
        sources.append(("runner_error", str(evaluation["runner_error"])))
    for index, item in enumerate(evaluation.get("collection_error_tails") or []):
        sources.append(("collection_errors[" + str(index) + "]", str(item)))
    return sources


def grader_candidate_error(evaluation: dict, changed: list[str]) -> dict | None:
    """Where the candidate broke the test run, or None. An empty candidate never qualifies."""
    changed_set = set(changed or [])
    if not changed_set:
        return None
    for source, text in tracebacks(evaluation):
        frame = innermost_project_frame(text)
        if frame in changed_set:
            return {"source": source, "file": frame}
    return None
