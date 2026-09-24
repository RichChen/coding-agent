"""Memory curator agent for extracting procedural memory."""

from __future__ import annotations

from reposkill_agent.agents.contracts import RoleAgent
from reposkill_agent.core.contracts import GraphRunResult
from reposkill_agent.memory.consolidator import MemoryConsolidator
from reposkill_agent.memory.procedural import ProceduralMemory


class MemoryCuratorAgent(RoleAgent):
    """Curate success traces into reusable procedural memory."""

    role = "memory_curator"

    def __init__(self) -> None:
        self.consolidator = MemoryConsolidator()

    def curate(self, run: GraphRunResult) -> ProceduralMemory | None:
        return self.consolidator.build_procedural(run)
