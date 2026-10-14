# SWE-bench fixture: sympy__sympy-24066

- repo: `sympy/sympy`
- base_commit: `514579c655bf22e2af14f0743376ae1d7befe345`
- environment_setup_commit: `c6cb7c5602fa48034ab1bd43c2347a7e8488f12e`
- version: `1.12`
- swebench_python: `3.9`
- swebench_packages: `mpmath flake8`
- swebench_pip_packages: `['mpmath==1.3.0', 'flake8-comprehensions']`
- swebench_install: `python -m pip install -e .`