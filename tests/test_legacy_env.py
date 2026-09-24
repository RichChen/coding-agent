from reposkill_agent.memory.legacy_env import is_legacy_env_artifact, split_legacy


def test_legacy_env_noise_is_marked():
    samples = [
        "pip install six pluggy",
        "pip download numpy",
        "ModuleNotFoundError: No module named 'pluggy'",
        "No module named six",
        "/bin/sh: 1: git: not found",
        "find / -name mpmath -type d",
        "wrote a stub package under /tmp/stubs/pluggy.py",
        "Temporary failure in name resolution",
    ]
    assert all(is_legacy_env_artifact(sample) for sample in samples)


def test_repository_facts_are_kept():
    samples = [
        "pytest tests live under testing/",
        "django uses tests/runtests.py",
        "sqlmigrate.py must be changed together with the migration executor",
        "python -m pytest testing/python/fixtures.py -q",
    ]
    kept, legacy = split_legacy(tuple(samples))
    assert kept == tuple(samples)
    assert legacy == ()
