# Solid 化改进路线图（P0–P2-1）

> **用途**：把「最小可交付」逐项升级到「Solid（可讲 + 有证据 + 边界清楚）」的方向清单。  
> **来源**：2026-06-25 对 P0-1～P0-4、P1-1～P1-3、P2-1 的 Solid 标准审阅 + ABC 分层 + confound 分析。  
> **配套**：`docs/IMPROVEMENT-PLAN.zh-CN.md`（原始计划）、`docs/changes/POLISH-P1-P2-CLOSEOUT.zh-CN.md`（polish 收尾）、`docs/changes/CODEX-DEFERRED-GAPS.zh-CN.md`（已 defer 项）。
>
> **执行批次**：
> - A 批次（已完成）：`docs/SOLID-A-BATCH-EXECUTION.zh-CN.md` → 收尾 `docs/changes/SOLID-A-BATCH-CLOSEOUT.zh-CN.md`（112 passed）。
> - B 批次（已完成 2026-06-25）：`docs/SOLID-B-BATCH-EXECUTION.zh-CN.md` → 收尾 `docs/changes/SOLID-B-BATCH-CLOSEOUT.zh-CN.md`（131 passed）。
> - C 批次（已完成 2026-06-25）：`docs/SOLID-C-BATCH-EXECUTION.zh-CN.md` → 收尾 `docs/changes/SOLID-C-BATCH-CLOSEOUT.zh-CN.md`（139 passed）。
> - D-2（已完成 2026-06-27）：`docs/SOLID-D2-REMAINING-EXECUTION.zh-CN.md` · `docs/SOLID-D2-DEMO-EXECUTION.zh-CN.md` → `docs/DEMO-SCRIPT.zh-CN.md` · `docs/INTERVIEW-DEMO.zh-CN.md` · `docs/changes/SOLID-D2-*-CLOSEOUT.zh-CN.md`

---

## 0. 评判基准与图例

**Solid 定义**：面试能讲清 + 有可复现证据 + 工程边界明确。当前多数模块为「最小可交付」——能 demo，但缺一层可观测 / 可对比 / 可复现的加固。

**ABC 分层含义**：

- **A 层**：高性价比、低风险、改动小，建议优先做。
- **B 层**：中等工作量，明显提升说服力。
- **C 层**：scope 大或边际收益递减，按岗位需求选做（部分已 defer）。

工作量记号：小 / 中 / 大。

---

## 1. Polish 已完成项（2026-06-25，基线状态）

固化前已落地，作为本路线图的起点：

| 项 | 状态 |
|----|------|
| `stream_chat` 接入 `AgentLoop` + `EventBus`（`tracing.llm_stream_events`） | ✅ |
| 删除死代码 `plan_summary_for_prompt()` | ✅ |
| `CODEX-DEFERRED-GAPS` 决策表 + 缺口 1 标完成 | ✅ |
| `plan_act` 真实 eval（`reports/examples/baseline_vs_plan_act_real.md`） | ✅ |
| 全量测试 | ✅ 139 passed（Solid C 批次后，2026-06-25） |

---

## 2. 关键 confound（解读 eval 时必须声明）

### 2.1 plan_act eval 的策略混淆

`reports/examples/baseline_vs_plan_act_real.md` 中 baseline 81.5% vs plan_act 88.9%（+7.4%）**不能** 单独归因于 Planner：

| 配置 | runtime.mode | command.allow_all |
|------|--------------|-------------------|
| `baseline.yaml` | react | **true**（宽松） |
| `plan_act.yaml` | plan_act | **false**（hardened 白名单） |

成功率差异同时混合了「显式规划」与「命令策略收紧」两个变量。

**消除方法（P1-1 A 层）**：新增 `plan_act_permissive.yaml`（plan_act + baseline 策略），做同策略 A/B。  
✅ **已完成 2026-06-25**：`reports/examples/baseline_vs_plan_act_permissive_real.md`（baseline 85.2% vs plan_act_permissive 92.6%，Δ +7.4%，`--runs 3`）。

### 2.2 模型/API 方差

同一数据集，2026-06-24 baseline 95.8%（8 任务期）vs 2026-06-25 baseline 81.5%（9 任务期）。结论应基于 `--runs N` + bootstrap CI，不引用单次数字。

