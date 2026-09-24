from events.message import Result
from events.pipeline import deadletter_result


def test_deadletter_returns_result():
    result = deadletter_result("failed")
    assert isinstance(result, Result)
    assert not result.ok
