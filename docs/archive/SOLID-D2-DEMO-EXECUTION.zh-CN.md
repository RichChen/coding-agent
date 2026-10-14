# Solid D-2 · 演示脚本 + INTERVIEW-DEMO 总收口（Composer 执行）

> **执行模型**：Composer（**纯文档**，不跑 eval、不改 harness 代码）。  
> **范围**：ROADMAP §4 D-2 第 **19–20** 项——`docs/DEMO-SCRIPT.zh-CN.md` + 重写/扩写 `docs/INTERVIEW-DEMO.zh-CN.md` + ROADMAP 状态更新 + CLOSEOUT。  
> **上游**：`docs/SOLID-D2-REMAINING-CLOSEOUT.zh-CN.md`（taxonomy + 多模型已完成）；D-1 全链路 CLOSEOUT 与 `docs/CONTAMINATION-NOTES.zh-CN.md`。  
> **环境**：`C:\Users\Administrator\.conda\envs\coding-harness\python.exe`；**本文不要求改代码**，但若误触代码须保持 **148 passed**。  
> **Git**：可用 `C:\Program Files\Git\bin\git.exe`；完成后 **commit 文档改动**。

---

## 0. 写作原则（必读，避免叙事错误）

1. **三层数字，勿混用**（面试被追问时靠这个站住）：
   - **repo 自造任务**（12–16 条）：plan_act 单变量 **+5.6%**、compact stress **-13.6% 耗时**——证明 harness **机制**有效。
   - **SWE-bench 子集**（10 任务）：baseline **32%** vs plan_act **24%**（REWORK）→ scaffold 后 **20%** vs **27%**（runs=3）——**CI 均重叠，planner 无统计优势**；且探针证明**强污染**，绝对成功率**不作能力指标**。
   - **多模型矩阵**（repo 16）：v4-pro **96.9%** vs deepseek-chat **87.5%**——证明 harness **与模型解耦**。

2. **最强亮点是 D-1 方法论**（污染探针 + 诚实 null + 防作弊 + scaffold 排除 confound），不是刷 SWE-bench 成功率。

3. **所有路径/命令必须真实存在**——写前先 `Test-Path` / `glob` 核实；**禁止编造数字**（下表为已核实来源）。

---

## 1. 已核实证据表（写作时直接引用）

| 主题 | 数字/结论 | 证据路径 |
|------|-----------|----------|
| plan_act 单变量（repo） | baseline 94.4% vs plan_act **100%**，Δ **+5.6%**（12 任务，runs=3） | `reports/examples/baseline_vs_plan_act_permissive_v2_real.md` |
| context compact 效率 | compact_stress 耗时 **-13.6%**、步数 **-0.8**，成功率不回归 | `reports/examples/baseline_vs_context_compact_threshold_real.md` |
| SWE-bench 干净 A/B | baseline **32.0%** vs plan_act **24.0%**，CI 重叠无显著 | `reports/report_20260626T101113.md` |
| SWE-bench scaffold A/B | baseline **20.0%** vs plan_act **26.7%**，CI 重叠无显著 | `reports/report_20260626T194843.md` |
| 污染探针 | 5×重复：池化 exact **54.2%**，**7/10** 多数票定位 | `reports/contamination_probe.md` |
| 多模型矩阵 | v4-pro **96.9%** vs chat **87.5%**（repo 16，runs=2） | `reports/report_20260627T033945.md` |
| 失败 taxonomy | step_limit **47.5%**、none(judge 挂) **38.4%** | `reports/examples/failure_taxonomy.md` |
| plan-act trace 示例 | `plan_created` → `plan_updated` → `plan_replanned` | `docs/examples/plan_act_events_redacted.jsonl` |
| 能力全景 | A–D 批次 CLOSEOUT | `docs/changes/SOLID-*-CLOSEOUT.zh-CN.md` |

---

## Phase 1 — 新建 `docs/DEMO-SCRIPT.zh-CN.md`

**定位**：面试官/自己**可照读**的演示稿；30 秒电梯词 + 2 分钟现场 walkthrough。语气：陈述、可执行，不堆形容词。

### 1.1 文档结构（必须包含以下章节）

