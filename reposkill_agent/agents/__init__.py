"""Role-based deterministic agents for Phase 3."""

from reposkill_agent.agents.contracts import AgentContext, AgentResult, RoleAgent
from reposkill_agent.agents.locator import LocatorAgent
from reposkill_agent.agents.manager import ManagerAgent
from reposkill_agent.agents.memory_curator import MemoryCuratorAgent
from reposkill_agent.agents.qa import QAAgent

__all__ = [
    "AgentContext",
    "AgentResult",
    "DeveloperAgent",
    "LLMDeveloperAgent",
    "LocatorAgent",
    "ManagerAgent",
    "MemoryCuratorAgent",
    "QAAgent",
    "RoleAgent",
]


def __getattr__(name: str):
    if name == "DeveloperAgent":
        from reposkill_agent.agents.developer import DeveloperAgent

        return DeveloperAgent
    if name == "LLMDeveloperAgent":
        from reposkill_agent.agents.llm_developer import LLMDeveloperAgent

        return LLMDeveloperAgent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
