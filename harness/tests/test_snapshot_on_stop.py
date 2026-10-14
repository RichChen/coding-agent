"""A step deadline must export the workspace before the container is removed."""
import pytest

from src.runtime.loop import AgentLoop


class _FakeBackend:
    def __init__(self, active=True):
        self.active = active
        self.snapshot_error = None
        self.candidate_delta = None
        self.snapshot_flag = None

    async def close(self, *, snapshot=False):
        self.snapshot_flag = snapshot
        if snapshot and self.active:
            self.candidate_delta = {"changed": {"pkg/edited.py": "bmV3"}, "deleted": []}
        self.active = False
        return True


@pytest.mark.asyncio
async def test_step_deadline_exports_before_cleanup():
    backend = _FakeBackend(active=True)
    result = object()
    await AgentLoop._close_backend(backend, result)
    assert backend.snapshot_flag is True
    assert backend.candidate_delta
    assert "pkg/edited.py" in backend.candidate_delta["changed"]


@pytest.mark.asyncio
async def test_missing_container_records_snapshot_error():
    backend = _FakeBackend(active=False)
    await AgentLoop._close_backend(backend, object())
    assert backend.snapshot_flag is False
    assert backend.snapshot_error == "container_gone_before_snapshot"
