from events.pipeline import retry_policy


def test_retry_policy_zero_attempts():
    assert retry_policy(0) == 0
