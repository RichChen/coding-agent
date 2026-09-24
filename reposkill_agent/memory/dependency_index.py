"""Optimization only: an index never substitutes for validity checking."""

from reposkill_agent.memory.records import MemoryRecord


class DependencyIndex:
    def __init__(self, records: list[MemoryRecord]):
        self.index: dict[tuple[str, str], set[str]] = {}
        self.unknown = set()
        for record in records:
            if not record.dependency_mapping_complete or not record.dependencies:
                self.unknown.add(record.memory_id)
            for dep in record.dependencies:
                self.index.setdefault((dep.kind, dep.key), set()).add(record.memory_id)

    def affected(self, changed: set[tuple[str, str]]) -> set[str]:
        result = set(self.unknown)
        for key in changed:
            result.update(self.index.get(key, ()))
        return result
