# Failure Taxonomy (auto-generated)

Generated: 2026-06-27T03:25:19.210087+00:00
Sources: report_20260626T194843.csv, report_20260626T101113.csv

Total failure rows: 99

## By failure_reason
| Reason | Count | Share |
|--------|-------|-------|
| step_limit | 47 | 47.5% |
| none | 38 | 38.4% |
| timeout | 12 | 12.1% |
| model_parse_error | 2 | 2.0% |

## By assert type (from expected_failures)
| Assert type | Count | Share |
|-------------|-------|-------|
| command_success | 99 | 100.0% |

## By config
| Config | Failures | Total rows | Fail rate |
|--------|----------|------------|-----------|
| baseline | 50 | 80 | 62.5% |
| plan_act_permissive | 49 | 80 | 61.3% |

## Representative tasks (top failures)
| Task ID | Config | Count | Dominant reason | Sample expected_failure |
|---------|--------|-------|-----------------|-------------------------|
| swebench_sympy__sympy-23191 | baseline | 8 | none | command_success failed: set PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 && python -m pytest -q sympy/vector/tests/test_printing.... |
| swebench_sympy__sympy-23191 | plan_act_permissive | 8 | none | command_success failed: set PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 && python -m pytest -q sympy/vector/tests/test_printing.... |
| swebench_sympy__sympy-24102 | baseline | 8 | step_limit | command_success failed: set PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 && python -m pytest -q sympy/parsing/tests/test_mathemat... |
| swebench_sympy__sympy-24102 | plan_act_permissive | 8 | step_limit | command_success failed: set PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 && python -m pytest -q sympy/parsing/tests/test_mathemat... |
| swebench_sympy__sympy-24909 | baseline | 8 | none | command_success failed: set PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 && python -m pytest -q sympy/physics/units/tests/test_pr... |
| swebench_sympy__sympy-24909 | plan_act_permissive | 7 | step_limit | command_success failed: set PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 && python -m pytest -q sympy/physics/units/tests/test_pr... |
| swebench_psf__requests-3362 | baseline | 6 | none | command_success failed: set PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 && %SWEBENCH_REQUESTS_PY% -m pytest -q tests/test_reques... |
| swebench_psf__requests-3362 | plan_act_permissive | 6 | none | command_success failed: set PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 && %SWEBENCH_REQUESTS_PY% -m pytest -q tests/test_reques... |
| swebench_sympy__sympy-23262 | baseline | 6 | step_limit | command_success failed: set PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 && python -m pytest -q sympy/utilities/tests/test_lambdi... |
| swebench_sympy__sympy-23262 | plan_act_permissive | 6 | step_limit | command_success failed: set PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 && python -m pytest -q sympy/utilities/tests/test_lambdi... |
| swebench_sympy__sympy-24066 | plan_act_permissive | 6 | none | command_success failed: set PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 && python -m pytest -q sympy/physics/units/tests/test_qu... |
| swebench_sympy__sympy-23117 | baseline | 5 | step_limit | command_success failed: set PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 && python -m pytest -q sympy/tensor/array/tests/test_ndi... |
| swebench_sympy__sympy-23117 | plan_act_permissive | 5 | step_limit | command_success failed: set PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 && python -m pytest -q sympy/tensor/array/tests/test_ndi... |
| swebench_sympy__sympy-24066 | baseline | 5 | none | command_success failed: set PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 && python -m pytest -q sympy/physics/units/tests/test_qu... |
| swebench_sympy__sympy-24152 | baseline | 4 | step_limit | command_success failed: set PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 && python -m pytest -q sympy/physics/quantum/tests/test_... |

## Notes
- `step_limit` 占失败行 47.5%；scaffold 跑（更多自测步数）中撞步数墙仍常见。
- `command_success` 类 assert 失败占 100.0%，与开启 `run_command` 后 judge 跑 pytest 直接相关。
- 多 config 对比时失败率差异需结合污染语境解读（见 `docs/CONTAMINATION-NOTES.zh-CN.md`）：**绝对成功率不作能力指标**。
