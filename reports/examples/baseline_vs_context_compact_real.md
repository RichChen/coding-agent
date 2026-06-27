# Baseline vs Context Compact — Real Eval Report

> Status: **real API-backed run** (DeepSeek `deepseek-v4-pro`, 2026-06-25).

```bash
C:\Users\Administrator\.conda\envs\coding-harness\python.exe scripts\run_eval.py \
  --dataset datasets\mini_tasks.json --configs baseline context_compact
```

Source: `reports/report_20260625T034508.md`

## Summary

| Config | Tasks | Passed | Success Rate | Avg Steps | Avg Time (ms) | Tool Fail Rate |
|--------|-------|--------|--------------|-----------|---------------|----------------|
| baseline | 36 | 32 | 88.9% | 2.7 | 5599 | 0.0% |
| context_compact | 36 | 33 | 91.7% | 3.0 | 6129 | 8.2% |

## Delta

| Metric | baseline | context_compact | Delta |
|--------|----------|-----------------|-------|
| Success Rate | 88.9% | 91.7% | **+2.8%** |
| Avg Steps | 2.7 | 3.0 | +0.3 |
| Avg Time (ms) | 5599 | 6129 | +529 |

## Interpretation

On `mini_tasks` (mostly 2–4 step file tasks), enabling L1 micro-compact did **not** hurt success rate. Pass rate slightly improved (+2.8%) at the cost of marginally more steps/time and a small tool-failure rate on compact runs.

**Important caveat:** most mini tasks are too short to trigger compaction (`context_events` stayed empty in traces because tool message count rarely exceeds `keep_recent=3`). This comparison mainly shows compact does not regress short-task performance; long multi-tool repo tasks are the better stress test for compaction.

## Failed tasks (both configs struggled)

- `file_create_react_component`
- `file_create_markdown_table`
- `file_create_logging_config` (compact run used more steps due to tool retries)
