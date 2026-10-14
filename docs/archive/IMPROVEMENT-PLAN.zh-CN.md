# Coding Harness 最终改进方案

> 目标：把当前项目从“单 Agent harness demo”升级为更适合国内互联网顶尖企业 Agent 研发实习面试展示的工程项目。
>
> **实施状态（2026-06-25）**：P0-1～P0-4、P1-1、P1-2、P1-3 已完成（含收尾补强）；P2-1 已完成最小雏形；P2-2 仍为待办。各阶段细节见 `docs/changes/` 下对应记录。
>
> **未来改进方向（Solid 化）**：见 `docs/SOLID-ROADMAP.zh-CN.md` —— 对每个模块按 A/B/C 分层列出从「最小交付」升级到「Solid」的具体项，并记录 eval confound。本文回答「做了什么」，路线图回答「还能更 solid 在哪」。

---

## 0. 当前进度快照

| 项 | 状态 | 交付物 | 已知缺口 |
|---|---|---|---|
| P0-1 分层 repo 评测集 | ✅ 已完成 | `datasets/repo_tasks.json`（9 任务，含 1 个 subagent 任务）、`tests/fixtures/repos/` | — |
| P0-2 裁判系统 | ✅ 已完成 | `file_not_contains`、`command_success`、`json_equals`、`regex_match`、`multi_assert`、`yaml_contains`；`command_output` 默认校验 exit code；`mini_tasks` 清洗 5 项 | — |
| P0-3 多次运行统计 | ✅ 已完成 | `--runs N`、mean/std 报告与 CSV、**bootstrap 95% CI** | — |
| P0-4 展示材料 | ✅ 已完成 | `reports/examples/`、`docs/FAILURE-CASES.zh-CN.md`、`docs/INTERVIEW-DEMO.zh-CN.md`、`docs/examples/real_trace_redacted.jsonl` | 后续可继续补真实 demo 视频/截图 |
| P1-1 Planner | ✅ 已完成（含行为增强） | `src/runtime/planner.py`、`configs/plan_act.yaml`、plan prompt 注入、一次性 `plan_replanned` trace | 不做复杂 DAG / 多次 replan |
| P1-2 Context | ✅ 已完成（含补强） | 同上 + compact stress eval | L2 见 CODEX-DEFERRED-GAPS |
| P1-3 Agent-as-Tool | ✅ 已完成（含补强） | `subagent_task`、`subagent_traces`、真实 demo trace | 多 worker/递归/写文件见 CODEX-DEFERRED-GAPS |
| P2-1 LLMClient | ✅ 已完成（最小雏形） | `OpenAICompatibleAdapter`、`LLMErrorKind`、`LLMStreamEvent`、`stream_chat()` event skeleton | 真 SSE / cancel token / 多 provider 完整适配后续再做 |
| P2-2 Sandbox | ⏳ 待办 | — | — |

**验证备注**：在 `coding-harness` conda 环境中全量 `pytest tests -q --basetemp .pytest_tmp` 已通过；fixture 误收集已由 pytest 配置规避。

---

## 1. 总体定位

当前项目的最强主线是：

> 可控、可观测、可评测的单 Agent Coding Harness。

后续改进不应把项目改散，而应围绕三件事增强说服力：

1. **评测可信**：任务更真实，裁判更严格，报告能说明差异不是随机波动。
2. **Agent 能力更完整**：补显式规划、轻量子 Agent、上下文控制。
3. **工程边界更清楚**：补 LLM streaming/取消/适配层与更安全的命令执行边界。

面试表达建议：

> 我没有先堆一个复杂 Multi-Agent 平台，而是先把单 Agent 的 runtime、policy、eval、trace 做扎实；再逐步引入 Planner、Agent-as-Tool 和上下文管理，用离线评测证明每个改动的收益与代价。

---

## 2. 优先级总览

| 优先级 | 模块 | 目的 | 最小可交付 |
|---|---|---|---|
| P0-1 | 高质量评测集 | 提高任务代表性 | 8-12 个分层 repo 任务 |
| P0-2 | 裁判系统 | 降低假阳性 | `multi_assert` + 可执行断言 |
| P0-3 | 统计报告 | 证明差异稳定 | 多次运行均值/方差或 bootstrap CI |
| P0-4 | 展示材料 | 面试有证据 | 真实脱敏 trace + 失败案例分析 |
| P1-1 | Planner | 对齐任务分解 | 计划生成 + step 状态更新 |
| P1-2 | Context | 控制上下文膨胀 | L0/L1，暂不做 L2 LLM 总结 |
| P1-3 | Agent-as-Tool | 对齐 Multi-Agent | `max_depth=1`、只读子 Agent |
| P2-1 | LLMClient | 接近真实产品 | provider adapter + 事件流雏形 |
| P2-2 | Sandbox | 明确安全边界 | argv 命令执行 + 可选 Docker runner |

