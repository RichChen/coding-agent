from scripts.swebench_specs import install_commands, spec_row


def test_sympy_install_comes_from_official_specs():
    commands = install_commands(spec_row("sympy/sympy", "1.5"))
    text = " && ".join(commands)
    assert "mpmath==1.3.0" in text
    assert "pip install -e ." in text


def test_requirements_spec_uses_the_fetched_file():
    commands = install_commands(spec_row("django/django", "3.0"))
    assert commands[0].endswith("-r /tmp/swebench-requirements.txt")
