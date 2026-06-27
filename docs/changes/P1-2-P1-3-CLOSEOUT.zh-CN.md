# P1-2 / P1-3 收尾补强记录

## 状态

已完成针对 P1-2 Context 与 P1-3 Agent-as-Tool 的收尾补强。

本次工作遵守边界：

- 不重做已有 P1-2/P1-3。
- 不做 L2 LLM context summary。
- 不做 `max_depth > 1`、多 worker、递归 subagent。
- 不让子 Agent 写文件。
- 不重构整个 `AgentLoop`。

## P1-2 缺口闭合

### 统一入口

新增：

- `src/runtime/context.py`

提供：

- `ContextPolicyConfig`
- `build_context_hooks()`

`src/harness/factory.py` 已改为通过该入口装配 context hooks。

### 关键上下文保护

`src/runtime/compact.py` 新增保留规则：

- 非 tool 消息不压缩，因此原始 user 任务、plan 文本天然保留。
- 最近 1 条失败 tool result 保留。
- 最近若干条文件修改相关 tool result 保留：
  - `write_file`
  - `search_replace`
  - `edit_file`

### compact 配置

新增：

- `configs/context_compact.yaml`

用于后续 compact on/off 对比。

### 证据

新增/更新测试：

- compact 后字符数下降。
- user 任务、失败 tool result、修改文件相关 tool result 不被误压。
- context policy 能构建 `MicroCompactHooks`。

## P1-3 缺口闭合

### repo task

`datasets/repo_tasks.json` 新增：

- `medium_subagent_cross_file`

新增 fixture：

- `tests/fixtures/repos/medium_subagent_cross_file/`

任务描述会引导父 Agent 先调用 `subagent_task` 分析跨文件 bug，再修复代码。

### 子 Agent 输出结构

`src/tools/subagent.py` 现在会从子 Agent final answer 轻量解析：

- `summary`
- `findings`
- `suggested_next_steps`
- `confidence`

并保持原 JSON 字段兼容。

### 父子 trace 链接

`AgentRunResult` 新增：

```python
subagent_traces: list[dict]
```

父 Agent 成功执行 `subagent_task` 后，会记录：

```json
{
  "child_task_id": "...",
  "trace_file": "...",
  "success": true
}
```

`src/eval/runner.py` 与 `scripts/run_single.py` 已写入 run summary metadata。

### 展示材料

新增：

- `docs/examples/subagent_trace_redacted.jsonl`

该文件是脱敏 mock-style 示例，用于说明父 trace 如何链接子 trace。

## 验证

Focused 测试：

```bash
C:\Users\Administrator\.conda\envs\coding-harness\python.exe -m pytest tests/test_compact.py tests/test_subagent.py -q --basetemp .pytest_tmp
```

结果：

```text
17 passed
```

全量测试将在本记录之后运行，并以最终回复为准。

全量测试：

```bash
C:\Users\Administrator\.conda\envs\coding-harness\python.exe -m pytest tests -q --basetemp .pytest_tmp
```

结果：

```text
93 passed
```

静态验收：

- `configs/context_compact.yaml` 可通过 `load_config()` 加载，`micro_compact=true`。
- `configs/subagent_readonly.yaml` 可通过 `load_config()` 加载，`enabled=true`、`max_depth=1`、`readonly=true`。
- `datasets/repo_tasks.json` 当前 9 条任务，包含 `medium_subagent_cross_file`。
- `docs/examples/subagent_trace_redacted.jsonl` 已存在。

## 联网 eval/demo

**2026-06-25 更新：已完成真实 API 跑分。** 详见 `docs/changes/P1-EVIDENCE-REAL-RUNS.zh-CN.md`。

摘要：

| 实验 | 命令 | 结果 |
|------|------|------|
| Subagent demo | `run_single.py` + `subagent_readonly.yaml` | Success，父子 trace 已脱敏至 `docs/examples/subagent_trace_redacted.jsonl` |
| Repo + subagent | `run_eval.py --dataset repo_tasks --configs subagent_readonly` | **77.8%** (7/9)，`medium_subagent_cross_file` 触发 subagent |
| Compact A/B | `run_eval.py --dataset mini_tasks --configs baseline context_compact` | baseline **88.9%** vs compact **91.7%** |

示例报告：

- `reports/examples/subagent_readonly_repo_tasks_real.md`
- `reports/examples/baseline_vs_context_compact_real.md`
