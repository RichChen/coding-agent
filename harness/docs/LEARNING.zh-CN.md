# 学习指南：如何读透 coding-harness

面向希望**精通**本仓库的开发者（含实习项目深度准备）。英文主 README 见 [README.md](../README.md)，中文概览见 [README.zh-CN.md](../README.zh-CN.md)。

---

## 1. 先建立「整体心智模型」

用一句话概括本仓库：

> **在模型不可信的前提下，用策略层 + 沙箱 + 预算把工具调用约束住，并用同一套评测脚本证明「收紧后」指标如何变化。**

三条线并行存在，读代码时随时问自己「当前这行属于哪条线」：

| 线 | 职责 | 主要目录 |
|----|------|----------|
| **运行时** | plan → act → observe 循环、消息拼装、停止条件、Hook 管线 | `src/runtime/`、`src/llm/` |
| **安全与资源** | 路径越界、命令策略、文件大小限制、步数/超时 | `src/policy/` |
| **观测与评测** | JSONL 轨迹、生命周期事件、批量任务、报告与指标 | `src/tracing/`、`src/eval/` |
| **装配与配置** | 统一工厂、Pydantic 校验、YAML → AgentLoop | `src/harness/`、`src/config/` |

---

## 2. 推荐阅读顺序（三遍法）

### 第一遍：跟着「一次请求」走主线（约 1～2 小时）

按调用链阅读，**不要**在第一遍里深入每个工具实现细节。

1. `scripts/run_single.py`  
   - 看：如何加载 YAML、`sys.path`、如何组装 `LLMClient` / `Sandbox` / `Budget` / `ToolRegistry` / `AgentLoop`。  
   - 目标：回答「入口如何把配置变成可运行的 `AgentLoop`？」

2. `src/runtime/loop.py`  
   - 看：`run()` 里的 `while True`：何时调 `llm.chat`、何时认为「最终答案」、何时执行 `tool_calls`、如何把 `ToolResult` 塞回 `messages`。  
   - 看：`EventBus` 生命周期事件（`run_start` / `llm_complete` / `tools_complete` / `run_end`）在何处 emit、如何自动 open/close。  
   - 看：`BudgetExhausted` 与 `FailureReason` 如何映射到返回结果。  
   - **注意**：system prompt 已外置到 `prompts/system_default.md`（通过 `runtime.system_prompt_path` 配置），`loop.py` 中只剩一行 fallback 常量。

3. `src/llm/client.py`  
   - 看：如何拼接 `POST {base_url}/chat/completions`，以及如何把响应解析成 `LLMResponse` / `ToolCall`。  
   - 目标：换厂商时只动这一层需要改什么。

4. `src/tools/base.py` + `src/tools/registry.py`  
   - 看：`ToolResult.to_message()` 为何长成 OpenAI 要求的 `role: tool` 形状。  
   - 目标：加一个新工具最少要改哪些类。

5. `src/harness/factory.py`  
   - 看：`load_config` 如何用 Pydantic `HarnessConfig` 校验 YAML，`build_agent` 如何装配 `LLMClient` / `Sandbox` / `Budget` / `ToolRegistry` / `AgentLoop`（以及可选的 `MicroCompactHooks` / `EventBus`）。  
   - 目标：理解为何两个 script 都从这里取 agent，不再各自拼装。

**第一遍结束自检**：能在纸上画出「用户一句话 → 第 k 轮 LLM → 工具 → 下一轮 LLM」的方框图。

---

### 第二遍：安全、资源与失败语义（约 1～2 小时）

5. `src/policy/sandbox.py`  
   - 重点：`resolve()` 如何用 `workspace_root` + `relative_to` 防止路径越狱。  
   - 对照测试：`tests/test_sandbox.py`。

6. `src/policy/rules.py`  
   - 重点：先黑名单、再 `allow_all` / 白名单前缀的判定顺序。  
   - 对照：`tests/test_policy.py`。

7. `src/policy/budget.py`  
   - 重点：`start_step` 与 `check_step_timeout` 分工；谁在循环的什么位置被调用（回到 `loop.py`）。