```markdown
# 演示脚本（30s + 2min）

> 数字与路径见 `docs/INTERVIEW-DEMO.zh-CN.md`；全项目地图见 `docs/SOLID-ROADMAP.zh-CN.md`。

## 30 秒版（背下来）

[一段连贯口播，含：]
- 一句话定位：可控 / 可观测 / 可评测 的单 Agent Coding Harness
- **证据点 1（机制有效）**：同策略单变量 plan_act，repo 12 任务 **+5.6%**（无 policy confound）
- **证据点 2（效率）**：context compact 在 stress 集 **-13.6% 耗时**，成功率不回归
- **证据点 3（评估有效性 — 最强）**：接 SWE-bench 子集后做污染探针（54.2% 无上下文定位 = 强记忆），诚实声明绝对成功率不可作能力指标；消除 scaffold confound 后 planner 仍无显著优势

## 2 分钟版（逐步操作）

### Step 0 — 开场（15s）
[架构一句话：loop + policy + eval + trace；模型不可信，harness 约束并量化策略]

### Step 1 — 架构速览（20s）
[打开/指：`src/runtime/loop.py`、`src/eval/runner.py`、`src/tracing/logger.py`、`configs/baseline.yaml`]
[讲：配置驱动、YAML 校验、JSONL trace]

### Step 2 — 现场跑单任务（40s）
[给可复制命令 + 预期输出说明]

### Step 3 — 打开 trace 走查（25s）
[打开 `docs/examples/plan_act_events_redacted.jsonl`，指 3 个 event 类型]

### Step 4 — 展示 eval 报告（30s）
[打开 `reports/report_20260626T101113.md` 或 `reports/report_20260627T033945.md`]
[指：Bootstrap CI、Significance 一句、Model Matrix（若用后者）]

### Step 5 — 失败与 taxonomy（20s）
[打开 `reports/examples/failure_taxonomy.md`，讲 step_limit vs judge 挂；可选指 Unstable 某 task]

### Step 6 — 收束（10s）
[指向 D-1 污染叙事 + `docs/CONTAMINATION-NOTES.zh-CN.md`]

## 附录：常用命令

[列出 4–6 条真实命令，见 §1.2]

## 附录：若被追问

[3–5 条 Q&A：为何 planner 在 SWE-bench 不显著？污染怎么办？hardened 为何降成功率？]
```

### 1.2 Step 2 推荐命令（写入脚本，须与仓库一致）

**方案 A（零成本、推荐现场 demo）**——单任务 + plan_act：

```powershell
cd D:\crq\src\coding-harness
C:\Users\Administrator\.conda\envs\coding-harness\python.exe scripts/run_single.py ^
  "Create hello.py that prints Hello, World!" ^
  --config configs/plan_act_permissive.yaml
```

说明：跑完会在 `traces/` 下生成 JSONL；若需 events 级演示，直接打开 `docs/examples/plan_act_events_redacted.jsonl`（已脱敏，更稳）。

**方案 B（可选，会调 API、1 个 mini 任务）**：

```powershell
C:\Users\Administrator\.conda\envs\coding-harness\python.exe scripts/run_eval.py ^
  --dataset datasets/mini_tasks.json ^
  --configs plan_act_permissive ^
  --runs 1
```

**不要**在演示脚本里默认跑 SWE-bench 全量（太贵）。

### 1.3 写作禁忌

- 不要把 repo 任务的 +5.6% 说成 SWE-bench 结论。
- 不要把 SWE-bench 32% 说成「agent 能力很强」——必须带污染免责声明。
- 不要引用已作废报告 `report_20260625T180202.md`（402 污染）。

### ✅ Phase 1 验收

- [ ] `docs/DEMO-SCRIPT.zh-CN.md` 存在，30s/2min 两版自洽。
- [ ] 文中每一条文件路径、命令在磁盘上可找到。

---

## Phase 2 — 重写/扩写 `docs/INTERVIEW-DEMO.zh-CN.md`

**目标**：5 分钟可读完的**最终面试材料**；整合 A–D，**保留并收束已有 D-1 节**（勿删污染叙事，可精简重复）。

### 2.1 建议结构（按此重组，可合并短节）

1. **抬头**：数字来源日期更新至 2026-06-27；证据索引表（链到 DEMO-SCRIPT、ROADMAP、各 CLOSEOUT、关键 report）。
2. **30 秒 / 2 分钟版**：各一段（可与 DEMO-SCRIPT 呼应，INTERVIEW-DEMO 略短，详细步骤链到 DEMO-SCRIPT）。
3. **能力矩阵（A–D）**——表格，每行：能力 | 一句话 | 证据路径

   | 批次 | 能力 | 证据 |
   |------|------|------|
   | A | 单变量 plan_act A/B | `baseline_vs_plan_act_permissive_v2_real.md` |
   | A | plan 刷新进 messages | `src/runtime/loop.py` |
   | B | suggested_tools + replan | `src/runtime/planner.py` |
   | B | argv 命令白名单 | `configs/hardened_argv.yaml` |
   | C | token 阈值 compact 正收益 | `baseline_vs_context_compact_threshold_real.md` |
   | C | bootstrap CI / cost / pass matrix | `src/eval/report.py` |
   | D | SWE-bench 子集 + 防作弊 | `SOLID-D1-SCAFFOLD-CLOSEOUT` |
   | D | 污染探针 + NOTES | `contamination_probe.md` |
   | D | 失败 taxonomy 自动聚合 | `failure_taxonomy.md` |
   | D | 多模型矩阵 | `report_20260627T033945.md` |

