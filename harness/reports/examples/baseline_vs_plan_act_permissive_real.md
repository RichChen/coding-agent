# Baseline vs Plan-Act Permissive — Real Eval Report

> Status: **real API-backed run** (2026-06-25).
>
> Model: `deepseek-v4-pro` via DeepSeek OpenAI-compatible API  
> Command:
> ```bash
> python scripts/run_eval.py --dataset datasets/repo_tasks.json --configs baseline plan_act_permissive --runs 3
> ```
> Source report: `reports/report_20260625T073908.md`

Generated: 2026-06-25T07:39:08Z

Dataset: `datasets/repo_tasks.json` (9 tasks)

## ✅ 对比说明（已消除策略 confound）

本次为 **单变量 Planner A/B**：`plan_act_permissive.yaml` = `baseline.yaml` 原样 + `runtime.mode: plan_act` + `runtime.planner.enabled: true`。  
两配置 **`policy.command.allow_all: true`**、工具集、context 设置完全一致，仅隔离 Planner + 每步 plan 刷新效应。

## Summary

| Config | Runs | Tasks | Success Rate mean/std | Avg Steps mean/std | Avg Time mean/std (ms) | Tool Fail Rate mean/std | Policy Blocks mean/std |
|--------|------|-------|-----------------------|--------------------|------------------------|-------------------------|------------------------|
| baseline | 3 | 9 | 85.2% / 6.4 | 4.6 / 0.3 | 19006 / 2052 | 3.0% / 1.2 | 0.0 / 0.0 |
| plan_act_permissive | 3 | 9 | 92.6% / 6.4 | 5.1 / 0.1 | 19434 / 423 | 0.7% / 1.1 | 0.0 / 0.0 |

## Mean Delta Comparison

| Metric | baseline | plan_act_permissive | Delta |
|--------|----------|---------------------|-------|
| Success Rate | 85.2% | 92.6% | **+7.4%** |
| Avg Steps | 4.6 | 5.1 | +0.5 |
| Avg Time (ms) | 19006 | 19434 | +428 |
| Tool Fail Rate | 3.0% | 0.7% | -2.4% |
| Policy Blocks | 0 | 0 | 0 |

## Bootstrap 95% CI

- baseline success rate (run resampling): [77.8%, 88.9%]
- plan_act_permissive success rate (run resampling): [88.9%, 100.0%]
- Delta (plan_act_permissive - baseline, first run tasks): [+0.0%, +0.0%]

## Per-Run Results

### baseline

| Run | Passed | Failed | Success Rate |
|-----|--------|--------|--------------|
| 1 | 8 | 1 | 88.9% |
| 2 | 7 | 2 | 77.8% |
| 3 | 8 | 1 | 88.9% |

### plan_act_permissive

| Run | Passed | Failed | Success Rate |
|-----|--------|--------|--------------|
| 1 | 8 | 1 | 88.9% |
| 2 | 8 | 1 | 88.9% |
| 3 | 9 | 0 | **100.0%** |

## 解读

- 在 **同策略** 前提下，plan_act + 每步 `Plan update:` system 消息刷新带来约 **+7.4%** 成功率（3 run mean）。
- 步数仅 +0.5，耗时几乎持平；无 policy block 干扰。
- 仍受模型/API 方差影响（见 `docs/SOLID-ROADMAP.zh-CN.md` §2.2）；结论应结合 bootstrap CI 与多 run 表述。

## 代码证据

- Plan 刷新：`src/runtime/loop.py`（`plan_changed` → append `Plan update:` system 消息）
- 对照 config：`configs/plan_act_permissive.yaml`
- 单测：`tests/test_planner_loop_sync.py::test_plan_act_appends_plan_update_message_after_advance_sync`
