from auth_rules.tokens import parse_token


def test_v2_service_token_roundtrip_fields():
    raw = '{"version": 2, "subject": "svc-payments", "value": "pay_secret_99"}'
    parsed = parse_token(raw)
    assert parsed["subject"] == "svc-payments"
    assert parsed["token"] == "pay_secret_99"
