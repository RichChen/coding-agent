# Solid C 批次 · 执行清单（Composer 2.5 用）

> **定位**：A 批次（5 项）、B 批次（5 项）已完成（见 `docs/changes/SOLID-A-BATCH-CLOSEOUT.zh-CN.md`、`SOLID-B-BATCH-CLOSEOUT.zh-CN.md`，当前 **131 passed**）。本文是 C 批次的可直接落地清单，决策已锁定，按顺序做即可。  
> **上游**：`docs/SOLID-ROADMAP.zh-CN.md`（方向与 ABC 分层；§3 表格已带完成标注）。  
> **环境**：`C:\Users\Administrator\.conda\envs\coding-harness\python.exe`；测试加 `--basetemp $env:TEMP\coding-harness-pytest`。  
> **基线**：当前全量 **131 passed**；每项改动后必须保持全绿，再跑相关真实 eval。

---

## 0. 本批次主线（为什么做这些）

B 批次后出现关键观察：**12 任务集 baseline 已达 94.4%、plan_act 100%——接近天花板**，继续在该集上比较会「撞顶」失去区分度。C 批次重心从「加固已有」转向 **拉开区分度 + 补最后的工程深度 + 把 compact 从『无回归』推进到『有收益』**。

---

## 1. 已锁定决策（不要再改）

| 决策点 | 选定方案 | 说明 |
|--------|----------|------|
| 难任务来源 | **A：自造 3–4 个 hard** | 可控、无外部依赖、当周可完成。不接入 SWE-bench（那是 P0-1 C 层，留后） |
| P2-1 真 SSE 是否现在做 | **B：仍 defer 真 SSE** | 先做 cancel token + retry 5xx/4xx 细分（小而实用）；真 SSE 边际收益递减 |
| 是否引入成本维度 | **A：report 加 token/耗时/估算$列** | 产品思维加分，改动小 |

---

## 2. 执行顺序（5 项）

1. P0-1 C — 自造 3–4 个 hard 难任务（拉开区分度）
2. P1-2 A — token 估算触发 compact + 在新难任务证明 compact 提升
3. P2-1 C（部分）— cancel token + retry 5xx/4xx 细分
4. P0-3 B — 成本维度（token/耗时/估算$）+ per-task 热力图
5. P0-2 收尾 — flaky 检测接入真实多 run 报告

每完成 1 项：跑全量 pytest → 绿 → 在 `docs/SOLID-ROADMAP.zh-CN.md` §3 对应行 + §4 列表标完成日期与证据路径。

---

## 3. P0-1 C：自造 3–4 个 hard 难任务

**目标**：制造 baseline 明显做不满（期望 baseline 50–80%）、但 plan_act / compact 能体现优势的任务，恢复区分度。

**新增任务 + fixture**（`datasets/repo_tasks.json`、`tests/fixtures/repos/`）

1. `hard_long_context_chain`：需顺序阅读 5+ 文件、跨文件追踪一个值的流向后才能定位修复点（压上下文，配合 P1-2 验证 compact）。
2. `hard_multi_step_locate`：错误日志 → 定位 → 修复 → 回归，需 ≥ 3 步且中途可能失败（配合 plan_act replan）。
3. `hard_regression_fix`：修 A 处不能破坏 B 处现有测试（多文件约束 + 完整 pytest 校验）。
4. （可选第 4 个）`hard_refactor_keep_green`：小重构后保持全部测试通过。

**约束**

- 每个 fixture 小型、纯本地、无网络/第三方依赖。
- 每个新任务**必须**配 `.oracle/`（参考解 + 必要 `final_answer.txt`），并通过 `scripts/check_dataset_oracle.py`。
- 裁判用 `multi_assert`（含 `command_success` 跑 pytest + `python_defines`/`file_contains`）。
- 难度标 `hard`，tags 含可区分维度（如 `long-context` / `multi-step` / `regression`）。

