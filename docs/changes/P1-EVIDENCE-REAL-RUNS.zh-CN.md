# P1 真实 API 证据补充记录

## 状态

已完成三项 P1 加分项的真实 API 跑分与材料更新（`coding-harness` conda 环境）。

## 1. Subagent 真实 demo + 脱敏 trace

命令：

```bash
# 复制 fixture 到临时 workspace 后单任务演示
python scripts/run_single.py --config configs/subagent_readonly.yaml --workspace <fixture_copy> \
  "Use subagent_task first to inspect parser.py and service.py ..."
```

结果：

- `Success: True`，5 steps，subagent 被调用
- 父 trace：`traces/single_task_default_20260625T033344.jsonl`
- 子 trace：`traces/subagent_1782358430172_call_00_MQe3vTJ5J6DkdZWaMQ2L8781_subagent_20260625T033350.jsonl`
- 脱敏示例：`docs/examples/subagent_trace_redacted.jsonl`（基于真实 run，call id / 路径已缩短）

## 2. Repo tasks + subagent_readonly eval

命令：

```bash
python scripts/run_eval.py --dataset datasets/repo_tasks.json --configs subagent_readonly
```

结果（`reports/report_20260625T033754.md`）：

| 指标 | 值 |
|------|-----|
| Success Rate | 77.8% (7/9) |
| Avg Steps | 5.4 |
| Avg Time | 15837 ms |
| Tool Fail Rate | 13.2% |
| Policy Blocks | 5 |

`medium_subagent_cross_file`：触发了 `subagent_traces`，但裁判 FAIL（修了 service 而非 parser）。

示例报告：`reports/examples/subagent_readonly_repo_tasks_real.md`

## 3. mini_tasks baseline vs context_compact

命令：

```bash
python scripts/run_eval.py --dataset datasets/mini_tasks.json --configs baseline context_compact
```

结果（`reports/report_20260625T034508.md`）：

| Config | Success Rate | Avg Steps | Avg Time (ms) |
|--------|--------------|-----------|---------------|
| baseline | 88.9% (32/36) | 2.7 | 5599 |
| context_compact | 91.7% (33/36) | 3.0 | 6129 |

结论：短任务上 compact **未降低**成功率（+2.8%），步数/耗时略增。多数 mini 任务过短，未产生 `context_events`（未触发压缩）。

示例报告：`reports/examples/baseline_vs_context_compact_real.md`

## 附带 bugfix

`src/runtime/loop.py`：未知工具时 `ToolResult` 补 `output=""`，避免 subagent eval 中模型调用未启用工具时崩溃。

## 原始报告文件

- `reports/report_20260625T033754.md` / `.csv` — repo subagent
- `reports/report_20260625T034508.md` / `.csv` — mini compact 对比
- `reports/mini_compact_eval_log.txt` — 完整 stdout 日志
