# Baseline vs Context Compact — Stress Tasks (Real API)

> Dataset: `datasets/compact_stress_tasks.json` (3 hard multi-step tasks)  
> Model: DeepSeek `deepseek-v4-pro`, 2026-06-25

```bash
python scripts/run_eval.py --dataset datasets/compact_stress_tasks.json --configs baseline context_compact
```

Source: `reports/report_20260625T044616.md`

## Summary

| Config | Tasks | Passed | Success Rate | Avg Steps | Avg Time (ms) |
|--------|-------|--------|--------------|-----------|---------------|
| baseline | 3 | 2 | **66.7%** | 5.7 | 13744 |
| context_compact | 3 | 2 | **66.7%** | 5.3 | 13250 |

## Delta

| Metric | Delta |
|--------|-------|
| Success Rate | **0.0%**（相同通过任务） |
| Avg Steps | -0.3 |
| Avg Time | -494 ms |

## Bootstrap 95% CI (per-task, n=3)

- baseline: [0.0%, 100.0%]
- context_compact: [0.0%, 100.0%]
- Delta: [+0.0%, +0.0%]

> 任务数仅 3 条，CI 很宽；主要价值是「长任务上 compact 未降低通过率」。

## Per-task

| Task | baseline | context_compact |
|------|----------|-----------------|
| `hard_multi_read_chain` | PASS (5 steps) | PASS (5 steps) |
| `hard_cross_file_api` | PASS (8 steps) | PASS (4 steps) |
| `hard_report_transform` | FAIL | FAIL |

## Interpretation

- 两条配置在 stress 集上 **通过率相同**；compact 未造成回归。  
- `hard_multi_read_chain` 为新增多文件阅读任务（`parts/alpha~delta` + `aggregator.py`）。  
- 本 run 中 `context_events` 仍多为空（5 步任务 tool 消息数常未超过 `keep_recent=3`）；更长链路任务才会稳定触发 L1 压缩。  
- 面试说法：compact 在 **hard 多步任务** 上与 baseline 持平，而非在 mini 短任务上臆测长上下文收益。
