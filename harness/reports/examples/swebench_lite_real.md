# SWE-bench Lite Subset — Real Eval Report

> Status: **real API-backed run** (2026-06-25, Solid D-1).  
> Dataset source: `princeton-nlp/SWE-bench_Lite` (test split, 实拉筛选与逐实例可行性验证)。

## 命令

```bash
python scripts/run_eval.py --dataset datasets/swebench_lite_tasks.json --configs baseline --runs 3
```

Source report: `reports/report_20260625T113256.md`

## 纳入实例（经步骤 2 可行性验证通过）

- `sympy__sympy-24909`
- `sympy__sympy-24213`
- `sympy__sympy-24152`

对应离线 fixture：

- `tests/fixtures/repos/swebench_sympy__sympy-24909`
- `tests/fixtures/repos/swebench_sympy__sympy-24213`
- `tests/fixtures/repos/swebench_sympy__sympy-24152`

## 区分度结果（baseline ×3）

| Config | Runs | Tasks | Success Rate mean/std | Avg Steps mean/std | Avg Time mean/std (ms) |
|--------|------|-------|-----------------------|--------------------|------------------------|
| baseline | 3 | 3 | **11.1% / 19.2** | 26.0 / 5.3 | 184488 / 36802 |

- 明显低于 90%，区分度恢复（自造任务集 93.8% 的天花板问题被打破）。
- Pass matrix：`0/3`, `1/3`, `0/3`，任务难度与方差均高于现有自造集。
- Unstable：`swebench_sympy__sympy-24213` 为 1/3。

## 弃用实例（节选）

完整弃用清单见 `reports/examples/swebench_lite_validation_log.json`。

- `pallets__flask-5063`：目标节点收集失败（collector 问题）。
- `pallets__flask-4992`：依赖冲突（`werkzeug.urls.url_quote` 导入错误）。
- `psf__requests-3362`：依赖缺失（`urllib3`）。
- `psf__requests-2674`：旧测试节点收集失败。

## 说明

- 任务 ID、测试名全部来自真实数据集字段（`instance_id` / `FAIL_TO_PASS` / `PASS_TO_PASS`）。
- 受本地依赖可安装性约束，本轮实际纳入 3 个实例（宁少勿多）。
- 每个实例均满足：`test_patch` 后 FAIL_TO_PASS 先失败、应用 gold `patch` 后通过，并已固化 `.oracle`。
