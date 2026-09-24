"""Repo profile memory for stable repo-specific hints."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


class RepoProfileMemory(BaseModel):
    """Persistent summary for one repository fingerprint."""

    repo_fingerprint: str
    test_commands: list[str] = Field(default_factory=list)
    top_level_entries: list[str] = Field(default_factory=list)
    common_files: list[str] = Field(default_factory=list)
    style_notes: list[str] = Field(default_factory=list)


class RepoProfileStore:
    """JSON-backed map of repo profiles."""

    def __init__(self, memory_dir: Path) -> None:
        self.memory_dir = memory_dir
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.memory_dir / "repo_profile.json"

    def upsert(self, profile: RepoProfileMemory) -> None:
        data = self._read()
        data[profile.repo_fingerprint] = profile.model_dump()
        self.path.write_text(self._dump_map(data), encoding="utf-8")

    def get(self, repo_fingerprint: str) -> RepoProfileMemory | None:
        data = self._read()
        raw = data.get(repo_fingerprint)
        if raw is None:
            return None
        return RepoProfileMemory.model_validate(raw)

    def _read(self) -> dict:
        if not self.path.exists():
            return {}
        text = self.path.read_text(encoding="utf-8").strip()
        if not text:
            return {}
        import json

        loaded = json.loads(text)
        if "repo_fingerprint" in loaded:
            return {loaded["repo_fingerprint"]: loaded}
        return loaded

    @staticmethod
    def _dump_map(data: dict) -> str:
        import json

        return json.dumps(data, ensure_ascii=False, indent=2)