8. `src/runtime/retry.py`  
   - 重点：`RetryPolicy.execute` 与 `_classify` 的粗糙启发式；思考若接生产应如何改进（不急着改代码）。

9. `src/policy/limits.py` + `src/runtime/compact.py`  
   - `limits.py`：`file_size_limit_bytes` 如何在校验文件大小后阻止超大文件读写。  
   - `compact.py`：Layer-1 micro-compact 如何压缩旧 tool 消息（保留最近 N 条 + `read_file` 关键结果），通过 `LoopHooks` 注入 `before_llm`。

**第二遍结束自检**：能口头解释「为什么 policy 拒绝不算模型失败，而是 `ToolResult` 失败 + 可能记 policy_block」。

---

### 第三遍：评测闭环与可观测性（约 1～2 小时）

9. `src/eval/runner.py`  
   - 重点：`EvalRunner._run_task` 如何准备 `initial_files`、调用 `agent.run`、再用 `expected.type` 四种判定器（`file_contains` / `command_output` / `keywords_in_answer` / `file_exists`）打分。  
   - 思考：`success`（agent 是否正常结束）与 `expected_check`（任务是否做对）为何拆开。

10. `src/eval/metrics.py` + `src/eval/report.py`  
    - 重点：`aggregate_metrics` 里各类失败计数如何从 `TaskResult` / `FailureReason` 汇总；报告 CSV 含 `trace_file` 列可定位每个任务的 JSONL。

11. `src/tracing/logger.py` + `src/tracing/models.py` + `src/tracing/events.py`  
    - 重点：`TraceLogger` 的 step 级 JSONL 与 `EventBus` 的 lifecycle 级 JSONL 各自记录什么、有何不同。  
    - 参考 `docs/examples/demo_baseline_synthetic.jsonl` 对照阅读。

12. `scripts/run_eval.py` + `configs/debug.yaml`  
    - 重点：`agent_factory` 如何根据 dict 配置拼出 agent；`debug.yaml` 与 baseline/hardened 的区别（`lifecycle_events: true` + `read_events` 工具）。

**第三遍结束自检**：能解释「改 hardened 里一条命令白名单，最可能影响报告里哪一列」。

---

## 3. 测试作为「活文档」的阅读顺序

读完主逻辑后，用测试巩固（**从短到长**）：

1. `tests/test_sandbox.py`  
2. `tests/test_policy.py`、`tests/test_timeout.py`  
3. `tests/test_tools.py`（含文件大小限制、输出截断、edit_file）  
4. `tests/test_compact.py`（micro-compact + EventBus）  
5. `tests/test_runner.py`（评测指标与报告）  
6. `tests/test_agent_loop.py`（Mock LLM 集成测试，无需 API Key）

本地运行：

```bash
pytest tests/ -v
```

单测失败时，优先怀疑：**路径分隔符（Windows）**、**环境变量未加载**、**异步与 `asyncio.run` 嵌套**。

---

## 4. 自测小题（建议手写答案再对代码）

> 下面为对照当前代码写的参考答案；改 `loop.py` / `budget.py` / `metrics.py` 后请重新核对。

### 1. 若模型返回 `tool_calls` 但其中一个 name 未注册，消息历史会如何增长？

**不会中断循环**，历史会按 OpenAI tool 对话格式完整拉长，模型下一轮能看到失败信息。

一轮含未注册工具时的 `messages` 变化（见 `loop.py` 约 188–228 行）：

1. **先追加一条 `assistant` 消息**（`role: assistant`），`content` 为模型文本，`tool_calls` 数组里**仍包含**未注册的那个 name（与 LLM 原始响应一致）。
2. **再对每个 `tool_call` 顺序追加一条 `tool` 消息**（`ToolResult.to_message()`）：
   - `registry.get(name)` 为 `None` 时，构造 `success=False`、`error="Unknown tool: {name}"` 的 `ToolResult`；
   - `tool_failures` 加 1；
   - `messages.append(tr.to_message())` → `role: tool`，`content` 为 `Error: Unknown tool: ...`，`tool_call_id` 与 assistant 里对应 id 对齐。