**测试 / 验收**
```bash
python scripts/check_dataset_oracle.py          # 新任务 oracle 必过
python scripts/run_eval.py --dataset datasets/repo_tasks.json --configs baseline --runs 3
```
- 期望：新 hard 任务上 baseline 成功率明显 < 100%（恢复区分度）。
- 更新 `reports/examples/` 新增一份「难任务集 baseline 表现」报告，注明区分度恢复。

---

## 4. P1-2 A：token 估算触发 compact + 证明收益

**现状**：`MicroCompactHooks` 每次 `before_llm` 都跑 compact；保留规则（最近失败 + 最近修改结果）已在 `_protected_tool_indices` 实现。**缺**：按 token 预算的触发门。

**改 `src/runtime/compact.py` + `src/runtime/context.py`**

- 新增轻量 token 估算：`estimate_tokens(messages) ≈ total_chars / 4`（无需 tokenizer 依赖；注释说明是估算）。
- `MicroCompactHooks` 增 `token_threshold: int | None = None`：
  - `None` → 保持现有「每次都压」行为（向后兼容）。
  - 设值 → 仅当 `estimate_tokens(messages) > token_threshold` 才执行 compact；否则跳过（`did_compact=False`）。
- `ContextStats` 增 `estimated_tokens_before` / `estimated_tokens_after`（可观测）。
- `context_compacted` 事件带上 token 估算字段。

**Schema / config**

- `RuntimeContextConfig`（`src/config/schema.py`）增 `compact_token_threshold: int | None = None`。
- `context.py` 的 `ContextPolicyConfig.from_runtime_config` 透传；`build_context_hooks` 传入 `token_threshold`。
- 新建 `configs/context_compact_threshold.yaml`（micro_compact: true + 合理 threshold，如 6000）。

**测试**（`tests/test_compact.py`）

- threshold 未达 → 不 compact（`did_compact=False`）。
- threshold 超过 → compact 生效。
- `estimated_tokens_*` 字段存在且合理。

**验收 eval**（API，关键证据）
```bash
python scripts/run_eval.py --dataset datasets/repo_tasks.json --configs baseline context_compact_threshold --runs 3
```
- **目标**：在 P0-1 C 新增的 `hard_long_context_chain` 等长上下文任务上，compact 版 **成功率 ≥ baseline 且 token/字符显著下降**——从「无回归」推进到「有收益」。
- 写入 `reports/examples/baseline_vs_context_compact_threshold_real.md`，明确标注是否首次观察到 compact 正收益。

---

## 5. P2-1 C（部分）：cancel token + retry 5xx/4xx 细分

**retry 5xx/4xx 细分**（`src/llm/client.py` + `src/runtime/retry.py`）

- `LLMError` 增可选 `status_code: int | None`（HTTP 错误时填）。
- `client.py` 抛 `LLMErrorKind.HTTP` 时带上 `status_code`。
- `RetryPolicy.should_retry`：对 `LLMError(kind=HTTP)`，仅当 `status_code` 为 5xx（或 429）时可重试；4xx（除 429）不重试。
- `retry_on` 语义文档化：`http` 表示「可重试的 http」，由 status_code 细分决定。

**cancel token**（`src/runtime/loop.py` + `src/llm/client.py`）

- `AgentLoop.run` 接受可选 `cancel_event: asyncio.Event | None`。
- 每轮 THINKING/ACTING 前检查 `cancel_event.is_set()`；若已取消 → 优雅结束，返回 `AgentRunResult(success=False, failure_reason=...)`，发 `run_end(reason="cancelled")` 事件。
- 新增 `FailureReason.CANCELLED`。
- `client.chat` 的 httpx 调用包在可被取消的 task 中（asyncio 原生取消即可，无需改 httpx）。

**测试**

- `tests/test_llm_client.py`：`should_retry(LLMError(HTTP, 503))` 为真；`(HTTP, 404)` 为假；`(HTTP, 429)` 为真。
- `tests/test_agent_loop.py`：预置 `cancel_event` 已 set → run 立即返回 `CANCELLED`，不调用 LLM。

**验收**
```bash
python -m pytest tests/test_llm_client.py tests/test_agent_loop.py -q --basetemp $env:TEMP\coding-harness-pytest
```

