# SWE-bench fixture: sympy__sympy-23262

- repo: `sympy/sympy`
- base_commit: `fdc707f73a65a429935c01532cd3970d3355eab6`
- environment_setup_commit: `9a6104eab0ea7ac191a09c24f3e2d79dcd66bda5`
- version: `1.11`
- swebench_python: `3.9`
- swebench_packages: `mpmath flake8`
- swebench_pip_packages: `['mpmath==1.3.0', 'flake8-comprehensions']`
- swebench_install: `python -m pip install -e .`