---

## 3. P0：先让项目“评测可信”

P0 的目标是先提升项目面试说服力。不要先进入复杂重构；先让这个 harness 能在更真实、更严格、更稳定的评测上产出结论。

### 3.1 P0-1：高质量分层评测集

#### 问题

当前 `datasets/mini_tasks.json` 主要是创建文件、修改一行、简单 transform。它适合 smoke test，但不足以证明 Agent 能处理真实代码任务。

#### 修改方案

保留现有 `mini_tasks.json`，新增一个更强的数据集，例如：

- `datasets/repo_tasks.json`
- `tests/fixtures/repos/`

新增任务不要硬追数量。第一版建议 **8-12 个高质量任务**，按难度分层：

| 难度 | 数量 | 代表场景 |
|---|---:|---|
| easy | 2-4 | 单文件 bugfix、配置修复、补函数 |
| medium | 3-4 | 跨文件修改、根据测试失败修复、补测试 |
| hard | 2-4 | 多步骤定位、重构后保持测试通过、上下文较长任务 |

每个任务应包含：

- `id`
- `description`
- `fixture_dir` 或 `initial_files`
- `expected`
- `difficulty`
- `tags`

建议覆盖场景：

- 修复 pytest 失败
- 根据错误日志定位 bug
- 跨文件 rename/refactor
- 修复 JSON/YAML/pyproject 配置
- 添加测试并确保通过
- 小型 API/工具函数行为修复
- 多文件读写后生成报告或模块

#### 最小可交付

- 新增 8 个 repo 级任务。
- easy/medium/hard 至少各 2 个。
- 每个任务都能本地独立验证。

#### 实施记录

- ✅ 已完成，见 `docs/changes/P0-1-REPO-TASKS.zh-CN.md`。
- 任务分布：easy 3 / medium 3 / hard 2，全部使用 `fixture_dir` + `multi_assert`。

#### 验收标准

运行：

```bash
python scripts/run_eval.py --dataset datasets/repo_tasks.json --configs baseline
```

可以得到稳定报告，并且每个任务失败时能通过 trace 定位原因。

---

### 3.2 P0-2：增强裁判系统

#### 问题

当前 judge 多数是关键词包含，容易出现假阳性。例如要求删除某行时，只检查保留行存在，不检查目标行是否消失。

#### 修改方案

在 `src/eval/runner.py` 增加更严格的 `expected.type`：

| 类型 | 用途 |
|---|---|
| `file_not_contains` | 检查文件不包含某些内容 |
| `regex_match` | 检查正则匹配 |
| `json_equals` | 结构化比较 JSON |
| `command_success` | 检查命令退出码为 0 |
| `pytest_passes` | 专门跑 pytest |
| `multi_assert` | 组合多个断言 |

推荐以 `multi_assert` 作为主入口，例如：

```json
{
  "type": "multi_assert",
  "assertions": [
    {"type": "file_contains", "path": "poem.txt", "keywords": ["Roses are red"]},
    {"type": "file_not_contains", "path": "poem.txt", "keywords": ["debug line"]},
    {"type": "command_success", "command": "python -m pytest -q"}
  ]
}
```

同时清洗现有 `mini_tasks.json` 中弱裁判任务。

#### 最小可交付

- 实现 `file_not_contains`、`command_success`、`multi_assert`。
- 修复 5 个以上现有弱裁判。

#### 实施记录

- ✅ 已完成，见 `docs/changes/P0-2-JUDGES.zh-CN.md`。
- 额外实现：`json_equals`、`regex_match`、`pytest_passes`。
- 报表通过 `expected_check` 列与 `success && expected_check` 聚合区分 agent 结束 vs 裁判通过。

#### 验收标准

- 错误答案不能仅靠关键词蒙混过关。
- 报告能区分：
  - Agent 没跑完（`failure_reason`）
  - Agent 跑完但 expected 失败（`expected_check=false`）
  - 命令执行失败（裁判内 `command_success` 返回 false，**尚无独立 failure 类型**）
  - 文件断言失败（同上，**尚无逐条断言失败明细**）

---

