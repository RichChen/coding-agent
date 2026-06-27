# Subagent Readonly — Real Repo Tasks Eval

> Status: **real API-backed run** (DeepSeek `deepseek-v4-pro`, 2026-06-25).

```bash
C:\Users\Administrator\.conda\envs\coding-harness\python.exe scripts/run_eval.py \
  --dataset datasets/repo_tasks.json --configs subagent_readonly --runs 3
```

Source: `reports/report_20260625T074930.md`

## Summary

| Config | Runs | Tasks | Success Rate mean/std | Avg Steps mean/std | Avg Time mean/std (ms) |
|--------|------|-------|-----------------------|--------------------|------------------------|
| subagent_readonly | 3 | 9 | **96.3% / 6.4** | 5.6 / 0.1 | 21829 / 2120 |

## Per-run

| Run | Passed | Failed | Success Rate |
|-----|--------|--------|--------------|
| 1 | 9 | 0 | 100.0% |
| 2 | 8 | 1 | 88.9% |
| 3 | 9 | 0 | 100.0% |

## Per-task highlights

| Task | Result (3 runs) | Notes |
|------|-----------------|-------|
| `medium_subagent_cross_file` | **3/3 PASS** | 任务描述明确「fix parser.py」；subagent 分析 + 父 Agent 改对文件 |
| `hard_report_transform` | 2/3 PASS | Run 2 失败：`command_success failed: python check_report.py (exit=1)` |
| Other 7 tasks | 全部 PASS | |

## Subagent evidence

- Parent trace 示例：`traces/medium_subagent_cross_file_subagent_readonly_20260625T074104.jsonl`
- child 输出 schema：`schema_ok` 字段写入 payload 与 `subagent_traces`
- Redacted interview example: `docs/examples/subagent_trace_redacted.jsonl`

## Interview talking point

> `medium_subagent_cross_file` 从 77.8% 期的「subagent 触发但改错文件」变为 **3/3 PASS**。Harness 通过任务描述对齐 + child 输出 schema 校验（`schema_ok`）+ 裁判失败明细，让 Multi-Agent 链路可讲、可 debug。
