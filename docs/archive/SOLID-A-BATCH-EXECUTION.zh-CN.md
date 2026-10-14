# Solid A 层批次 · 执行清单（Composer 2.5 用）

> **定位**：本文是给执行者（Composer 2.5）的可直接落地清单。决策点已锁定，按顺序做即可。  
> **上游**：`docs/SOLID-ROADMAP.zh-CN.md`（方向与 ABC 分层）。  
> **环境**：`C:\Users\Administrator\.conda\envs\coding-harness\python.exe`；测试加 `--basetemp $env:TEMP\coding-harness-pytest`。  
> **基线**：当前全量 **108 passed**；改动后必须保持全绿，再跑相关真实 eval。

---

## 0. 已锁定决策（不要再改）

| 决策点 | 选定方案 | 说明 |
|--------|----------|------|
| P1-1 plan 刷新方式 | **B：每步追加一条消息**（非替换原 system） | 每步 `plan_updated` 后向 `messages` **append** 一条计划更新消息；不删旧的 |
| 刷新消息的 role | **`system`**（而非 `developer`） | DeepSeek OpenAI-compatible 端点对 `developer` role 支持不稳定；用 `system` 已验证可用。内容前缀标注 `Plan update:` 表明是计划更新。若日后切 OpenAI 官方可改 `developer` |
| plan_act 公平对照 | **单变量：只改 mode** | `plan_act_permissive.yaml` = `baseline.yaml` 原样 + `runtime.mode: plan_act` + `runtime.planner.enabled: true`。**策略、工具、context 全部与 baseline 一致**，只隔离 Planner 效应 |

---

## 1. 执行顺序（5 项）

1. P1-1 A — plan 每步刷新 + permissive 对照 config
2. P1-3 A — 修 `medium_subagent_cross_file` + child 输出校验
3. P0-2 A — 裁判失败明细
4. P0-4 A — plan_act / stream trace 示例
5. P2-1 A — `LLMErrorKind` 驱动 retry + request metadata

每完成 1 项：跑全量 pytest → 绿 → 在 `docs/SOLID-ROADMAP.zh-CN.md` 对应行标完成日期 + 证据路径。

---

## 2. P1-1 A：plan 每步刷新 + permissive 对照

**改 `src/runtime/loop.py`**

- 在 `run()` 的 OBSERVING 段、`plan_updated` 事件发射处之后，向 `messages` **append**：
  ```python
  messages.append({
      "role": "system",
      "content": "Plan update: " + plan.to_prompt_text(),
  })
  ```
- 触发条件：`plan` 存在且本步发生了 `advance_after_tools` 推进 **或** `maybe_replan`。无变化的步可跳过 append（避免无谓膨胀）。
- 保留 run 开头那条初始 plan system 注入不变。

**新建 `configs/plan_act_permissive.yaml`**

- 复制 `configs/baseline.yaml` 全文；**仅**改：
  ```yaml
  runtime:
    mode: plan_act
    planner:
      enabled: true
  ```
- 其余（`policy.command.allow_all: true`、tools、context）与 baseline 完全一致。

**测试**：`tests/test_planner_loop_sync.py` 新增断言——plan 推进后 `messages` 中出现至少 1 条 `Plan update:` 开头的 system 消息（用 `MockLLMClient` 多步序列）。

**验收 eval**（API）：
```bash
python scripts/run_eval.py --dataset datasets/repo_tasks.json --configs baseline plan_act_permissive --runs 3
```
- 这是 **真正的单变量 Planner A/B**；报告写入 `reports/examples/baseline_vs_plan_act_permissive_real.md`，并注明「已消除策略 confound」。

---

## 3. P1-3 A：修 subagent 任务 + child 输出校验

**问题**：`medium_subagent_cross_file` 裁判要求改 `parser.py`（含 `email`、不含 `"mail"`），但 Agent 之前修了 `service.py`，FAIL。

**改 `tests/fixtures/repos/medium_subagent_cross_file/`**（先读现有 fixture 确认 bug 真实位置）

- 确认 bug 应当落在 `parser.py`；若 fixture 设计使「合理修法在 service.py」，则 **调整任务描述或裁判** 使二者一致。优先改任务描述明确「fix in parser.py」，而非放宽裁判。
- 目标：让一个正常 Agent（plan_act 或 baseline）能 PASS。

**改 `src/tools/subagent.py`**：child 返回 JSON 增加轻量 schema 校验

- 若 `findings` 为空或缺 `summary`，在返回 payload 标 `"schema_ok": false`，不抛异常（保持只读、非阻断）。
- 父 trace 的 `subagent_traces` 记录 `schema_ok`。