### 3.3 P0-3：统计显著性与稳定性报告

#### 问题

baseline 与 hardened 的成功率差异可能来自随机波动。面试官可能会问：“你怎么知道不是偶然？”

#### 修改方案

报告中加入稳定性统计。第一版不必过度复杂，推荐两级实现：

#### 方案 A：多次运行均值/方差

CLI 增加参数：

```bash
python scripts/run_eval.py --dataset datasets/repo_tasks.json --compare --runs 5
```

报告展示：

- success_rate mean/std
- avg_steps mean/std
- avg_elapsed_ms mean/std
- tool_failure_rate mean/std

#### 方案 B：bootstrap confidence interval

对 per-task pass/fail 做 bootstrap，报告展示：

- success_rate 95% CI
- baseline-hardened delta 95% CI

可先实现方案 A，再实现方案 B。

#### 最小可交付

- `--runs N`
- 报告展示均值与标准差

#### 实施记录

- ✅ 方案 A 已完成，见 `docs/changes/P0-3-REPEATED-RUNS.zh-CN.md`。
- ⏳ 方案 B（bootstrap CI）仍为后续项。

#### 验收标准

面试时可以回答：

> 我不是只跑一次，而是支持多次 rollout，报告里展示均值和方差；后续也可以用 bootstrap CI 衡量策略差异是否稳定。

---

### 3.4 P0-4：真实展示材料

#### 问题

项目代码和文档已经有主线，但缺少可以面试展示的“证据包”。

#### 修改方案

新增：

- `reports/examples/baseline_vs_hardened_real.md`
- `reports/examples/baseline_vs_hardened_real.csv`
- `docs/examples/real_trace_redacted.jsonl`
- `docs/FAILURE-CASES.zh-CN.md`
- `docs/INTERVIEW-DEMO.zh-CN.md`

展示材料包含：

- baseline vs hardened 成功率差异
- 平均步数差异
- tool failure rate 差异
- policy block 数量
- 3 个典型失败案例
- 1 个成功 trace 的逐步解释

#### 最小可交付

- 1 份真实脱敏 trace
- 1 份 baseline vs hardened 报告
- 3 个失败案例分析

#### 实施记录

- ✅ 示例证据包已完成，见 `docs/changes/P0-4-DEMO-PACK.zh-CN.md`。
- ⚠️ 当前为 **redacted example**，面试前需执行：
  ```bash
  python scripts/run_eval.py --dataset datasets/repo_tasks.json --compare --runs 3
  ```
  用真实输出覆盖 `reports/examples/` 中的 placeholder 数字。

#### 验收标准

可以用 3 分钟讲清楚：

1. 任务是什么
2. Agent 怎么执行
3. 哪里失败
4. policy/eval/trace 如何帮助定位问题
5. 下一步如何改进

---

## 4. P1：增强 Agent 能力，但避免重构泥潭

P1 的风险是 Planner、Context、Agent-as-Tool 三项同时推进会把项目拖进大重构。因此每一项都必须定义最小可交付边界。

### 4.1 P1-1：显式 Planner

#### 问题

当前是标准 ReAct loop，规划隐含在模型对话中。面试 JD 中常见“任务分解、自动化规划、复杂任务执行”，需要更显式的计划对象。

#### 修改方案

新增轻量 Planner：

- `src/runtime/planner.py`
- `Plan`
- `PlanStep`
- `PlanStatus`

第一版只做：

1. 任务开始时生成结构化计划。
2. 每轮工具执行后更新 step 状态。
3. trace 中记录计划创建与状态更新。

暂不做复杂 replan 策略。replan 只预留接口。

示例结构：

```json
{
  "goal": "Fix failing tests",
  "steps": [
    {"id": 1, "title": "Inspect failure", "status": "done"},
    {"id": 2, "title": "Patch implementation", "status": "in_progress"},
    {"id": 3, "title": "Run tests", "status": "pending"}
  ]
}
```

#### 配置建议

```yaml
runtime:
  mode: "react"      # react | plan_act
  planner:
    enabled: true
```

#### 最小可交付

- `plan_act` 模式能生成计划。
- 每步执行后能更新状态。
- trace/report 能显示 plan。

#### 实施记录

- ✅ 已完成，见 `docs/changes/P1-1-PLANNER.zh-CN.md`。
- `SimplePlanner` 基于启用工具生成 3 步确定性计划，不额外调用 LLM。
- `configs/plan_act.yaml` 可切换 `runtime.mode: plan_act`。
- trace metadata 含 `plan`；EventBus 含 `plan_created` / `plan_updated`。