### 2.3 P1-1 行为「plan 刷新进 messages」（✅ 2026-06-25）

~~plan 仅在 `run()` 开头注入一次 system message；`plan_updated` / `plan_replanned` 只写 trace，不回写 messages。~~

**已修复**：`plan_changed` 时向 `messages` append `Plan update:` system 消息（见 `src/runtime/loop.py`）。  
✅ **B 层 2026-06-25**：`suggested_tools[]` 驱动推进 + 结构化 replan（`src/runtime/planner.py`）。

---

## 3. 逐项 ABC 分层

### P0-1 分层 Repo 评测集

现状（最小）：9 任务 + `fixture_dir`，easy/medium/hard 分层，`multi_assert` 组合裁判。

| 层 | 项 | 价值 | 工作量 |
|----|----|------|--------|
| A | 任务扩到 12–15；补「纯 read+answer」「subagent 专用」各 1–2；report 按 `tags` 分组 | 代表性 | 中 | ✅ 2026-06-25 · 12 任务 · `src/eval/report.py` by-tag |
| A | 每任务附 oracle/参考解（仅 CI，不喂 Agent） | 裁判/debug 有据 | 小–中 | ✅ 2026-06-25 · `scripts/check_dataset_oracle.py` |
| C | 自造 3–4 个 hard 难任务，恢复 baseline 区分度 | 避免 12 任务撞顶 | 中 | ✅ 2026-06-25 · 16 任务 · `reports/examples/baseline_16tasks_discrimination_real.md` |
| B | 难度校准表 + 预期步数区间（异常检测） | 可信度 | 中 |
| C | 自造 hard 难任务（长上下文/多步定位/回归） | 恢复区分度 | 中 | ⚠️ 2026-06-25 · 12→16 任务 · 但对当前模型偏易，区分度有限 |
| C | 接入外部 benchmark 子集（如 SWE-bench lite） | 对外可比 | 大 | ✅ 2026-06-26 · 10 tasks / 3 repos · 污染探针 · **Scaffold A/B** `reports/report_20260626T194843.md` · `docs/changes/SOLID-D1-SCAFFOLD-CLOSEOUT.zh-CN.md` |

**Solid 差距**：外部 benchmark 已具备可移植 env + 题面清洗 + 防作弊 + scaffold 对称 A/B；绝对率不作能力指标；planner 消除 confound 后仍 **无显著翻盘**（CI 重叠）。

---

### P0-2 裁判系统

现状（最小+补强）：`multi_assert` / `json_equals` / `regex_match` / `file_not_contains` / `command_success` / `yaml_contains`；`command_output` 默认校 exit code。

| 层 | 项 | 价值 | 工作量 |
|----|----|------|--------|
| A | 裁判失败返回 **具体 assert 名 + 片段**，写入 trace/report | 失败分析、面试追问 | 小 | ✅ 2026-06-25 · `src/eval/runner.py` · `tests/test_runner.py` |
| A | `command_success` 的 cwd / env 白名单文档化 | 与 P2-2 衔接 | 小 |
| B | AST/结构化检查（`ast.parse`、import 图） | 降假阳性 | 中 | ✅ 2026-06-25 · `python_ast_valid` / `python_defines` |
| B | flaky 检测：关键任务多 run 自动标 unstable | 可信结论 | 中 | ✅ 2026-06-25 · Unstable Tasks in report · `docs/FAILURE-CASES.zh-CN.md` §6 · `--runs 5` `reports/report_20260625T095943.md` |
| C | LLM-as-judge（仅 hard 任务 + 人工 spot-check） | 开放题 | 大 |

**Solid 差距**：失败时常只见 PASS/FAIL，缺「哪条 assert 挂了」的叙事。

---

### P0-3 多次运行统计（含 bootstrap CI）

现状（最小+补强）：`--runs N`、mean/std、bootstrap 95% CI、CSV run 级展开。

