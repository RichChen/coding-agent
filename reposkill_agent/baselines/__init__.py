"""External and vanilla baseline runners for RepoSkillAgent comparisons."""

from reposkill_agent.baselines.contracts import (
    BaselineRunner,
    BaselineRunRequest,
    BaselineRunResult,
)

BASELINE_REGISTRY: dict[str, str] = {
    "vanilla_deepseek": "vanilla_deepseek",
    "openhands_sdk": "openhands_sdk",
    "swe_agent": "swe_agent",
    "aider": "aider",
}


def get_baseline(name: str, **kwargs) -> BaselineRunner:
    """Instantiate a baseline runner by registry name."""
    if name not in BASELINE_REGISTRY:
        raise ValueError(f"Unknown baseline: {name}. Choose from: {sorted(BASELINE_REGISTRY)}")
    if name == "vanilla_deepseek":
        from reposkill_agent.baselines.vanilla_deepseek import VanillaDeepSeekBaseline

        return VanillaDeepSeekBaseline(**kwargs)
    if name == "openhands_sdk":
        from reposkill_agent.baselines.openhands_sdk import OpenHandsSdkBaseline

        return OpenHandsSdkBaseline()
    if name == "swe_agent":
        from reposkill_agent.baselines.swe_agent import SweAgentBaseline

        return SweAgentBaseline()
    if name == "aider":
        from reposkill_agent.baselines.aider import AiderBaseline

        return AiderBaseline()
    raise ValueError(f"Unknown baseline: {name}")


__all__ = [
    "BASELINE_REGISTRY",
    "BaselineRunRequest",
    "BaselineRunResult",
    "BaselineRunner",
    "get_baseline",
]