#### 暂不做

- 复杂 DAG
- 多 planner 投票
- 自动频繁 replan
- plan 质量单独打分

---

### 4.2 P1-2：上下文管理

#### 问题

长任务中工具输出和对话历史会膨胀。当前有 micro-compact，但还没有统一上下文策略。

#### 修改方案

先做 L0/L1，不急着做 L2 LLM 总结。

| 层级 | 策略 | 第一版是否做 |
|---|---|---|
| L0 | 单次工具输出截断 | 已有，补 trace 与配置清晰度 |
| L1 | 历史 tool result 压缩 | 已有 micro-compact，增强可观测 |
| L2 | LLM summary 压缩 | 暂缓 |

新增或整理：

- `src/runtime/context.py`
- context stats
- compact event trace

保留重要信息：

- 用户原始任务
- 当前 plan
- 最近 N 条 tool result
- 最近失败原因
- 已修改文件列表

#### 最小可交付

- L0/L1 策略统一配置。
- 每次 compact 记录 trace：
  - before message count
  - after message count
  - compacted tool count

#### 暂不做

- LLM 自动总结
- 长期 memory
- 向量检索

---

### 4.3 P1-3：Agent-as-Tool

#### 问题

当前没有 Multi-Agent 落地。直接做复杂 Multi-Agent 平台成本高、风险大。

#### 修改方案

只做最小 Agent-as-Tool：

- 新增 `subagent_task` 工具。
- 父 Agent 可把只读分析任务委托给子 Agent。
- 子 Agent 固定 `max_depth=1`。
- 子 Agent 第一版只读，不写文件。
- 子 Agent 返回结构化摘要。

返回格式：

```json
{
  "summary": "...",
  "files_inspected": ["src/a.py", "tests/test_a.py"],
  "findings": ["..."],
  "suggested_next_steps": ["..."],
  "confidence": "medium"
}
```

配置：

```yaml
runtime:
  subagents:
    enabled: true
    max_depth: 1
    readonly: true
```

#### 最小可交付

- 父 Agent 能调用一个只读子 Agent。
- 子 Agent 有独立 trace。
- 父 trace 能链接到子 trace。

#### 暂不做

- 多 worker 并行
- agent 间协商
- 子 Agent 写文件
- 多层递归
- 冲突合并

---

## 5. P2：生产化边界增强

P2 不一定最先做，但它能提升工程深度。适合在 P0/P1 有结果后推进。

### 5.1 P2-1：LLMClient 增强

#### 问题

当前 `LLMClient` 是较薄的 OpenAI-compatible 非流式封装。真实 Agent 产品通常需要 streaming、取消、供应商适配、错误分类。

#### 修改方案

抽象：

- `BaseLLMClient`
- `OpenAICompatibleClient`
- `MockLLMClient`

新增能力：

- provider adapter
- streaming event
- cancel token
- error classification
- request metadata trace

事件类型：

- `message_delta`
- `tool_call_delta`
- `llm_stream_done`
- `llm_error`

#### 最小可交付

- 保持当前非流式 API 兼容。
- 增加 provider adapter 结构。
- debug 模式能记录流式事件雏形。

#### 暂不做

- 完整前端 UI
- 所有供应商完整适配
- 复杂 token/cost 计费系统

---

### 5.2 P2-2：命令执行与沙箱增强

#### 问题

当前已有路径沙箱与命令策略，但 `run_command` 使用 shell 执行，隔离级别不是生产级。

#### 修改方案

分两阶段。

#### 阶段 A：本地 runner 增强

- 支持 argv 结构化命令：

```json
{
  "argv": ["python", "-m", "pytest", "-q"]
}
```

- 白名单从字符串 prefix 升级为 argv 级别匹配。
- 默认减少 `shell=True` 使用。
- 记录：
  - exit code
  - stdout
  - stderr
  - duration
  - timed_out
- 增加环境变量白名单。

#### 阶段 B：可选 Docker runner

配置：

```yaml
tools:
  command_runner: "local"   # local | docker
```

Docker runner 限制：

- no network
- memory limit
- CPU limit
- timeout
- non-root user
- workspace bind mount

#### 最小可交付

- argv command runner
- argv whitelist
- 保持旧 `command` 字符串兼容

#### 暂不做

- 立即强制 Docker
- Windows 下复杂容器隔离
- 完整 seccomp profile

---

## 6. 建议实施顺序

### 第一阶段：可信评测闭环

