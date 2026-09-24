"""Prompt builders for LLM developer agent."""

from __future__ import annotations

from reposkill_agent.agents.contracts import AgentContext

MAX_FILE_CHARS = 6000
MAX_TEST_OUTPUT_CHARS = 4000
MAX_SKILL_CARDS = 2
MAX_MEMORY_HINTS = 3


def build_system_prompt() -> str:
    return (
        "You are a code-fixing agent for small Python repositories.\n"
        "Respond with a single JSON object only (no markdown fences).\n"
        "Schema:\n"
        '{"summary": str, "edits": [{"path": str, "content": str, "reason": str}], '
        '"confidence": float, "needs_more_context": bool, "requested_context": [str]}\n'
        "Rules:\n"
        "- Only edit files from the allowed_paths list.\n"
        "- Use full file content in each edit (mode=write).\n"
        "- Do not invent files or paths.\n"
        "- Keep changes minimal while making tests pass.\n"
        "- If context is insufficient, set needs_more_context=true, edits=[], "
        "and list requested_context hints (e.g. tests, callers, config).\n"
        "- SkillCard/MemoryHint blocks are advisory; do not copy them verbatim.\n"
        "- No long natural-language explanations outside JSON fields."
    )


def format_skill_cards(skills: list[dict]) -> str:
    """Compact SkillCard v2 injection block."""
    if not skills:
        return ""
    lines: list[str] = []
    for skill in skills[:MAX_SKILL_CARDS]:
        recipe = skill.get("edit_recipe") or []
        if not recipe and skill.get("procedure"):
            recipe = [line.strip() for line in str(skill["procedure"]).splitlines() if line.strip()]
        evidence = skill.get("required_evidence") or skill.get("required_context") or []
        anti = skill.get("anti_patterns") or skill.get("not_applicable_when") or []
        lines.extend(
            [
                "SkillCard:",
                f"id: {skill.get('id', '')}",
                f"pattern: {skill.get('pattern', skill.get('purpose', ''))}",
                f"evidence: {', '.join(evidence)}",
                f"recipe: {'; '.join(recipe[:4])}",
                f"avoid: {', '.join(anti[:3])}",
                f"verify: {skill.get('verifier', '')}",
            ]
        )
    return "\n".join(lines)


def format_memory_hints(hints: list[dict]) -> str:
    """Compact MemoryHint v2 injection block."""
    if not hints:
        return ""
    lines: list[str] = []
    for hint in hints[:MAX_MEMORY_HINTS]:
        if hint.get("text"):
            receipt = hint.get("injection_receipt") or {}
            lines.extend(
                [
                    "LightweightMemoryReference:",
                    f"variant: {hint.get('variant', '')}",
                    f"source: {hint.get('memory_id', '')}",
                    f"snapshot: {hint.get('snapshot_hash', '')}",
                    f"content_hash: {hint.get('requested_hash', '')}",
                    f"receipt_status: {receipt.get('status', 'unavailable')}",
                    f"reference: {hint['text']}",
                ]
            )
            continue
        files = hint.get("likely_files") or []
        applies = hint.get("applies_when") or []
        lines.extend(
            [
                "MemoryHint:",
                f"type: {hint.get('type', '')}",
                f"source: {hint.get('source_task_id', hint.get('source_task', ''))}",
                f"pattern: {hint.get('successful_pattern', hint.get('workflow', ''))}",
                f"files: {', '.join(files[:4])}",
                f"convention: {hint.get('repo_convention', '')}",
                f"warn: {hint.get('warning', '')}",
                f"confidence: {hint.get('confidence', '')}",
                f"applies_when: {', '.join(applies[:4])}",
            ]
        )
    return "\n".join(lines)


def build_json_repair_prompt(*, allowed_paths: list[str], raw_preview: str) -> str:
    """Minimal repair prompt after llm_parse_error (no API key, no full prior prompt)."""
    schema = (
        '{"summary": str, "edits": [{"path": str, "content": str, "reason": str}], '
        '"confidence": float, "needs_more_context": bool, "requested_context": [str]}'
    )
    preview = raw_preview[:200]
    return (
        "Your previous response was invalid JSON. Return one valid JSON object only.\n"
        f"Schema: {schema}\n"
        f"allowed_paths: {allowed_paths}\n"
        f"raw_response_preview: {preview}\n"
        "Do not wrap in markdown fences."
    )


def build_user_prompt(
    *,
    context: AgentContext,
    file_contents: dict[str, str],
    allowed_paths: list[str],
    repo_files: list[str],
    test_output: str,
) -> str:
    lines = [
        f"task_id: {context.task.id}",
        f"issue: {context.task.issue}",
        f"node: {context.node.id}",
        f"replan_count: {context.replan_count}",
        f"expected_files: {context.task.expected_files}",
        f"allowed_paths: {allowed_paths}",
        f"test_command: {context.task.test_command}",
    ]
    if test_output:
        clipped = test_output[:MAX_TEST_OUTPUT_CHARS]
        lines.append(f"failing_test_output:\n{clipped}")
    if repo_files:
        lines.append(f"repo_files_sample: {repo_files[:40]}")
    for path in allowed_paths:
        content = file_contents.get(path, "")
        clipped = content[:MAX_FILE_CHARS]
        lines.append(f"--- file: {path} ---\n{clipped}")
    skill_block = format_skill_cards(context.active_skills)
    if skill_block:
        lines.append(skill_block)
    memory_block = format_memory_hints(context.memory_hints)
    if memory_block:
        lines.append(memory_block)
    if context.previous_actions:
        lines.append(f"previous_actions_count: {len(context.previous_actions)}")
    lines.append("constraints: max_files_per_patch=3; only allowed_paths")
    return "\n".join(lines)


def prompt_length_summary(system: str, user: str) -> dict[str, int]:
    """Return prompt length stats for reports (no content)."""
    return {
        "system_len": len(system),
        "user_len": len(user),
        "total_len": len(system) + len(user),
    }
