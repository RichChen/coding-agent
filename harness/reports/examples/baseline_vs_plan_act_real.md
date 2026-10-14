# Baseline vs Plan-Act — Real Eval Report

> Status: **real API-backed run** (2026-06-25).
>
> Model: `deepseek-v4-pro` via DeepSeek OpenAI-compatible API  
> Command:
> ```bash
> python scripts/run_eval.py --dataset datasets/repo_tasks.json --configs baseline plan_act --runs 3
> ```
> Source report: `reports/report_20260625T061433.md`

Generated: 2026-06-25T06:14:33Z

Dataset: `datasets/repo_tasks.json` (9 tasks)

## ⚠️ 对比说明（面试必讲）

本次 **不是** 纯 Planner A/B：`plan_act.yaml` 同时启用了 **hardened 级命令白名单**（`allow_all: false`），而 `baseline.yaml` 为宽松策略（`allow_all: true`）。  
因此成功率差异 **混合了**「显式规划」与「策略收紧」两种因素。解读时应强调 harness 能量化 tradeoff，而非宣称 plan_act 单独 +7.4%。

更公平的后续实验：新增 `plan_act_permissive.yaml`（plan_act + baseline 策略）或 `baseline` vs `hardened` 单独对比。

## Summary

| Config | Runs | Tasks | Success Rate mean/std | Avg Steps mean/std | Avg Time mean/std (ms) | Tool Fail Rate mean/std | Policy Blocks mean/std |
|--------|------|-------|-----------------------|--------------------|------------------------|-------------------------|------------------------|
| baseline | 3 | 9 | 81.5% / 6.4 | 4.3 / 0.1 | 12230 / 239 | 0.8% / 1.4 | 0.0 / 0.0 |
| plan_act | 3 | 9 | 88.9% / 0.0 | 5.9 / 0.1 | 16748 / 110 | 15.9% / 0.7 | 7.0 / 0.0 |

## Mean Delta Comparison

| Metric | baseline | plan_act | Delta |
|--------|----------|----------|-------|
| Success Rate | 81.5% | 88.9% | +7.4% |
| Avg Steps | 4.3 | 5.9 | +1.6 |
| Avg Time (ms) | 12230 | 16748 | +4519 |
| Tool Fail Rate | 0.8% | 15.9% | +15.1% |
| Policy Blocks | 0 | 7.0 (avg/run) | +7.0 |

## Bootstrap 95% CI

- baseline success rate (run resampling): [77.8%, 88.9%]
- plan_act success rate (run resampling): [88.9%, 88.9%]
- Delta (plan_act - baseline, first run tasks): [+0.0%, +33.3%]

## Per-Run Results

### baseline

| Run | Passed | Failed | Success Rate |
|-----|--------|--------|--------------|
| 1 | 7 | 2 | 77.8% |
| 2 | 8 | 1 | 88.9% |
| 3 | 7 | 2 | 77.8% |

### plan_act

| Run | Passed | Failed | Success Rate |
|-----|--------|--------|--------------|
| 1 | 8 | 1 | 88.9% |
| 2 | 8 | 1 | 88.9% |
| 3 | 8 | 1 | 88.9% |

## Interpretation

1. **稳定性**：plan_act 三轮均为 8/9（88.9%），方差 0；baseline 在 77.8%–88.9% 波动。  
2. **代价**：plan_act 平均多 1.6 步、多 ~4.5s，工具失败率与 policy block 显著上升——与 hardened 策略一致。  
3. **Planner 叙事**：trace 中可见 `plan_created` / `plan_updated` / `plan_replanned`；行为是否因 plan 本身提升，需 **同策略** 的 follow-up eval。  
4. **与历史跑分**：本次 baseline 81.5% 低于 2026-06-24 的 95.8%（同数据集 8 任务时期），说明 **模型/API 方差** 存在；应用 `--runs 3` + CI 讲稳定性，不单报一次数字。

## Trace 验收（缺口 1）

在 `plan_act` + `lifecycle_events: true` 下，events JSONL 应含 `plan_created`、`plan_updated`；工具失败时最多一次 `plan_replanned`。