1. P0-1 高质量分层评测集
2. P0-2 增强裁判系统
3. P0-3 多次运行统计报告
4. P0-4 真实展示材料

这一阶段完成后，项目就能更有底气地用于简历和面试。

### 第二阶段：Agent 能力增强

5. P1-1 Planner 最小版
6. P1-2 Context L0/L1 增强
7. P1-3 只读 Agent-as-Tool

这一阶段完成后，项目能对齐 JD 中的“任务分解、上下文管理、Multi-Agent 协作经验”。

### 第三阶段：生产化补强

8. P2-1 LLMClient adapter/streaming
9. P2-2 argv runner 与可选 Docker runner

这一阶段完成后，项目工程深度更强，也更容易回答生产化问题。

---

## 7. 风险控制

### 风险 1：任务集越做越大，但质量不高

控制方式：

- 第一版只做 8-12 个高质量任务。
- 每个任务都要有明确难度、标签和判定。
- 优先代表性，不追数量。

### 风险 2：P1 同时推进导致重构失控

控制方式：

- Planner 只做计划生成和状态更新。
- Context 只做 L0/L1。
- Agent-as-Tool 只做 `max_depth=1`、只读子 Agent。

### 风险 3：评测结果被随机性影响

控制方式：

- P0 就加入 `--runs N`。
- 报告展示均值和标准差。
- 后续再加 bootstrap CI。

### 风险 4：安全增强影响本地可用性

控制方式：

- local runner 保持兼容。
- Docker runner 做可选能力。
- hardened 配置逐步收紧，不一次性破坏所有任务。

---

## 8. 面试讲法

### 30 秒版本

这是一个 Coding Agent harness 项目。我重点做的不是聊天 demo，而是 Agent 运行时、工具策略、安全约束、trace 和离线评测。后续改进会先增强真实 repo 任务和严格裁判，再加入 Planner、上下文压缩和只读子 Agent，用报告证明每个策略改动对成功率、失败类型和成本的影响。

### 2 分钟版本

项目当前实现了单 Agent 的 plan-act-observe loop，支持工具调用、路径沙箱、命令策略、预算控制、JSONL trace 和 baseline/hardened 评测。**已完成**：8 个分层 repo 任务、`multi_assert` 等严格裁判、`--runs` mean/std 报告，以及 `plan_act` 模式下的显式 Planner（trace 可审计）。

现在的主要短板是：展示材料仍是 redacted example、缺少 bootstrap CI、Context 与 Agent-as-Tool 未落地。

我的改进路线是三步：

1. ~~先做可信评测~~（**已完成 P0**）：8 个 repo 任务、可执行断言、`--runs` mean/std；待补真实 API 报告与 bootstrap CI。
2. ~~再做 Agent 能力（Planner 最小版已完成）~~：继续 P1-2 Context、P1-3 只读 Agent-as-Tool。
3. 最后做生产化：LLM adapter/streaming/取消，以及 argv runner 和可选 Docker runner。

这样既不会陷入大而全重构，又能逐步证明每个工程机制对 Agent 可靠性的价值。

---

## 9. 第一批建议修改清单

~~如果开始落地代码，建议第一批只做这些：~~

**第一批（P0 + P1-1）已完成。**

| # | 项 | 状态 |
|---|---|---|
| 1 | `datasets/repo_tasks.json` | ✅ |
| 2 | `tests/fixtures/repos/` | ✅ |
| 3 | `file_not_contains` | ✅ |
| 4 | `command_success` | ✅ |
| 5 | `multi_assert` | ✅ |
| 6 | 清洗弱裁判任务 | ✅（5 项） |
| 7 | `run_eval.py --runs` | ✅ |
| 8 | 报告 mean/std | ✅ |
| 9 | Planner 最小版 | ✅ |

### 9.1 第二批建议（面试前收尾）

1. **真跑 eval 替换示例报告**（P0-4 闭环）。
2. **pytest 工程卫生**：`norecursedirs = fixtures` 或 fixture 移出 `tests/`；确保 `pip install -e ".[dev]"`。
3. **裁判可观测性**（P0-2 补强）：`expected_check` 失败时记录首个失败断言类型；`command_output` 增加 `require_exit_zero`。
4. **进入 P1-2**：Context L0/L1 统一配置与 compact trace。

### 9.2 第三批（对齐 JD 深度）

5. P1-3 只读 Agent-as-Tool  
6. P2-1 LLMClient adapter / streaming 雏形  
7. P2-2 argv runner + 可选 Docker