| 层 | 项 | 价值 | 工作量 |
|----|----|------|--------|
| A | 报告固定输出 paired delta CI + 「是否显著」一句话 | 常被追问 | 小 | ✅ 2026-06-25 · Significance in report · ✅ 2026-06-26 返工加异常轮检测与 withheld |
| A | 记录每 run 的 git commit / model / config hash | 可复现 | 小 | ✅ 2026-06-25 · Run Metadata |
| B | per-task 成功率热力图 | 定位弱项 | 小–中 | ✅ 2026-06-25 · Per-Task Pass Matrix · `src/eval/report.py` |
| B | 成本列：token / API 耗时 / $ per run | 产品思维 | 中 | ✅ 2026-06-25 · `--cost-per-1k` · `reports/report_20260625T100708.md` |
| C | 多模型矩阵 eval | 横向对比 | 大 | ✅ 2026-06-27 · `configs/baseline_modelB.yaml` · `reports/report_20260627T033945.md`（baseline 96.9% vs modelB 87.5%） |

**Solid 差距**：统计框架已有，缺实验元数据与 per-task 叙事自动化。

---

### P0-4 展示材料

现状（最小→已补真实跑分）：`reports/examples/`、脱敏 trace、`INTERVIEW-DEMO`、`FAILURE-CASES`。

| 层 | 项 | 价值 | 工作量 |
|----|----|------|--------|
| A | 补 plan_act events trace 示例（含 `plan_replanned`） | Planner 故事闭环 | 小 | ✅ 2026-06-25 · `docs/examples/plan_act_events_redacted.jsonl` |
| A | 补 debug + `llm_stream_events` 的 events 片段 | P2-1 故事闭环 | 小 | ✅ 2026-06-25 · `docs/examples/llm_stream_events_redacted.jsonl` |
| B | 失败 taxonomy 一页，从 CSV 自动生成 | 维护成本降 | 中 | ✅ 2026-06-27 · `scripts/gen_failure_taxonomy.py` · `reports/examples/failure_taxonomy.md` |
| C | 录屏 / Glass 演示脚本（30s + 2min） | 现场印象 | 中 | ✅ 2026-06-27 · `docs/DEMO-SCRIPT.zh-CN.md` · `docs/INTERVIEW-DEMO.zh-CN.md` |

**Solid 差距**：P0-4 展示链路已闭环（trace 示例 + taxonomy + 演示脚本 + 面试总收口）。

---

### P1-1 Planner（含行为增强）

现状（最小）：确定性 3 步；prompt 注入（仅 run 开头）；一次 replan；弱匹配推进；trace 完整。

| 层 | 项 | 价值 | 工作量 |
|----|----|------|--------|
| A | **每步 `plan_updated` 后回写/刷新 messages** | 模型真跟着 plan 走 | 小 | ✅ 2026-06-25 · `src/runtime/loop.py` |
| A | 新增 `plan_act_permissive.yaml`，做同策略 A/B | 可宣称 Planner 收益 | 小 | ✅ 2026-06-25 · `reports/examples/baseline_vs_plan_act_permissive_real.md` |
| B | step 显式 `suggested_tools[]`，替代 title 关键词弱匹配 | 推进可信 | 中 | ✅ 2026-06-25 · `src/runtime/planner.py` |
| B | replan 改 step 文案 / 增删一步（仍限 1 次） | 叙事更实 | 中 | ✅ 2026-06-25 · 结构化 replan titles |
| C | 额外 LLM 调用生成/修订 plan | 真 Planner | 大 |

**Solid 差距**：trace 像 Planner，模型侧仍 largely react；eval confound 未解。

---

### P1-2 Context L0/L1

现状（最小）：L0 截断 + L1 micro-compact + `context_compacted` 事件；compact_stress eval（66.7% 无回归）。

| 层 | 项 | 价值 | 工作量 |
|----|----|------|--------|
| A | 按 **token 估算** 触发 compact（非仅字符） | 贴近真实窗口 | 小–中 | ✅ 2026-06-25 · `src/runtime/compact.py` · `configs/context_compact_threshold.yaml` |
| A | compact 保留规则（最近失败 + 已改文件列表）写进代码/文档 | 防丢关键上下文 | 小 | ✅ B 批次 · `_protected_tool_indices` |
| B | stress 任务扩到 5–6 条 + 多 run | 结论更稳 | 中 | ✅ 2026-06-25 · compact 效率正收益 · `reports/examples/baseline_vs_context_compact_threshold_real.md` |
| C | L2 LLM 摘要（= CODEX 缺口 2，已 defer） | 长上下文 | 大 |

