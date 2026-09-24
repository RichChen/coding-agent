"""Load and serve local skill specifications."""

from __future__ import annotations

from pathlib import Path

import yaml

from reposkill_agent.skills.models import SkillSpec


class SkillRegistry:
    """Registry backed by markdown files with YAML frontmatter."""

    def __init__(self, library_dir: Path) -> None:
        self.library_dir = library_dir
        self._skills: list[SkillSpec] = []

    def load(self) -> list[SkillSpec]:
        """Load all skill specs from the library directory."""
        self._skills = []
        if not self.library_dir.exists():
            return self._skills
        for path in sorted(self.library_dir.glob("*.md")):
            self._skills.append(self._load_one(path))
        return self._skills

    def all(self) -> list[SkillSpec]:
        """Return loaded skills."""
        if not self._skills:
            return self.load()
        return self._skills

    @staticmethod
    def _load_one(path: Path) -> SkillSpec:
        text = path.read_text(encoding="utf-8")
        parts = text.split("---", 2)
        if len(parts) < 3:
            raise ValueError(f"skill file missing frontmatter: {path}")
        meta = yaml.safe_load(parts[1]) or {}
        procedure = parts[2].strip()
        edit_recipe = meta.get("edit_recipe")
        if not edit_recipe and procedure:
            edit_recipe = [
                line.strip().lstrip("0123456789.").strip()
                for line in procedure.splitlines()
                if line.strip()
            ]
        return SkillSpec(
            id=meta["id"],
            name=meta["name"],
            version=meta.get("version", "0.1.0"),
            purpose=meta.get("purpose", ""),
            pattern=meta.get("pattern", meta.get("purpose", "")),
            required_evidence=meta.get(
                "required_evidence",
                meta.get("required_context", []),
            ),
            edit_recipe=edit_recipe or [],
            anti_patterns=meta.get(
                "anti_patterns",
                meta.get("not_applicable_when", []),
            ),
            applies_when=meta.get("applies_when", []),
            not_applicable_when=meta.get("not_applicable_when", []),
            required_context=meta.get("required_context", []),
            procedure=procedure,
            verifier=meta.get("verifier", "manual"),
            success_count=int(meta.get("success_count", 0)),
            failure_count=int(meta.get("failure_count", 0)),
            negative_transfer_notes=meta.get("negative_transfer_notes", []),
            domains=meta.get("domains", []),
        )
