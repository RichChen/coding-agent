# P1-1 Planner 行为增强记录

## 状态

已完成 Planner 最小行为增强。

本次没有重做 P1-1 的 `SimplePlanner`，只在原有 plan/trace 基础上补齐：

- plan 注入 prompt
- 工具失败时一次性 replan
- step 推进从“每轮推进”改为“成功工具弱匹配后推进”

默认 `react` 模式不变。

## 改动范围

### `src/runtime/planner.py`

新增：

- `Plan.active_step()`
- `Plan.current_step_title()`
- `Plan.to_prompt_text()`
- `Plan.maybe_replan(reason)`
- `Plan.advance_after_tools(tool_names, success_count)`

行为：

- `to_prompt_text()` 生成可注入 system message 的计划摘要。
- `maybe_replan()` 只对当前 active step 做一次轻量标题修订，不增加步骤、不循环 replan。
- `advance_after_tools()` 只有在工具成功且与当前 step title 弱匹配时推进。

### `src/runtime/loop.py`

在 `plan_act` 模式下：

- 创建 plan 后追加一条 system message：

```text
Current execution plan...
```

- 工具失败时最多触发一次 `plan_replanned` 事件。
- 每轮工具执行后用 `advance_after_tools()` 推进 plan。

## 非目标

本次没有做：

- 额外 LLM planner 调用
- 多次 replan
- DAG planner
- plan 质量评分
- expected_check 失败后的 eval-time replan

## 验证

Focused 测试：

```bash
C:\Users\Administrator\.conda\envs\coding-harness\python.exe -m pytest tests/test_planner.py tests/test_planner_loop_sync.py -q --basetemp .pytest_tmp
```

结果：

```text
9 passed
```

全量测试：

```bash
C:\Users\Administrator\.conda\envs\coding-harness\python.exe -m pytest tests -q --basetemp .pytest_tmp
```

结果：

```text
107 passed
```

## 回退方式

如需回退：

1. 从 `src/runtime/planner.py` 移除本记录新增的方法。
2. 从 `src/runtime/loop.py` 移除 plan system message 注入、`plan_replanned` 事件和 `advance_after_tools()` 调用。
3. 恢复为 `plan.advance_after_turn()`。
4. 删除 `tests/test_planner.py` 和 `tests/test_planner_loop_sync.py` 中新增断言。