**Solid 差距**：L1 已在对齐 confound 的 A/B 下证明 **效率正收益**（步数/耗时↓，成功率不回归）；L2 仍 defer。

---

### P1-3 Agent-as-Tool（只读 subagent）

现状（最小）：`subagent_task`、`max_depth=1`、父子 trace、`subagent_traces`；真实 demo 有；`medium_subagent_cross_file` 触发但裁判 FAIL。

| 层 | 项 | 价值 | 工作量 |
|----|----|------|--------|
| A | 修任务描述 / 裁判 / child prompt，让「分析→父执行」链路可 PASS | 完整 Multi-Agent 故事 | 小–中 | ✅ 2026-06-25 · `medium_subagent_cross_file` 3/3 PASS |
| A | child 输出 schema 校验（`findings` 非空等） | 父 Agent 可用性 | 小 | ✅ 2026-06-25 · `schema_ok` in `src/tools/subagent.py` |
| B | 2 个只读 child 并行（仍 max_depth=1） | 平台化雏形 | 中 |
| C | 可写子 Agent / 递归（= CODEX 缺口 3–4，已 defer/不做） | 范围大 | 大 |

**Solid 差距**：机制有了，但唯一 subagent 专用任务还没跑通，面试易被追问。

---

### P2-1 LLMClient（polish 后）

现状：adapter + `LLMErrorKind` + stream 事件合约；debug 下已接 EventBus；仍非真 SSE。

| 层 | 项 | 价值 | 工作量 |
|----|----|------|--------|
| A | `RetryPolicy` 用 `LLMErrorKind` | 错误分类有实际意义 | 小 | ✅ 2026-06-25 · `src/runtime/retry.py` |
| A | trace 记 request metadata（model / latency / tokens） | 可观测 | 小 | ✅ 2026-06-25 · `llm_complete` event in `src/runtime/loop.py` |
| B | 真 SSE chunk 增量解析 | 真 streaming | 中–大 |
| C | cancel token + 第二 provider adapter | 产品级 | 大 | ✅ 2026-06-25（部分）· cancel token + HTTP retry 细分 · `src/runtime/loop.py` · `tests/test_agent_loop.py` |

**Solid 差距**：分类与事件合约有了；cancel + HTTP retry 细分已落地；真 SSE 仍 defer。

---

### P2-2 命令执行与沙箱

现状：原 `run_command` 仅 shell + prefix 模糊白名单。

| 层 | 项 | 价值 | 工作量 |
|----|----|------|--------|
| A | argv 结构化执行（非 shell）+ 首元素精确白名单 + env 白名单 + `command_executed` 事件 | 安全边界叙事 | 中 | ✅ 2026-06-25 · `src/policy/rules.py` `check_argv` · `src/tools/command.py` · `configs/hardened_argv.yaml` |
| B | Docker runner / 完整隔离沙箱 | 生产级隔离 | 大 |
| C | 资源限额（cgroup / 内存 / CPU） | 生产级 | 大 |

**Solid 差距**：本地 argv 边界已清晰；进程级隔离（Docker）仍未做。

---

## 4. 推荐执行顺序（按 ROI）

目标「最小交付 → Solid」，建议顺序：

1. ~~**P1-1 A**~~ ✅ 2026-06-25
2. ~~**P1-3 A**~~ ✅ 2026-06-25
3. ~~**P0-2 A**~~ ✅ 2026-06-25
4. ~~**P0-4 A**~~ ✅ 2026-06-25
5. ~~**P2-1 A**~~ ✅ 2026-06-25
6. ~~**P2-2 阶段A**~~ ✅ 2026-06-25
7. ~~**P0-1 A**~~ ✅ 2026-06-25
8. ~~**P0-2 B**~~ ✅ 2026-06-25
9. ~~**P1-1 B**~~ ✅ 2026-06-25
10. ~~**P0-3 A**~~ ✅ 2026-06-25

**C 批次（已完成 2026-06-25，见 `docs/changes/SOLID-C-BATCH-CLOSEOUT.zh-CN.md`）**：

