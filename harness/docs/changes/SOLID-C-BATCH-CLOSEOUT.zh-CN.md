# Solid C 层批次收尾（2026-06-25）

> 按 `docs/SOLID-C-BATCH-EXECUTION.zh-CN.md` 顺序完成 5 项；决策已锁定（自造 hard、token 触发 compact、cancel+retry 细分、成本维度、真 SSE defer）。

## 测试

```bash
C:\Users\Administrator\.conda\envs\coding-harness\python.exe -m pytest tests -q --basetemp $env:TEMP\coding-harness-pytest
```

**结果：139 passed**（基线 131 → +8 新测）

## 逐项改动与证据

### P0-1 C — 自造 4 个 hard 难任务

| 改动 | 路径 |
|------|------|
| 新增 4 任务 + fixture | `hard_long_context_chain`, `hard_multi_step_locate`, `hard_regression_fix`, `hard_refactor_keep_green` |
| 数据集 12→16 | `datasets/repo_tasks.json` |
| Oracle | `tests/fixtures/repos/hard_*/.oracle/` |
| Oracle CI | `scripts/check_dataset_oracle.py` → 7 任务 PASS |
| 区分度 eval | `reports/examples/baseline_16tasks_discrimination_real.md`（baseline **91.7%** vs B 批次 12 任务 **94.4%**） |

### P1-2 A — token 估算触发 compact + 正收益

| 改动 | 路径 |
|------|------|
| `estimate_tokens()` + threshold 门控 | `src/runtime/compact.py` |
| Schema / 透传 | `src/config/schema.py`, `src/runtime/context.py` |
| 对齐 confound 的 config | `configs/context_compact_threshold.yaml`（与 baseline 同工具/步数，仅 +compact） |
| 单测 | `tests/test_compact.py`（threshold skip/compact + estimated_tokens） |
| 真实 eval | `reports/examples/baseline_vs_context_compact_threshold_real.md` |

**亮点**：compact_stress 上 **耗时 -13.6%、步数 -0.8**，成功率不回归；repo 16 任务耗时 **-2.3%**。

### P2-1 C（部分）— cancel token + retry 5xx/4xx

| 改动 | 路径 |
|------|------|
| `LLMError.status_code` | `src/llm/client.py` |
| HTTP 仅 429/5xx 可重试 | `src/runtime/retry.py`（补 `LLMErrorKind` import） |
| `FailureReason.CANCELLED` + `cancel_event` | `src/runtime/loop.py` |
| 单测 | `tests/test_llm_client.py`, `tests/test_agent_loop.py` |

### P0-3 B — 成本列 + per-task pass matrix

| 改动 | 路径 |
|------|------|
| `est_cost` / `total_tokens` | `src/eval/metrics.py` |
| Cost Summary + Pass Matrix 段 | `src/eval/report.py` |
| `--cost-per-1k` | `scripts/run_eval.py` |
| runner 透传 | `src/eval/runner.py` |
| 单测 | `tests/test_runner.py::TestCostAndPassMatrix` |
| 真实 eval | `reports/report_20260625T100708.md`（`$41.55` est. cost @ $0.5/1k） |

### P0-2 收尾 — flaky 接入真实多 run

| 改动 | 路径 |
|------|------|
| `--runs 5` baseline | `reports/report_20260625T095943.md` |
| Unstable: `hard_report_transform` 2/5, `medium_multi_file_sync` 4/5 | 报告 Unstable Tasks 段 |
| 稳定性叙事 | `docs/FAILURE-CASES.zh-CN.md` §6 |

## Eval 报告索引

| 实验 | 报告 |
|------|------|
| **区分度恢复**（16 任务 baseline ×3） | `reports/examples/baseline_16tasks_discrimination_real.md` |
| **compact 正收益**（baseline vs threshold ×3） | `reports/examples/baseline_vs_context_compact_threshold_real.md` |
| compact_stress 补充 | `reports/report_20260625T094353.md` |
| 成本 + pass matrix（compare ×3） | `reports/report_20260625T100708.md` |
| flaky ×5 | `reports/report_20260625T095943.md` |

## 未做 / 仍 defer

- 真 SSE streaming（P2-1 B/C）
- L2 LLM 摘要
- 外部 benchmark（SWE-bench）
- P2-2 Docker runner
- 多模型矩阵 eval

## 备注

- 新 hard 任务对当前模型偏易（多 run 全 PASS）；区分度主要靠 **`hard_report_transform` + 任务集扩容**。
- `context_compact_threshold.yaml` 曾在首轮 eval 含 confound（多工具/少步数），已修正为与 baseline 对齐后再跑 A/B。
