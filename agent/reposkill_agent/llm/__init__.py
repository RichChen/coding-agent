"""LLM integration layer for RepoSkillAgent."""

__all__ = [
    "FileEdit",
    "LLMConfig",
    "MissingLLMConfigError",
    "MockModelClient",
    "ModelClient",
    "PatchPlan",
    "build_system_prompt",
    "build_user_prompt",
]


def __getattr__(name: str):
    if name in {"LLMConfig", "MissingLLMConfigError", "MockModelClient", "ModelClient"}:
        from reposkill_agent.llm import client as client_mod

        return getattr(client_mod, name)
    if name in {"build_system_prompt", "build_user_prompt"}:
        from reposkill_agent.llm import prompts as prompts_mod

        return getattr(prompts_mod, name)
    if name in {"FileEdit", "PatchPlan"}:
        from reposkill_agent.llm import schemas as schemas_mod

        return getattr(schemas_mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
