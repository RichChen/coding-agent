# SOLID D1 返工收尾（SWE-bench Lite 子集）

日期：2026-06-26  
执行文档：`docs/SOLID-D1-REWORK-EXECUTION.zh-CN.md`

---

## 0) 前置：D-2 §5 异常轮检测

已合入（返工前置依赖）：

- `src/eval/metrics.py`：`is_degenerate_run()`、`RepeatedEvalMetrics.degenerate_run_indices` / `valid_run_count`，聚合 mean/std/CI 仅基于有效轮。
- `src/eval/report.py`：`## Anomalous Runs` 段、Per-Run `⚠ degenerate` 标记、有效轮不足时显著性 withheld。
- `tests/test_metrics.py`：3 项新增测试。
- 全量 pytest：**143 passed**（基线 139 + 新增 4）。

---

## 1) R2：requests-3362 可移植化

### 方案

- 数据集断言改用 `%SWEBENCH_REQUESTS_PY%`，不再硬编码 `.tmp` 绝对路径。
- 新增 `scripts/setup_swebench_envs.py`：在 `.swebench_envs/requests-3362/` 用 conda 建 py39 环境并按官方 specs 安装 requests 2.10（支持从旧 `.tmp/swebench_oracle_py39` 一次性迁移）。
- `.gitignore` 增加 `.swebench_envs/`。
- `tests/fixtures/repos/swebench_psf__requests-3362/SETUP.md` 注明需先跑 setup 脚本。

### 自检

```text
rg "D:\\\\|C:\\\\Users|\.tmp|swebench_oracle_py39" datasets/swebench_lite_tasks.json
→ 零命中
```

### 验证

```bash
python scripts/setup_swebench_envs.py
set SWEBENCH_REQUESTS_PY=D:\crq\src\coding-harness\.swebench_envs\requests-3362\python.exe
python scripts/check_dataset_oracle.py --dataset datasets/swebench_lite_tasks.json
→ Checked 10 oracle task(s). All oracle solutions PASS.
```

---

## 2) R3：sympy 题面解法泄露清洗

### 规则

在 `scripts/build_swebench_lite_subset.py` 新增 `_sanitize_problem()` + `PATCH_HINT_MARKERS`（如 `the following code fix`、`i thus propose`、`### code fix` 等）。从首个信号词处截断；若截断后 <80 字符则回退并 WARN。

### 重建

```bash
python scripts/build_swebench_lite_subset.py --refresh-descriptions --dataset-out datasets/swebench_lite_tasks.json
→ refreshed_descriptions: 10
```

### 抽查

- `sympy__sympy-24152` description 已不再包含 `propose` / `code fix` / 待改 diff，止于 Workaround 段之前。
- 实例集合仍为 **10 个**（3 repo），fixture 与断言未变。

### 清洗前后 baseline 对比（返工 eval 实测）

| 任务 | 清洗前 baseline（POLISH 5/5） | 清洗后 baseline（REWORK 5/5） | 说明 |
|------|------------------------------|-------------------------------|------|
| sympy-24152 | 5/5（泄题） | **3/5** | 泄题缓解，不再恒过 |
| sympy-24213 | 5/5 | **5/5** | 仍稳定通过（题面未含显式 patch 信号词） |
| sympy-24066 | 0/5 | **3/5** | 方差任务，见 Unstable |
| flask-4992 | 5/5 | **5/5** | 仍稳定 |
| 其余 sympy | 多数 0/5 | 0/5 | 难度保持 |

旧报告 `reports/report_20260625T180202.md` 中 baseline 30% 含泄题抬高，**不可与返工后数字直接对比**。

---

## 3) R1：干净 A/B（runs=5）

### 命令

```bash
set SWEBENCH_REQUESTS_PY=D:\crq\src\coding-harness\.swebench_envs\requests-3362\python.exe
python scripts/run_eval.py --dataset datasets/swebench_lite_tasks.json --configs baseline plan_act_permissive --runs 5
```

### 报告

- 路径：`reports/report_20260626T101113.md`（CSV：`reports/report_20260626T101113.csv`）
- 启动：2026-06-26 11:21 UTC+8；完成：2026-06-26 18:11 UTC+8（约 6.8 小时）
- **无 HTTP 402**；报告未出现 `Anomalous Runs` 段，5 轮均计入有效统计

### 核心结果

| 指标 | baseline | plan_act_permissive | Delta |
|------|----------|---------------------|-------|
| Success Rate mean/std | **32.0% / 8.4** | **24.0% / 15.2** | -8.0% |
| Avg Steps mean/std | 22.1 / 1.2 | 18.6 / 1.1 | -3.5 |
| Avg Time mean/std | 205655ms / 22310 | 270479ms / 50807 | +64824ms |

**Bootstrap 95% CI**

- baseline success rate：`[26.0%, 38.0%]`
- plan_act_permissive success rate：`[12.0%, 34.0%]`
- 配对 delta（首轮）：`[-30.0%, +0.0%]`

**显著性结论**：CI 重叠，**无显著差异**（报告原文：「CI 重叠，差异可能由方差导致，需更多 run。」）。与 POLISH 旧报告「倾向显著」相反，但以本报告为准。

### Per-Run 摘要

**baseline**（5 轮均有效）：30% / 40% / 20% / 30% / 40%

**plan_act_permissive**：20% / 30% / 40% / 30% / **0%**（run5 全失败但 avg steps=17.3，未触发 degenerate 检测；若需更稳结论可补跑单轮）

### 与旧报告对比

| 项 | POLISH（402 污染） | REWORK（干净） |
|----|-------------------|----------------|
| baseline mean | 30.0%（24152/24213 泄题 5/5） | 32.0%（24152 降至 3/5） |
| plan_act mean | 12.0%（run3~5 坍塌 0%） | 24.0%（5 轮均有推进） |
| 显著性 | 误报「倾向显著」 | **无显著差异** |

> **旧结论作废**：`reports/report_20260625T180202.md` 中 plan_act run3~5 因 HTTP 402 坍塌，且 sympy 题面泄题；其「倾向显著」与 baseline 30% 均不可信。POLISH-CLOSEOUT §4.2 已加注作废。

---

## 4) 与 POLISH 的差异摘要

| 项 | POLISH | REWORK |
|----|--------|--------|
| requests 断言 | 硬编码 `.tmp` 绝对路径 | `%SWEBENCH_REQUESTS_PY%` + setup 脚本 |
| sympy 题面 | 完整 problem（含解法） | 信号词截断清洗 |
| A/B 显著性 | 402 污染 → 误报显著 | baseline 32% vs plan_act 24%，**无显著差异** |
| A/B 报告 | `report_20260625T180202.md`（作废） | `report_20260626T101113.md` |
| pytest | 139 | 143 |