---

## 6. P0-3 B：成本维度 + per-task 热力图

**成本列**（`src/eval/metrics.py` + `src/eval/report.py`）

- `EvalMetrics` 增 `avg_tokens` 已有；新增报告列：总 token、平均 token/任务、平均耗时已有。
- 新增「估算成本」：可配置单价（如 `cost_per_1k_tokens`，默认占位 0 并注明「按需填」），report 算 `est_cost = total_tokens/1000 * price`，标注是估算。
- 单价放 `scripts/run_eval.py` 的可选 `--cost-per-1k` 参数（默认 0 → 显示 `n/a`）。

**per-task 热力图**（`src/eval/report.py`，文本版）

- 重复 run 下，新增「Per-Task Pass Matrix」段：行=task，列=run，单元格 `P`/`F`，行尾 `passes/runs`。
- 纯 Markdown 表格即可（不需要图像）。

**测试**（`tests/test_runner.py`）

- 成本列：给定 token 与单价，`est_cost` 计算正确；单价 0 → `n/a`。
- pass matrix：构造 3 run 假数据，矩阵行列正确。

**验收**
```bash
python scripts/run_eval.py --dataset datasets/repo_tasks.json --compare --runs 3 --cost-per-1k 0.5
```
报告含成本列 + per-task pass matrix。

---

## 7. P0-2 收尾：flaky 检测接入真实多 run

**现状**：B 批次已实现 Unstable Tasks 报告段（基于 repeated metrics）。本项是**接入真实跑分 + 文档化稳定性结论**。

**操作**

- 用一个会偶发失败的任务集（含 P0-1 C 的 hard 任务）跑 `--runs 5`，让 flaky 检测真实触发。
- report 的 Unstable Tasks 段确认列出 `0 < passes < runs` 的任务。
- 在 `docs/INTERVIEW-DEMO.zh-CN.md` 或 `FAILURE-CASES.zh-CN.md` 增一段「稳定性叙事」：哪些任务 flaky、推测原因（模型方差 / 多步累积）、如何用多 run + CI 表述结论。

**验收**
```bash
python scripts/run_eval.py --dataset datasets/repo_tasks.json --configs baseline --runs 5
```
报告 Unstable Tasks 段非空（若恰好全稳定，换更难任务或加 run 数）；面试稿有稳定性段落。

---

## 8. 收尾

- 全部完成后：全量 `pytest tests -q` 绿；更新 `docs/SOLID-ROADMAP.zh-CN.md` §3 表格 + §4 列表（标 C 批次完成）。
- 新增 `docs/changes/SOLID-C-BATCH-CLOSEOUT.zh-CN.md`：实际改动、测试数、eval 报告路径、未做项。
- eval 数字一律 `--runs N` 并在报告声明 confound 与显著性。
- **重点交付**：P1-2 的「compact 正收益」证据（§4）与 P0-1 的「区分度恢复」证据（§3）是本批次最大亮点，务必产出报告。

## 9. 不在本批次（保持 defer）

- 真 SSE streaming（P2-1 B/C）
- L2 LLM 摘要（CODEX 缺口 2）
- 多 worker / 递归 / 可写子 Agent（CODEX 缺口 3–4）
- 外部 benchmark 接入（P0-1 C 大版）
- P2-2 Docker runner（P2-2 B）
- 多模型矩阵 eval（P0-3 C）

## 10. 给 Composer 的一句话起点

> 按 `docs/SOLID-C-BATCH-EXECUTION.zh-CN.md` 顺序执行 C 批次 5 项。决策已锁定（自造 hard 任务、token 触发 compact、cancel+retry 细分、加成本维度、真 SSE 仍 defer）。每项做完跑全量 pytest 保持绿（基线 131），再跑标注的真实 eval；conda 解释器见文档抬头。本批次最大亮点目标：P1-2「compact 正收益」+ P0-1「区分度恢复」两份 eval 证据。完成后更新 `docs/SOLID-ROADMAP.zh-CN.md` §3/§4 标注。
