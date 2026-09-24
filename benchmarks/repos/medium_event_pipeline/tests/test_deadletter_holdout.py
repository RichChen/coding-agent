from events.message import Result
from events.pipeline import deadletter_result


def test_deadletter_preserves_error_message():
    result = deadletter_result("timeout exceeded")
    assert isinstance(result, Result)
    assert not result.ok
    assert result.error == "timeout exceeded"
