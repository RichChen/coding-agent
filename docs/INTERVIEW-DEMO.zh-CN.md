# 面试讲解稿

> 数字来源：真实 DeepSeek API 跑分（`coding-harness` conda 环境，2026-06-24～26）。  
> 详见 `reports/examples/`、`docs/changes/P0-A-CLOSEOUT.zh-CN.md`；D-1 SWE-bench + 污染方法论见 `reports/report_20260626T101113.md`、`reports/contamination_probe.md`、`docs/CONTAMINATION-NOTES.zh-CN.md`。

## 30 秒版

这是一个 **可控、可观测、可评测** 的单 Agent Coding Harness。我把评测从 toy tasks 升级到 **repo 级任务**直至 **SWE-bench Lite 真实子集**，裁判升级为 **`multi_assert` + 可执行断言**，并用同一套脚本做单变量 A/B。**最能体现深度的一段是 D-1**：我不仅跑了 baseline vs planner 的干净对比，还**做了污染探针证明这批任务被模型记忆污染**、绝对成功率不可作能力指标——这是"我懂评估有效性"的硬证据（详见下方 D-1 节）。

## 2 分钟版

**主线**：在模型不可信的前提下，用 harness 约束工具调用，用离线 eval 量化策略改动的影响。

**已完成能力：**

1. **运行时**：plan-act-observe loop、沙箱、命令 policy、预算、JSONL trace  
2. **评测（P0）**：36 条 mini smoke + 9 条 repo 任务；裁判支持 `json_equals` / `yaml_contains` / `command_success` / `multi_assert`；`--runs N` + mean/std + **bootstrap 95% CI**  
3. **Agent 能力（P1）**：显式 Planner（`plan_act`）、L1 context compact（可审计 `context_compacted`）、只读 `subagent_task`（父子 trace 链接）

**事件 trace 示例（面试可打开 JSONL 演示）：**

- Plan-act 生命周期：`docs/examples/plan_act_events_redacted.jsonl` — 含 `plan_created` / `plan_updated` / `plan_replanned`（工具失败触发重规划）。
- LLM 流式事件：`docs/examples/llm_stream_events_redacted.jsonl` — 含 `message_delta` / `tool_call_delta` / `llm_stream_done` 片段，展示 streaming 与 `llm_complete` 的 usage/model 元数据。

**核心实验数字（面试可直接引用）：**

| 实验 | 配置对比 | 成功率 | 要点 |
|------|----------|--------|------|
| repo 任务 ×3 轮 | baseline vs hardened | **95.8%** vs **87.5%**（Δ -8.3%） | hardened 量化安全摩擦：policy block ↑、tool fail ↑ |
| mini 任务 | baseline vs context_compact | **88.9%** vs **91.7%**（Δ +2.8%） | 短任务 compact 未回归 |
| repo 任务 | subagent_readonly | **77.8%**（7/9） | `medium_subagent_cross_file` 触发 subagent，父子 trace 可链 |

**讲失败案例的顺序：**

1. `medium_rename_symbol` / `medium_subagent_cross_file` — 跨文件 bug，subagent 分析 vs 父 Agent 改错文件  
2. `easy_config_json` — 结构化裁判比关键词可靠  
3. `hard_report_transform` — 「能跑」≠「做对」

## D-1：外部基准 + 污染方法论（最强亮点，证明"我懂评估有效性"）

> 数字来源：`reports/report_20260626T101113.md`（干净 A/B）、`reports/contamination_probe.md`（污染探针）、`reports/report_20260626T194843.md`（scaffold 扩张后）、`docs/CONTAMINATION-NOTES.zh-CN.md`、`docs/changes/SOLID-D1-*-CLOSEOUT.zh-CN.md`。

**这条线讲的是"我能诊断一个评测到底可不可信"，比任何成功率数字都值钱。叙事按四步推进：**

1. **接外部基准**：把评测从自造任务升级到 **SWE-bench Lite 子集（10 任务 / 3 repo：sympy·flask·requests）**，可移植 env（`setup_swebench_envs.py`）、题面解法泄露清洗、gold patch 只进 `.oracle/` 不喂 Agent。
2. **干净单变量 A/B**：baseline(react) vs plan_act_permissive，**唯一差异是 mode/planner**。结果 **baseline 32% vs plan_act 24%，CI 重叠、无显著差异**。planner 没赢——但我没止步于"无差异"。
3. **怀疑数据、做污染探针**：发现 per-task 呈**双峰**（flask 恒过 / 多数 sympy 恒 0），这是污染指纹。于是复刻 *The SWE-Bench Illusion*：**只给 issue、不给 repo 结构，让模型猜改哪个文件**。一个没见过任务的模型不可能稳定答对仓库相对路径——实测 **池化 exact 54.2%、7/10 实例多数票命中正确文件 = 强 instance-level 记忆污染**。
   - **探针本身还暴露了两个测量陷阱并被我修掉**：① 推理模型在 `max_tokens=256` 下被截断，误记成"定位失败"；② `temperature=0` 仍非确定，单次结果在 50%–78% 晃 → 改为**重复采样 N=5 按命中频率聚合**。这两步是"我会做严谨测量"的直接证据。
4. **排除 confound、给 planner 最后机会**：质疑"planner 无差异是不是被紧预算/缺自测工具坑了"，于是**先补防作弊**（判定前从只读 fixture 恢复测试文件，否则开了 `run_command`+`write_file` 就能改测试假通过），再**扩 scaffold**（开自测工具 + 预算 30→40 步 / 超时翻倍，单变量对称）。重跑后 **planner 仍无统计优势**（CI 重叠），且步数从 22 涨到 35、自测在跑但绝对成功率没抬升——**印证瓶颈是"知道改哪却写不出修复"的真实难度 + 污染，不是 scaffold 饿出来的**。

**一句话收口这条线**：

> 我用一个近零成本的探针证明了这批任务被污染、绝对成功率不可作能力指标；又用一次受控的 scaffold 扩张排除了"配置不足"这个替代解释。所以我的结论不是"我的 agent 多强"，而是"**在这个数据条件下，planner 的相对收益不可辨识，原因是污染压缩了区分度**"——治本路径是 SWE-bench-Live / held-out repo（已写进未来工作），而不是继续堆 scaffold。

## 该怎么收束

> 我不是单纯在做一个会调用模型的脚本，而是在做一个 **能约束、能度量、能回归** 的 Agent 工程框架；P0/P1 已用真实跑分证明各机制的收益与代价。**而 D-1 进一步证明我不仅会"做"评测，还会"质疑"评测——主动识别污染、量化它、并诚实声明指标边界。**

## 若被追问「还缺什么」

- P2：LLM streaming/adapter、argv/Docker 沙箱（见 `docs/changes/CODEX-DEFERRED-GAPS.zh-CN.md` 中待 Codex 决策项）  
- 刻意未做：L2 LLM 总结、递归 subagent、多 worker
- **评测治本（已识别、列为未来工作）**：当前外部基准存在污染（探针实测强记忆），治本是接 **SWE-bench-Live**（post-2024 issue、月度刷新、有 Windows split、deepseek-v4-pro 已在榜）或自建 held-out repo——我选择"诚实标注 + 写清治本路径"而非为污染数据继续堆 scaffold（成本/收益不划算）。
