# SWE-bench fixture: sympy__sympy-24152

- repo: `sympy/sympy`
- base_commit: `b9af885473ad7e34b5b0826cb424dd26d8934670`
- environment_setup_commit: `c6cb7c5602fa48034ab1bd43c2347a7e8488f12e`
- version: `1.12`
- swebench_python: `3.9`
- swebench_packages: `mpmath flake8`
- swebench_pip_packages: `['mpmath==1.3.0', 'flake8-comprehensions']`
- swebench_install: `python -m pip install -e .`