from events.pipeline import retry_policy


def test_retry_policy_allows_three_attempts():
    assert retry_policy(1) == 3
