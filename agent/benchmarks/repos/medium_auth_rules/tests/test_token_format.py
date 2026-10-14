from auth_rules.tokens import parse_token


def test_v2_token_format_parsed():
    raw = '{"version": 2, "subject": "svc-billing", "value": "tok_v2_abc"}'
    parsed = parse_token(raw)
    assert parsed["version"] == 2
    assert parsed["subject"] == "svc-billing"
    assert parsed["token"] == "tok_v2_abc"


def test_v1_token_still_supported():
    raw = '{"version": 1, "subject": "svc-legacy", "token": "tok_v1_xyz"}'
    parsed = parse_token(raw)
    assert parsed["version"] == 1
    assert parsed["token"] == "tok_v1_xyz"