因此：若一轮有 3 个 `tool_call`、其中 1 个未注册，则本轮结束后 messages 净增 **1 条 assistant + 3 条 tool**（未注册那条也是标准 tool 错误消息，不是异常抛出）。循环继续进入下一轮 `THINKING`，**不会**把 `failure_reason` 设为 `TOOL_ERROR`（agent 仍可继续尝试）。

---

### 2. `Budget` 的「单步超时」量的是什么？

**量的是「上一轮 `start_step()` 到本轮循环开头 `check_step_timeout()`」的墙钟时间，包含该轮 LLM 调用与工具执行，不是「仅两次 LLM 之间、不含工具」。**

对照 `budget.py` 与 `loop.py`：

| 调用点 | 位置 | 作用 |
|--------|------|------|
| `check_step_timeout()` | `while True` **最开头**（约 121 行） | 用 `_last_step_start` 检查是否超过 `step_timeout_seconds` |
| `start_step()` | 进入 `THINKING`、**调 LLM 之前**（约 125 行） | `_step_count += 1`，并把 `_last_step_start = now` |

时序（第 k 轮，k≥2）：

1. 循环开头 `check_step_timeout()` → 计时起点是**上一轮**的 `start_step()`（上一轮 LLM 开始前）。
2. 该间隔覆盖：上一轮 **LLM 等待 + 全部 tool 串行执行 + 写 trace**，直到本轮检查为止。
3. 通过后 `start_step()` 重置 `_last_step_start`，再发起本轮 LLM。

**注意**：超时只在**下一轮循环开头**检查，工具执行再久也不会在中途打断；`StepRecord.elapsed_ms` 只统计 **LLM 段**（`step_start` 在 `llm.chat` 前），与 budget 单步超时口径不一致。

---

### 3. `EvalRunner` 的 `steps=len(result.steps)` 与 loop 里的「一步」是否一致？

**在「正常跑完」时大体一致，但语义不同，边界情况会让 metrics 产生偏差。**

| 概念 | 含义 |
|------|------|
| **`len(result.steps)`** | `StepRecord` 条数：每次「有 tool_calls 的 LLM 轮」记 1 条（`ACTING`），或最终无工具的一轮记 1 条（`DONE`），或 LLM 异常记 1 条（`FAILED`） |
| **`Budget._step_count`** | 每次循环开头 `start_step()` 加 1，**含**「最后一轮只出最终答案、无工具」那次 |

成功路径示例（3 轮工具 + 1 轮最终答案）：`len(steps)=4`，`budget` 也调了 4 次 `start_step()` → **`avg_steps` 与预算步数对齐**。

**不一致 / 偏差来源**：

1. **一步多工具**：多个 `tool_call` 仍只产生 **1** 条 `StepRecord`；`avg_steps` 偏低，无法反映工具调用次数。
2. **预算耗尽**：`check_step_timeout` 或 `start_step` 抛 `BudgetExhausted` 时，**当轮可能尚未** `steps.append` → `len(steps)` 可小于已消耗的 budget 步数。
3. **`StepRecord.step` 字段**：`state.step_number` 在每轮工具循环结束后 `+= 1`（`loop.py` OBSERVING 阶段末尾），trace 中 `step` 与 `len(steps)` **对齐**（0, 1, 2, ...）。
4. **`policy_block` 已对齐**：`aggregate_metrics` 改为 `sum(r.policy_blocks for r in results)`，直接汇总每次运行中工具执行时 `policy_blocks` 计数器（含已拒绝的命令和越权路径），不再依赖 `failure_reason` 枚举。

---

### 4. `tool_failure_rate` 如何保证精确？

**当前实现（`metrics.py`）**：`AgentRunResult` 包含 `total_tool_invocations`（`loop.py` 中每次 `tool.execute` +1，含 unknown tool）。`aggregate_metrics` 直接：

