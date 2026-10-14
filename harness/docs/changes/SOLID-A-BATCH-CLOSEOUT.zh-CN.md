# Solid A 层批次收尾（2026-06-25）

> 按 `docs/SOLID-A-BATCH-EXECUTION.zh-CN.md` 顺序完成 5 项 A 层加固。

## 测试

```bash
C:\Users\Administrator\.conda\envs\coding-harness\python.exe -m pytest tests -q --basetemp $env:TEMP\coding-harness-pytest
```

**结果：112 passed**（基线 108 → +4 新测）

## 逐项改动与证据

### P1-1 A — plan 每步刷新 + permissive 对照

| 改动 | 路径 |
|------|------|
| plan 推进/replan 后 append `Plan update:` system 消息 | `src/runtime/loop.py` |
| 单变量对照 config | `configs/plan_act_permissive.yaml` |
| 单测 | `tests/test_planner_loop_sync.py::test_plan_act_appends_plan_update_message_after_advance_sync` |
| 真实 eval（3 run，已消除策略 confound） | `reports/examples/baseline_vs_plan_act_permissive_real.md` |

**Eval 数字**：baseline 85.2% vs plan_act_permissive **92.6%**（Δ +7.4%），`--runs 3`。

### P1-3 A — subagent 任务 + child 输出校验

| 改动 | 路径 |
|------|------|
| 任务描述明确 fix `parser.py` | `datasets/repo_tasks.json` |
| child payload `schema_ok` + 父 trace 记录 | `src/tools/subagent.py`, `src/runtime/loop.py` |
| 单测 | `tests/test_subagent.py::test_subagent_child_missing_schema_fields_marks_schema_ok_false` |
| 真实 eval | `reports/examples/subagent_readonly_repo_tasks_real.md` |

**Eval 数字**：subagent_readonly **96.3%**（3 run mean）；`medium_subagent_cross_file` **3/3 PASS**。

### P0-2 A — 裁判失败明细

| 改动 | 路径 |
|------|------|
| `_explain_expected` → `expected_failures` | `src/eval/runner.py`, `src/eval/metrics.py` |
| 报告 Failure Detail 列 | `src/eval/report.py` |
| 单测 | `tests/test_runner.py::test_multi_assert_partial_failure_returns_failures` |

**验收**：`reports/report_20260625T074930.csv` 中 `hard_report_transform` 含具体 assert 失败原因。

### P0-4 A — trace 示例补全

| 产物 | 路径 |
|------|------|
| plan_act events（含 replan） | `docs/examples/plan_act_events_redacted.jsonl` |
| LLM stream events | `docs/examples/llm_stream_events_redacted.jsonl` |
| 面试稿引用 | `docs/INTERVIEW-DEMO.zh-CN.md` |

### P2-1 A — LLMErrorKind retry + request metadata

| 改动 | 路径 |
|------|------|
| `RetryPolicy.should_retry` 优先 `LLMError.kind` | `src/runtime/retry.py` |
| `llm_complete` 事件补 `model` / `usage` | `src/runtime/loop.py` |
| 单测 | `tests/test_llm_client.py::test_retry_policy_uses_llm_error_kind` |
| Mock 兼容 | `tests/fixtures/mock_llm.py`（`model` 属性） |

## Eval 报告索引

| 实验 | 报告 |
|------|------|
| baseline vs plan_act_permissive（无 confound） | `reports/examples/baseline_vs_plan_act_permissive_real.md` |
| subagent_readonly repo tasks | `reports/examples/subagent_readonly_repo_tasks_real.md` |
| 原始 CSV | `reports/report_20260625T073908.csv`, `reports/report_20260625T074930.csv` |

## 未做 / 留 B 层

- `http` 5xx vs 4xx 细分 retry（文档标注 B 层）
- 真 SSE streaming（P2-1 B）
- `plan_act.yaml` 与 baseline 的旧 confound 对比仍保留在 `baseline_vs_plan_act_real.md` 作历史参考
