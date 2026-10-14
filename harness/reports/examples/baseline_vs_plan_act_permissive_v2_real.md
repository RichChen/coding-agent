# Baseline vs Plan-Act Permissive v2 — Real Eval Report

> Status: **real API-backed run** (2026-06-25), after P1-1 B (`suggested_tools` + structured replan).
>
> Model: `deepseek-v4-pro`  
> Command:
> ```bash
> python scripts/run_eval.py --dataset datasets/repo_tasks.json --configs baseline plan_act_permissive --runs 3
> ```
> Source report: `reports/report_20260625T083227.md`

Dataset: **12 tasks** (expanded from 9 in P0-1 B)

## Summary

| Config | Runs | Success Rate mean/std | Avg Steps mean/std | Avg Time mean/std (ms) |
|--------|------|-----------------------|--------------------|------------------------|
| baseline | 3 | 94.4% / 4.8 | 4.1 / 0.2 | 17194 / 1257 |
| plan_act_permissive | 3 | **100.0% / 0.0** | 4.6 / 0.2 | 19776 / 1765 |

**Δ +5.6%**（同策略单变量 A/B，已消除 policy confound）

## vs A 批次（9 任务）

| 批次 | baseline | plan_act_permissive | Δ |
|------|----------|---------------------|---|
| A 批次 | 85.2% | 92.6% | +7.4% |
| B 批次 v2（12 任务 + suggested_tools） | 94.4% | 100.0% | +5.6% |

12 任务集上方差更小；plan_act 在 3 run 内全绿。

## 代码证据

- `src/runtime/planner.py` — `suggested_tools`、结构化 replan、`replanned` 标志
- `tests/test_planner.py`、`tests/test_planner_loop_sync.py`