**测试**：`tests/test_subagent.py` 增 1 例——child 输出缺字段时 `schema_ok=False`。

**验收 eval**（API）：
```bash
python scripts/run_eval.py --dataset datasets/repo_tasks.json --configs subagent_readonly --runs 3
```
- 目标：`medium_subagent_cross_file` 至少在多数 run PASS；更新 `reports/examples/subagent_readonly_repo_tasks_real.md`。

---

## 4. P0-2 A：裁判失败明细

**问题**：`_check_expected` 只返回 `bool`，`multi_assert` 失败时看不出是哪条 assert 挂了。

**改 `src/eval/runner.py`**（非侵入式）

- 新增 `_explain_expected(workspace, result, expected) -> tuple[bool, list[str]]`：复用现有各 `_check_*`，对失败的 assert 收集人类可读原因（如 `"command_success failed: python -m pytest -q (exit=1)"`、`"file_contains: missing keyword 'email' in parser.py"`）。
- `multi_assert` 逐条记录失败项。
- 保留原 `_check_expected` 供向后兼容；让 runner 主路径调用 `_explain_expected`，把 `failures` 写入该任务的结果/trace metadata。

**改 `src/eval/report.py`**：失败任务表增加「Failure Detail」列或在 per-task 区列出失败 assert 原因。

**测试**：`tests/test_runner.py` 增 1 例——`multi_assert` 部分失败时 `failures` 含具体条目。

**验收**：跑任意已有 eval，报告里失败任务能看到「哪条 assert + 为什么」。

---

## 5. P0-4 A：trace 示例补全

**plan_act events 示例**

- 用 `plan_act.yaml`（或 permissive）+ `lifecycle_events: true` 跑 1 个会触发工具失败的 repo 任务，取 events JSONL，脱敏后存 `docs/examples/plan_act_events_redacted.jsonl`（含 `plan_created` / `plan_updated` / 至少一次 `plan_replanned`）。

**stream events 示例**

- 用 `configs/debug.yaml`（`llm_stream_events: true`）跑 1 个简单任务，取含 `message_delta` / `tool_call_delta` / `llm_stream_done` 的 events 片段，脱敏存 `docs/examples/llm_stream_events_redacted.jsonl`。

**改 `docs/INTERVIEW-DEMO.zh-CN.md`**：在 Agent 能力段引用这两个示例文件，各加一句讲法。

**验收**：两个 JSONL 每行可 `json.loads`；INTERVIEW-DEMO 有引用。

---

## 6. P2-1 A：错误分类驱动 retry + request metadata

**改 `src/runtime/retry.py`**

- `RetryPolicy.should_retry` 优先用异常的 `kind`（若为 `LLMError`）：
  ```python
  from src.llm.client import LLMError, LLMErrorKind
  if isinstance(error, LLMError):
      return error.kind.value in self.config.retry_on   # timeout/http/parse/unknown
  ```
- 保留旧字符串 `_classify` 作为非 `LLMError` 的回退。
- 注意：`retry_on` 现有值是 `["timeout", "model_error"]`；新增对 `LLMErrorKind` 值（`timeout`/`http`/`parse`/`unknown`）的匹配。`http` 5xx 可重试、4xx 不重试可作为 B 层细化，本次先按 kind 名匹配。

**request metadata trace**

- `AgentLoop` 在 `llm_complete` 事件已记 `elapsed_ms`；补 `model`（`self.llm.model`）与 `usage` token 字段到该事件 payload。

**测试**：`tests/test_llm_client.py` 或新测——`should_retry(LLMError(kind=TIMEOUT))` 为真、`PARSE` 不在 `retry_on` 时为假。

**验收**：`pytest tests -q` 全绿；retry 行为对 `LLMError.kind` 生效。

---

## 7. 收尾

- 全部完成后：全量 `pytest tests -q` 绿；更新 `docs/SOLID-ROADMAP.zh-CN.md` 各行状态。
- 新增一份 `docs/changes/SOLID-A-BATCH-CLOSEOUT.zh-CN.md` 记录实际改动、测试数、eval 报告路径。
- eval 数字一律用 `--runs 3` 并在报告声明是否还有 confound。

---

## 8. 给 Composer 的一句话起点

> 按 `docs/SOLID-A-BATCH-EXECUTION.zh-CN.md` 顺序执行 A 层 5 项。决策已锁定（plan 每步 append system 消息、permissive 只改 mode）。每项做完跑全量 pytest 保持绿，再跑标注的真实 eval；conda 解释器见文档抬头。
