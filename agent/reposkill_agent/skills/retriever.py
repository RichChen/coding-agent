"""Simple keyword-based skill retriever."""

from __future__ import annotations

from reposkill_agent.core.contracts import TaskSpec
from reposkill_agent.skills.domain import domain_compatible, task_domains
from reposkill_agent.skills.models import SkillSpec


class SkillRetriever:
    """Retrieve skills by lexical overlap with task issue/tags."""

    def retrieve(
        self,
        task: TaskSpec,
        skills: list[SkillSpec],
        top_k: int = 3,
    ) -> list[SkillSpec]:
        """Return top-k skills by lightweight keyword scoring."""
        query_tokens = self._tokens(f"{task.issue} {' '.join(task.tags)}")
        tag_set = {tag.lower() for tag in task.tags}
        task_domain = task_domains(task)
        scored: list[tuple[int, SkillSpec]] = []
        for skill in skills:
            if not domain_compatible(skill, task):
                continue
            target = " ".join(
                [
                    skill.id.replace("_", " "),
                    skill.name,
                    skill.purpose,
                    skill.pattern,
                    " ".join(skill.applies_when),
                    " ".join(skill.required_evidence),
                    " ".join(skill.required_context),
                ]
            )
            tokens = self._tokens(target)
            score = len(query_tokens & tokens)
            applies = {item.lower() for item in skill.applies_when}
            if tag_set & applies:
                score += 3
            if task_domain and task_domain & {d.lower() for d in skill.domains}:
                score += 4
            if score > 0:
                scored.append((score, skill))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [item[1] for item in scored[:top_k]]

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return {token.strip(".,:;()[]{}").lower() for token in text.split() if token.strip()}
