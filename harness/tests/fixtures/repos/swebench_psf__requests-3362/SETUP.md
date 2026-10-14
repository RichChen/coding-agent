# SWE-bench fixture: psf__requests-3362

- repo: `psf/requests`
- base_commit: `36453b95b13079296776d11b09cab2567ea3e703`
- environment_setup_commit: `36453b95b13079296776d11b09cab2567ea3e703`
- version: `2.10`
- swebench_python: `3.9`
- swebench_packages: `pytest`
- swebench_pip_packages: `[]`
- swebench_install: `python -m pip install .`
- requests interpreter: set `SWEBENCH_REQUESTS_PY` via `python scripts/setup_swebench_envs.py`