# SWE-bench fixture: sympy__sympy-24213

- repo: `sympy/sympy`
- base_commit: `e8c22f6eac7314be8d92590bfff92ced79ee03e2`
- environment_setup_commit: `c6cb7c5602fa48034ab1bd43c2347a7e8488f12e`
- version: `1.12`
- swebench_python: `3.9`
- swebench_packages: `mpmath flake8`
- swebench_pip_packages: `['mpmath==1.3.0', 'flake8-comprehensions']`
- swebench_install: `python -m pip install -e .`