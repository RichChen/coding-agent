# Codex 待决策缺口清单

> **背景**：方案 A（P0/P1 面试前收尾）已由 Cursor 完成。本文列出 **尚未实现、且需要 Codex 判断是否值得做** 的四类缺口。  
> **请先读**：`docs/IMPROVEMENT-PLAN.zh-CN.md`、`docs/changes/P0-A-CLOSEOUT.zh-CN.md`

---

## 如何使用本文

对每一项给出决策之一：

- **做**：说明最小可交付 + 验收命令 + 预估工作量  
- **defer**：写清理由与面试怎么说  
- **不做**：写清替代叙事  

不要默认「全部完善」——其中多项会显著扩大项目范围。

---

## 缺口 1：P1-1 Planner 行为增强

### 当前状态（2026-06-25 更新）

- ✅ `SimplePlanner` 生成 3 步确定性计划  
- ✅ `plan_act` 模式 + `plan_created` / `plan_updated` / `plan_replanned` trace  
- ✅ 计划 **已注入 prompt**（run 开头 system message）  
- ✅ 工具失败时 **一次性** replan（标题轻量修订）  
- ✅ step 推进：成功工具与 step title **弱匹配** 后推进  
- ⏳ plan 每步刷新进 messages（Solid A 层，见后续 Solid 审阅）  
- ✅ `repo_tasks` baseline vs plan_act 对比 eval（见 `reports/examples/baseline_vs_plan_act_real.md`；注意策略 confound）

### 原「若做」最小边界（已由 Codex 完成）

1. 在 system 或首条 user 消息后注入 plan 摘要  
2. 工具失败时允许 **一次** replan  
3. step 完成判定：关联工具成功且与 step title 弱匹配  

**决策：做（最小版）** — 2026-06-25 Codex 实现；Cursor polish 补 stream 接入与 eval。

### 验收

- `configs/plan_act.yaml` 在 2～3 个 repo task 上 trace 可见 plan 版本变化  
- 默认 `react` 行为不变  
- `pytest tests/test_planner*.py` 仍全过  

### 风险

- 行为变化可能导致现有 repo eval 数字波动，需重跑对比  
- 易与 replan 策略纠缠，导致 scope 膨胀  

### 面试价值

**中–高**（JD 常问任务分解；当前已有 trace，增强后更有「Planner 真的在指导 Agent」的说服力）

---

## 缺口 2：P1-2 L2 LLM 上下文总结

### 当前状态

- ✅ L0 工具输出截断、L1 micro-compact + `context_compacted` trace  
- ✅ 短/中任务 compact 对比实验（见 `reports/examples/baseline_vs_context_compact_real.md`）  
- ❌ 无 LLM 对历史消息的 **语义摘要**  

### 若做，建议最小边界

- 仅在 messages 字符数超过阈值时触发  
- 摘要后保留：user 任务、plan、最近 N tool、最近失败、已改文件列表  
- trace 记录：摘要前后 token/字符数、被摘要消息数  

### 验收

- `compact_stress_tasks` 上 compact **有** `context_events`，L2 摘要 **额外** 降低字符数且不降成功率  
- 需真实 API eval 证明  

### 风险

**高**：额外 API 成本、摘要漂移、实现与调试周期长  

### 面试价值

**中**（能讲「三层 context 策略」，但 L1 已够用；L2 更适合有充足时间时做）

### 建议默认决策

**defer**，除非目标岗位 explicitly 要求 long-context / summarization。

---

## 缺口 3：P1-3 Multi-Agent 平台化（多 worker + 递归）

### 当前状态

- ✅ 只读 `subagent_task`，`max_depth=1`，独立 trace，父 metadata `subagent_traces`  
- ❌ 无并行 worker  
- ❌ 无子 Agent 再委托子 Agent（递归）  
- ❌ 无 agent 间协商 / 冲突合并  

### 若做，建议最小边界

- **不要** 一次做全平台  
- 可选中间步：并行 **2 个** 只读 subagent（不同子任务），父 Agent 合并 JSON 结果  

### 验收

- trace 中可见并行子 run  
- 仍禁止写文件、禁止 depth>1  

### 风险

**很高**：调度、取消、错误传播、eval 稳定性  

### 面试价值

**中**（「我做过 Agent-as-Tool」已够；平台化除非 JD 强调 distributed agents）

### 建议默认决策

**defer** 或 **仅做并行只读 PoC**（1 周内）。

---

## 缺口 4：P1-3 子 Agent 写文件

### 当前状态

- 子 Agent **只读**（`read_file` / `list_dir`）  
- 父 Agent 负责所有写操作  

### 若做，建议最小边界

- 子 Agent 仅允许 `write_file` 到 **指定子目录**（如 `.subagent/``）  
- 父 Agent 负责 merge 到主 workspace  
- policy 必须拦截子 Agent 的 `run_command`  

### 验收

- 1 个 repo task：子 Agent 写分析报告，父 Agent 改代码  
- 无递归 subagent  

### 风险

**高**：权限边界、误写、eval 难判定  

### 面试价值

**中–低**（只读 narrative 更清晰：「分析 vs 执行分离」）

### 建议默认决策

**不做**，除非有明确 demo 需求。

---

## 决策汇总表（供 Codex 填写）

| 缺口 | 建议默认 | Codex 决策 | 备注 |
|------|----------|------------|------|
| 1. Planner 行为增强 | 可选做最小版 | **做（最小版）** | Codex 2026-06-25；polish + eval 见 `POLISH-P1-P2-CLOSEOUT` |
| 2. L2 LLM summary | defer | **defer** | L1 已有实验证据 |
| 3. 多 worker / 递归 | defer | **defer** | 只读 subagent 已够用 |
| 4. 子 Agent 写文件 | 不做 | **不做** | 分析/执行分离叙事 |

---

## 与 P2 的关系

若时间有限，**P2-1（LLMClient adapter/streaming）** 可能比缺口 2–4 更适合「生产化」叙事。  
Codex 决策时请同时考虑：`docs/IMPROVEMENT-PLAN.zh-CN.md` 中 P2-1 / P2-2 优先级。

---

## 环境提醒

- Eval 请在 **本机 conda + 可联网** 环境跑：`C:\Users\Administrator\.conda\envs\coding-harness\python.exe`  
- 受限 Agent 环境可能 `All connection attempts failed`，不应把网络失败当策略结论  