11. ~~**P0-1 C 难任务扩充**~~ ✅ 2026-06-25 · `reports/examples/baseline_16tasks_discrimination_real.md`
12. ~~**P1-2 A token compact + 正收益**~~ ✅ 2026-06-25 · `reports/examples/baseline_vs_context_compact_threshold_real.md`
13. ~~**P2-1 C（部分）cancel + retry 细分**~~ ✅ 2026-06-25
14. ~~**P0-3 B 成本 + pass matrix**~~ ✅ 2026-06-25 · `reports/report_20260625T100708.md`
15. ~~**P0-2 收尾 flaky 多 run**~~ ✅ 2026-06-25 · `reports/report_20260625T095943.md`

**D 批次（D-1 + D-2 已完成，2026-06-27）**：

- **D-1（Codex 5.3）** `docs/SOLID-D1-SWEBENCH-EXECUTION.zh-CN.md`：
  16. ~~**P0-1 C 大版 — SWE-bench Lite 子集接入**~~ ✅ 2026-06-25 · `datasets/swebench_lite_tasks.json` · `reports/examples/swebench_lite_real.md`
  16b. ~~**D1 打磨 — 官方 specs 环境 + 扩样本 + runs=5 A/B**~~ ✅ 2026-06-26 · `docs/SOLID-D1-POLISH-EXECUTION.zh-CN.md` · `reports/report_20260625T180202.md`（402 污染，已作废）· `docs/changes/SOLID-D1-POLISH-CLOSEOUT.zh-CN.md`
  16c. ~~**D1 返工 — 可移植 requests + 题面清洗 + 干净 A/B**~~ ✅ 2026-06-26 · `reports/report_20260626T101113.md` · `docs/changes/SOLID-D1-REWORK-CLOSEOUT.zh-CN.md`
  16d. ~~**D1 污染方法论 — 文件定位探针 + NOTES**~~ ✅ 2026-06-26 · `scripts/contamination_probe.py` · `reports/contamination_probe.md` · `docs/CONTAMINATION-NOTES.zh-CN.md` · `docs/changes/SOLID-D1-CONTAMINATION-CLOSEOUT.zh-CN.md`
  16e. ~~**D1 Scaffold — 防作弊 + 工具/预算扩张 + 重跑 A/B**~~ ✅ 2026-06-26 · `docs/SOLID-D1-SCAFFOLD-EXECUTION.zh-CN.md` · `reports/report_20260626T194843.md`（baseline 20.0% vs plan_act 26.7%，CI 重叠无显著）· `docs/changes/SOLID-D1-SCAFFOLD-CLOSEOUT.zh-CN.md`
- **D-2（Composer 2.5）** `docs/SOLID-D2-REMAINING-EXECUTION.zh-CN.md`：
  17. ~~**P0-4 B — 失败 taxonomy 自动生成**~~ ✅ 2026-06-27 · `reports/examples/failure_taxonomy.md` · `docs/changes/SOLID-D2-REMAINING-CLOSEOUT.zh-CN.md`
  18. ~~**P0-3 C — 多模型矩阵**~~ ✅ 2026-06-27 · `reports/report_20260627T033945.md`
  19. ~~**P0-4 C — 演示脚本**~~ ✅ 2026-06-27 · `docs/DEMO-SCRIPT.zh-CN.md`
  20. ~~**文档总收口 — INTERVIEW-DEMO A–D**~~ ✅ 2026-06-27 · `docs/INTERVIEW-DEMO.zh-CN.md` · `docs/changes/SOLID-D2-DEMO-CLOSEOUT.zh-CN.md`

**仍 defer**：真 SSE、L2 摘要、多 worker、LLM planner、P2-2 Docker —— scope 大、面试边际收益递减。

---

## 5. 维护约定

- 每完成一个 A/B/C 项，在本表对应行标注完成日期与证据路径（report / trace / 测试）。
- 涉及 eval 数字的改动，必须用 `--runs N` 并在报告声明 confound（见 §2）。
- 与 `IMPROVEMENT-PLAN.zh-CN.md` 的关系：那是「做了什么」，本文是「还能更 solid 在哪」。