```text
tool_failure_rate = sum(tool_failures) / sum(total_tool_invocations) × 100
```

分母精确反映真实工具调用次数，不再依赖启发式估算。`AgentRunResult` 的返回在三个路径（正常结束 / LLM 错误 / BudgetExhausted）都携带 `total_tool_invocations`，`EvalRunner._run_task` 再透传至 `TaskResult`。

**局限（依然存在）**：
- 「工具失败」是二进制（`ToolResult.success`），**不区分严重程度**（超时 vs 文件不存在 vs 沙箱拒绝）。
- `policy_blocks` 通过 tool error 中的 `"policy"` 关键词识别（`loop.py`），属于启发式；若未来工具错误消息不含该词会漏计。
- 不同任务间 `total_tool_invocations` 方差大（有的 1 轮结束、有的 10 轮），`tool_failure_rate` 在少量任务下不稳定，**宜配合 per-task 明细**一起看。

---

**速记对照**

| 题号 | 一句话 |
|------|--------|
| 1 | assistant + 每条 tool 各一条消息；未注册 → tool 错误消息，循环继续 |
| 2 | 单步超时 = 上轮 start_step → 本轮 check，**含**工具；不在工具执行中途打断 |
| 3 | 正常结束时 len(steps)≈budget 步数；多工具/预算中断会偏差；step_number 每轮递增已对齐 |
| 4 | `total_tool_invocations` 精确分母；局限在 failure 语义不区分严重程度、policy_blocks 关键词启发式 |

---

## 5. 调试建议（实操）

- **先单任务**：`run_single.py` + `hardened`/`baseline`/`debug` 切换，确认能出最终答案或稳定失败。`debug` 配置会生成 `events_*.jsonl` 便于排查循环内部。  
- **再小数据集**：从 `mini_tasks.json` 抽 3 条任务跑 `run_eval`，确认 `reports/`、`traces/` 落盘。  
- **API 问题**：看 `LLMError` 文本与 HTTP body 截断；检查 `base_url` 是否含 `/v1`。  
- **加日志**：优先在 `AgentLoop.run` 的 phase 边界打结构化日志，避免在 `LLMClient` 里刷屏。

---

## 6. 推荐的「精通」标准

你至少应能做到下面任意 **4** 条（实习面试足够展开）：

- 不看文档，5 分钟内讲清 `AgentLoop` 主循环（含 Hook 注入点与 EventBus 生命周期事件）。  
- 加一个仅允许 `pytest` 子集命令的白名单策略，并解释与 `hardened.yaml` 的差异。  
- 为数据集增加一种新的 `expected.type`（现已有 4 种参考实现：`file_contains` / `command_output` / `keywords_in_answer` / `file_exists`），并改 `runner` + 测试。  
- 把 `TraceLogger` 接到一次真实 run，并能用 `jq` 或编辑器从 JSONL 里抽出某次 `tool_calls`；或阅读 `docs/examples/demo_baseline_synthetic.jsonl` 理解轨迹结构。  
- 修改 `prompts/system_default.md` 并观察 agent 行为变化，解释 prompt 与代码解耦的好处。  

---

## 7. 扩展方向（按投入从少到多）

- ~~Mock `LLMClient`，让 CI 在无 API Key 时仍跑通集成测试。~~ ✅ 已完成（`tests/fixtures/mock_llm.py` + `tests/test_agent_loop.py`，5 个集成测试）。  
- ~~将 `SYSTEM_PROMPT` 外置为模板文件，做多语言 / 多场景实验。~~ ✅ 已完成（`prompts/system_default.md`，通过 `runtime.system_prompt_path` 配置）。  
- 引入 Docker 或 `nsjail` 类隔离（保留当前纯路径沙箱为 fallback）。  
- 对接真实 SWE-bench 子集（注意许可证与成本）。

---

若你按本指南仍卡在某文件，把**文件名 + 行号 + 你的理解**记下来，再对照 `loop.py` 重读一遍，通常卡点会在「消息历史与 OpenAI tool 消息格式」一处。
