# Solid D-1 SWE-bench Lite 接入收尾（2026-06-25）

> 执行文档：`docs/SOLID-D1-SWEBENCH-EXECUTION.zh-CN.md`  
> 目标：接入本地可跑 SWE-bench Lite 轻量子集，产出真实区分度证据。

## 测试与校验

```bash
C:\Users\Administrator\.conda\envs\coding-harness\python.exe scripts/check_dataset_oracle.py --dataset datasets/swebench_lite_tasks.json
C:\Users\Administrator\.conda\envs\coding-harness\python.exe -m pytest tests -q --basetemp $env:TEMP\coding-harness-pytest
```

- Oracle：`Checked 3 oracle task(s). All oracle solutions PASS.`
- 全量测试：`139 passed`

## 产物

### 1) 实拉筛选脚本

- `scripts/select_swebench_instances.py`
  - 从 `princeton-nlp/SWE-bench_Lite` 实拉候选
  - 支持 repo 过滤（本次：`pallets/flask`, `psf/requests`, `sympy/sympy`）
  - 输出 UTF-8 JSONL（避免 PowerShell 重定向编码问题）

### 2) 逐实例验证 + 固化脚本

- `scripts/build_swebench_lite_subset.py`
  - 顺序执行：下载 base_commit → 应用 `test_patch` → FAIL_TO_PASS 先失败 → 应用 gold `patch` → FAIL_TO_PASS 转通过 → PASS_TO_PASS 子集通过
  - 失败即弃用并记录原因
  - 通过实例固化为离线 fixture + `.oracle`
  - 自动生成 `datasets/swebench_lite_tasks.json`

### 3) 数据集与 fixture

- `datasets/swebench_lite_tasks.json`（3 任务）
- `tests/fixtures/repos/swebench_sympy__sympy-24909`
- `tests/fixtures/repos/swebench_sympy__sympy-24213`
- `tests/fixtures/repos/swebench_sympy__sympy-24152`
- 验证日志：`reports/examples/swebench_lite_validation_log.json`

## 纳入实例（真实 ID）

- `sympy__sympy-24909`
- `sympy__sympy-24213`
- `sympy__sympy-24152`

## 弃用实例（代表性原因）

- `pallets__flask-5063`：pytest collector 无法收集目标 node。
- `pallets__flask-4992`：`werkzeug` 版本冲突导致导入失败。
- `psf__requests-3362`：`urllib3` 缺失。
- `psf__requests-2674`：旧 node 形式收集失败。

> 结论：按“装不上或 gold 跑不通就弃用”的策略，最终纳入 3 个稳定可复现实例（宁少勿多）。

## 区分度 eval（baseline ×3）

```bash
C:\Users\Administrator\.conda\envs\coding-harness\python.exe scripts/run_eval.py --dataset datasets/swebench_lite_tasks.json --configs baseline --runs 3
```

- 原始报告：`reports/report_20260625T113256.md`
- 示例报告：`reports/examples/swebench_lite_real.md`

核心结果：

- baseline success rate：**11.1% / 19.2**（3 任务 × 3 runs）
- 显著低于 90%，满足“恢复区分度”目标。

## 备注

- 本次仅做 D-1（SWE-bench 子集接入）；D-2 文档收口项仍按 `docs/SOLID-D2-CLOSEOUT-EXECUTION.zh-CN.md` 执行。
- 为避免污染主环境，实例验证使用临时 virtualenv；主项目依赖未被持久改动。
