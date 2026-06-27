# Polish 收尾：P2-1 stream 接入 + 文档同步 + plan_act eval

## 状态

已完成 polish 四项中的工程与文档部分（eval 结果见 `reports/examples/baseline_vs_plan_act_real.md`）。

## 改动

### 1. `stream_chat` 接入 AgentLoop + EventBus

- `TracingConfig.llm_stream_events`（默认 `false`）
- `configs/debug.yaml` 开启 `llm_stream_events: true`
- `AgentLoop._call_llm()`：当 `use_llm_stream=True` 时走 `stream_chat()`，将 `message_delta` / `tool_call_delta` / `llm_stream_done` / `llm_error` 写入 EventBus
- 仍保留 `llm_complete` 事件，与非流式路径一致

### 2. 清理死代码

- 删除未使用的 `plan_summary_for_prompt()`（`src/runtime/planner.py`）

### 3. 更新 `CODEX-DEFERRED-GAPS.zh-CN.md`

- 缺口 1 标记为已完成；决策表填写 Codex/Cursor 结论

### 4. plan_act 真实 eval

- `repo_tasks` × `baseline` vs `plan_act`，`--runs 3`
- 报告：`reports/examples/baseline_vs_plan_act_real.md`（源：`reports/report_20260625T061433.md`）
- 结果：baseline 81.5% vs plan_act 88.9%；**注意 plan_act 含 hardened 命令策略，非纯 Planner A/B**

## 验证

```bash
C:\Users\Administrator\.conda\envs\coding-harness\python.exe -m pytest tests -q --basetemp .pytest_tmp
```
