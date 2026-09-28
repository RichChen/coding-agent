"""Docker control retries and infra_error classification (6B-FIX G3). No Docker needed."""
import asyncio

import pytest

from scripts.run_swe_task import grader_infra_reason, run_infra_reason
from src.execution import docker
from src.execution.baseline_image_backend import BaselineImageBackend
from src.execution.docker import DockerExecutionBackend, DockerUnavailable, is_transient

IMAGE = "python@sha256:" + "0" * 64


@pytest.fixture
def waits(monkeypatch):
    seen = []

    async def sleep(seconds):
        seen.append(seconds)

    monkeypatch.setattr(docker, "_sleep", sleep)
    return seen


def _backend(outcomes, cls=DockerExecutionBackend):
    """A backend whose Docker CLI returns or raises the given outcomes in order."""
    backend = cls(image=IMAGE)
    calls = []

    async def control(*args, **kwargs):
        calls.append(args)
        if args[0] == "rm":
            return 0, b"", b""
        item = outcomes.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item

    backend._control = control
    return backend, calls


def test_retry_waits_are_2_5_10():
    assert docker.RETRY_WAITS == (2, 5, 10)


def test_transient_failure_is_retried_and_recorded(waits):
    reset = DockerUnavailable("Docker control unavailable: ConnectionResetError")
    backend, _ = _backend([reset, TimeoutError(), (0, b"ok", b"")])
    assert asyncio.run(backend._ok("exec", "x", op="snapshot")) == b"ok"
    assert waits == [2, 5]
    assert [(r["op"], r["retry"], r["wait_s"]) for r in backend.docker_retries] == [("snapshot", 1, 2), ("snapshot", 2, 5)]
    assert backend.docker_retries[0]["error"].startswith("DockerUnavailable: Docker control unavailable")
    assert all(r["at"] for r in backend.docker_retries)


def test_three_retries_then_docker_unavailable(waits):
    backend, _ = _backend([ConnectionResetError()] * 4)
    with pytest.raises(DockerUnavailable, match="after 3 retries"):
        asyncio.run(backend._ok("info"))
    assert waits == [2, 5, 10]
    assert [r["retry"] for r in backend.docker_retries] == [1, 2, 3]


def test_nonzero_cli_exit_is_retried(waits):
    backend, _ = _backend([(1, b"", b"error during connect: EOF"), (0, b"ok", b"")])
    assert asyncio.run(backend._ok("start", "c")) == b"ok"
    assert waits == [2]


def test_harness_script_failures_are_not_retried(waits):
    script = (1, b"", b"Traceback (most recent call last):\nValueError: generated native copy mismatch")
    backend, _ = _backend([script])
    with pytest.raises(DockerUnavailable, match="native copy mismatch"):
        asyncio.run(backend._ok("exec", "c", "python"))
    assert waits == [] and backend.docker_retries == []
    assert not is_transient(DockerUnavailable("Docker exec failed: delta_too_large\n"))
    assert not is_transient(ValueError("x"))


def test_create_retry_removes_the_half_created_container_first(waits):
    backend, calls = _backend([ConnectionResetError(), (0, b"id", b"")])
    asyncio.run(backend._ok(*backend.create_args()))
    assert [c[0] for c in calls] == ["create", "rm", "create"]
    assert calls[1] == ("rm", "-f", backend.name)


def test_snapshot_export_goes_through_the_retry(waits):
    delta = b'{"changed": {}, "deleted": [], "skipped_files": 0}'
    backend, _ = _backend([DockerUnavailable("Docker control unavailable: ConnectionResetError"), (0, delta, b"")],
                          cls=BaselineImageBackend)
    assert asyncio.run(backend.export_delta())["changed"] == {}
    assert backend.docker_retries[0]["op"] == "snapshot"


def test_snapshot_delta_too_large_is_not_retried(waits):
    backend, _ = _backend([(2, b"", b"delta_too_large\n")], cls=BaselineImageBackend)
    with pytest.raises(ValueError, match="delta_too_large"):
        asyncio.run(backend.export_delta())
    assert waits == []


def test_container_removal_is_retried(waits):
    backend, calls = _backend([(0, b"", b"")])
    rm_results = [ConnectionResetError(), (0, b"", b"")]

    async def control(*args, **kwargs):
        calls.append(args)
        if args[0] == "rm":
            item = rm_results.pop(0)
            if isinstance(item, BaseException):
                raise item
            return item
        return 0, b"", b""

    backend._control = control
    backend._owned = True
    assert asyncio.run(backend.close()) is True
    assert [c[0] for c in calls] == ["rm", "rm", "ps"]
    assert backend.docker_retries[0]["op"] == "rm"


class _Backend:
    def __init__(self, unavailable=None, cleanup_ok=True):
        self.unavailable_error = unavailable
        self.cleanup_ok = cleanup_ok


def test_run_infra_reason():
    delta = {"changed": {}, "deleted": []}
    assert run_infra_reason(None, _Backend(), delta, None) is None
    assert run_infra_reason("StoreError", _Backend(), delta, None) == "StoreError"
    assert run_infra_reason(None, _Backend(unavailable="Docker info failed after 3 retries"), None, None).startswith("container start failed")
    snap = "DockerUnavailable: Docker snapshot failed after 3 retries: ConnectionResetError"
    assert run_infra_reason(None, _Backend(), None, snap).startswith("candidate snapshot failed")
    assert run_infra_reason(None, _Backend(), None, None) == "candidate snapshot missing"
    assert run_infra_reason(None, _Backend(cleanup_ok=False), delta, None) == "container cleanup failed"


def test_grader_failure_before_tests_is_infra_but_a_later_timeout_is_not():
    before = {"status": "invalid_env", "reason": "TimeoutError: ", "execution_status": None}
    assert grader_infra_reason(before).startswith("grader failed before test execution: TimeoutError")
    start_failed = {"status": "invalid_env", "reason": "DockerUnavailable: Docker create failed after 3 retries"}
    assert grader_infra_reason(start_failed) is not None
    timed_out = {"status": "fail", "reason": None, "execution_status": "timed_out"}
    assert grader_infra_reason(timed_out) is None
    receipt_lost = {"status": "invalid_env", "reason": "JSONDecodeError", "execution_status": "succeeded"}
    assert grader_infra_reason(receipt_lost) is None
