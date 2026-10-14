from scripts.swebench_specs import install_commands, spec_row


def test_sympy_install_comes_from_official_specs():
    commands = install_commands(spec_row("sympy/sympy", "1.5"))
    text = " && ".join(commands)
    assert "mpmath==1.3.0" in text
    assert "pip install -e ." in text


def test_old_sklearn_uses_cython_that_can_compile_the_tree():
    commands = install_commands(spec_row("scikit-learn/scikit-learn", "0.22"))
    text = " && ".join(commands)
    assert "cython==0.29.37" in text
    assert "numpy==1.19.2" in text


def test_requirements_spec_uses_the_fetched_file():
    commands = install_commands(spec_row("django/django", "3.0"))
    assert any(command.endswith("-r /tmp/swebench-requirements.txt") for command in commands)
