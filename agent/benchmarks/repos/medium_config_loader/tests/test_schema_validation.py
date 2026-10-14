from config_loader.schema import Result, validate_config


def test_validate_config_rejects_non_int_timeout():
    result = validate_config({"timeout": "bad", "retries": 1})
    assert isinstance(result, Result)
    assert not result.ok


def test_validate_config_accepts_valid():
    result = validate_config({"timeout": 10, "retries": 2})
    assert result.ok