4. **三个数字亮点**（更新原文过时表）：
   - plan_act **+5.6%**（repo，单变量）
   - compact **-13.6%** 耗时（stress，成功率不回归）
   - **评估有效性**：污染探针 54.2% + SWE-bench planner **null result**（非「刷分亮点」）

5. **D-1 节**：保留现有四步叙事（可略压缩），确保与 `CONTAMINATION-NOTES` 一致。

6. **工程深度点**（ bullet，各 1 句 + 路径）：
   - argv / CommandPolicy
   - LLMErrorKind → RetryPolicy
   - cancel token + HTTP retry 细分
   - `--cost-per-1k` 成本列
   - `is_degenerate_run` 402 免疫
   - 判定前 `_restore_protected_paths` 防作弊

7. **失败与 flaky**：链到 `failure_taxonomy.md` + `FAILURE-CASES.zh-CN.md`。

8. **该怎么收束** / **若被追问**：更新为 A–D 完整版；future work（SWE-bench-Live）保留。

9. **导航**：显式指向 `docs/DEMO-SCRIPT.zh-CN.md`、`docs/SOLID-ROADMAP.zh-CN.md`。

### 2.2 与旧版关系

- 旧表「baseline vs hardened 95.8%」等 **可保留在「历史实验」小节**或并入能力矩阵，但**不要**与 D-1 SWE-bench 数字并列当作「三个最强亮点」。
- **不要**覆盖 D-1 节已写好的污染结论。

### ✅ Phase 2 验收

- [ ] 5 分钟内可扫完全貌；能力矩阵 ≥8 行；三个亮点数字与 §1 证据表一致。
- [ ] 无作废报告引用；无「SWE-bench 区分度=成功率很高」类误导表述。

---

## Phase 3 — ROADMAP + CLOSEOUT + Git

### 3.1 更新 `docs/SOLID-ROADMAP.zh-CN.md`

- §4 D-2 第 **19–20** 项标 ✅，证据路径：
  - 19 → `docs/DEMO-SCRIPT.zh-CN.md`
  - 20 → `docs/INTERVIEW-DEMO.zh-CN.md`
- 修正第 **236** 行附近「D-2 待执行」→ **「D-2 已完成（2026-06-27）」**。
- §3 P0-4 行「Solid 差距：…演示脚本 D 批次处理」→ 改为已完成或删除过时差距表述。
- 顶部执行批次列表补 D-2 demo 收口一行（可选）。

### 3.2 新增 `docs/changes/SOLID-D2-DEMO-CLOSEOUT.zh-CN.md`

简短记录：产出了哪两个 md、INTERVIEW-DEMO 重组要点、ROADMAP 更新、无代码改动 / pytest 仍 148。

### 3.3 Git commit

```powershell
cd D:\crq\src\coding-harness
& "C:\Program Files\Git\bin\git.exe" add docs/DEMO-SCRIPT.zh-CN.md docs/INTERVIEW-DEMO.zh-CN.md docs/SOLID-ROADMAP.zh-CN.md docs/changes/SOLID-D2-DEMO-CLOSEOUT.zh-CN.md docs/SOLID-D2-DEMO-EXECUTION.zh-CN.md
& "C:\Program Files\Git\bin\git.exe" commit -m "docs(d2): demo script and interview materials A-D closeout"
```

若还有未提交的 `SOLID-D2-REMAINING-CLOSEOUT` 改动，一并纳入。

---

## 边界 / 不做

- 不跑 eval、不改 `configs/` / `src/`（除非发现 DEMO-SCRIPT 引用的示例文件缺失且必须补——那种情况只补静态示例，不跑 API）。
- 不重写 `FAILURE-CASES.zh-CN.md` 全文（最多加 2 行指向 taxonomy）。
- 不新建 `DEMO-SCRIPT` 的英文版。

---

## 给 Composer 的一句话起点

> 按 `docs/SOLID-D2-DEMO-EXECUTION.zh-CN.md` 做 **纯文档收口**：新建 `docs/DEMO-SCRIPT.zh-CN.md`（30s 口播 + 2min 分步演示，命令用 `run_single.py` + 脱敏 trace + 打开 `report_20260626T101113.md` 与 `failure_taxonomy.md`）；扩写重组 `docs/INTERVIEW-DEMO.zh-CN.md`（能力矩阵 A–D、三亮点：+5.6% / -13.6% / 污染方法论，**保留 D-1 节**，勿把 repo 数字当 SWE-bench 结论）；更新 ROADMAP 标 19–20 完成并修正「D-2 待执行」；写 `SOLID-D2-DEMO-CLOSEOUT`；git commit。不跑 eval、不改代码；数字只从 §1 证据表引用。
