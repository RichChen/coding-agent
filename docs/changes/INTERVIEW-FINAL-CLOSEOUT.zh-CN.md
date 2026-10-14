# 面试前收尾记录

## 已修复

### 0. `.env` 自动加载

`src/harness/factory.py` 已支持在 `load_config()` 时读取项目根目录 `.env`。

加载规则：

- 系统环境变量优先。
- 如果系统环境变量不存在，则使用 `.env` 中的值。
- 不打印 API Key。

### 1. pytest 误收集 fixture repo

在 `pyproject.toml` 中加入：

```toml
norecursedirs = ["tests/fixtures/repos"]
```

这样 `pytest tests/` 不会把 `tests/fixtures/repos/` 下的 repo fixture 当成测试目录递归收集。

### 2. pytest marker 警告

在 `pyproject.toml` 中注册了：

```toml
markers = [
    "asyncio: marks async tests that require pytest-asyncio",
]
```

## 当前测试状态

在 `coding-harness` conda 环境中已验证全量测试：

```bash
C:\Users\Administrator\.conda\envs\coding-harness\python.exe -m pytest tests -q --basetemp .pytest_tmp
```

结果：

```text
85 passed
```

如果不使用该 conda 环境，且当前 Python 没有安装 `pytest-asyncio`，async 测试会被跳过，而不是执行失败：

- `pytest tests -q --basetemp .pytest_tmp`
- 结果：`55 passed, 30 skipped`

这说明项目逻辑本身没有被 fixture 误收集拖坏，但如果要让 async 测试实际执行，仍需要安装 dev 依赖：

```bash
pip install -e ".[dev]"
```

## 真实 eval（已完成）

在 Cursor Agent 可联网环境中，使用 `coding-harness` conda 环境 + 项目根目录 `.env` 已成功跑通真实 API eval。

### 冒烟

```bash
C:\Users\Administrator\.conda\envs\coding-harness\python.exe scripts\run_single.py --config configs\baseline.yaml "List all files in the workspace using list_dir"
```

结果：`Success: True`，DeepSeek API 200 OK。

### 全量对比（3 轮 × 8 任务 × 2 配置）

```bash
C:\Users\Administrator\.conda\envs\coding-harness\python.exe scripts\run_eval.py --dataset datasets\repo_tasks.json --compare --runs 3
```

耗时约 10 分钟。摘要：

| Config | Success Rate mean/std | Avg Steps mean/std | Avg Time mean/std (ms) | Tool Fail Rate mean/std | Policy Blocks mean/std |
|--------|----------------------|--------------------|------------------------|-------------------------|------------------------|
| baseline | 95.8% / 7.2 | 4.2 / 0.1 | 10395 / 497 | 0.0% / 0.0 | 0.0 / 0.0 |
| hardened | 87.5% / 12.5 | 5.5 / 0.3 | 13600 / 1527 | 16.3% / 1.2 | 5.3 / 0.6 |

原始报告：`reports/report_20260624T130653.md` / `.csv`

### 已同步到面试材料

- `reports/examples/baseline_vs_hardened_real.md` — 真实数字 + 解读
- `reports/examples/baseline_vs_hardened_real.csv` — 完整 per-run/per-task 明细
- `docs/examples/real_trace_redacted.jsonl` — 来自 `easy_remove_debug` baseline 成功 trace（call id 已缩短）

### 说明：此前 Codex 环境网络失败

在部分受限 Agent 环境中曾出现 `All connection attempts failed`（非 API Key 问题，是运行环境无出站网络）。当前 Cursor 终端可正常访问 `api.deepseek.com`。

## 交接提示

如果新 agent 接手，优先看：

1. [docs/archive/IMPROVEMENT-PLAN.zh-CN.md](../archive/IMPROVEMENT-PLAN.zh-CN.md)
2. 本目录下的 `P0-*` / `P1-*` 记录
3. `INTERVIEW-FINAL-CLOSEOUT.zh-CN.md`
