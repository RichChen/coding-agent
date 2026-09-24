# RepoSkillAgent 目录点击式索引（阅读顺序 + 时长 + 前置依赖）

> 用途：按“点目录就能读”的方式快速进入代码。  
> 约定：  
>
> - **时长** = 推荐首次阅读时间（不含深入调试）  
> - **前置依赖** = 先读哪些文件再读当前文件  
> - **检查点** = 读完后你应能回答的问题

---

## 0) 快速入口（5-10 分钟）

### `README.md`

- 时长：8 分钟
- 前置依赖：无
- 检查点：
  - 项目主结论是什么？
  - L0 / L2 / L5 各代表什么？
  - 主证据来自哪个报告？

### `docs/current-evidence.md`

- 时长：10 分钟
- 前置依赖：`README.md`
- 检查点：
  - 哪些结果是“主结论”，哪些只是历史？
  - 为什么不再用 tiny/hard 作为主结论？

### `docs/project-chronology.zh-CN.md`

- 时长：12 分钟
- 前置依赖：`README.md`
- 检查点：
  - 5.4 / 5.6 / 5.8 / 5.10 分别解决了什么问题？

---

## 1) 主链路（最优先，45-70 分钟）

### `scripts/run_llm_ablation.py`

- 时长：8 分钟
- 前置依赖：`README.md`
- 检查点：
  - repeats、seed、seed-memory 怎么传进 runner？
  - mock / real LLM 怎么切换？



### `reposkill_agent/eval/llm_ablation.py`

- 时长：18 分钟
- 前置依赖：`scripts/run_llm_ablation.py`
- 检查点：
  - L0-L5 配置如何映射能力开关？
  - repeat 的 memory 目录如何隔离/共享？



### `reposkill_agent/eval/graph_runner.py`

- 时长：30-40 分钟
- 前置依赖：`eval/llm_ablation.py`、`core/contracts.py`
- 检查点：
  - 一个 task 如何执行 inspect→locate→patch→test？
  - memory 何时检索、何时持久化？
  - needs_more_context 如何触发恢复？



### `reposkill_agent/core/contracts.py`

- 时长：12 分钟
- 前置依赖：无
- 检查点：
  - GraphRunResult / GraphMetrics 里有哪些关键字段？

---



## 2) 机制核心（建议按子系统分块读，90-140 分钟）



## 2.1 Skill 子系统



### `reposkill_agent/skills/models.py`

- 时长：10 分钟
- 前置依赖：无
- 检查点：SkillCard v2 包含哪些核心字段？



### `reposkill_agent/skills/domain.py`

- 时长：8 分钟
- 前置依赖：`skills/models.py`
- 检查点：domain mismatch 是如何定义的？



### `reposkill_agent/skills/retriever.py`

- 时长：10 分钟
- 前置依赖：`skills/models.py`
- 检查点：候选 skill 如何召回？



### `reposkill_agent/skills/validator.py`

- 时长：20 分钟
- 前置依赖：`skills/domain.py`、`skills/retriever.py`
- 检查点：
  - evidence gating 的拒绝条件有哪些？
  - negative transfer 如何抑制？



### `reposkill_agent/skills/library/*.md`

- 时长：20-30 分钟（挑 4-6 个先看）
- 前置依赖：`skills/validator.py`
- 检查点：每张 skill 卡覆盖哪类任务、避免哪类误用？



## 2.2 Memory 子系统



### `reposkill_agent/memory/models.py`

- 时长：6 分钟
- 前置依赖：无
- 检查点：MemoryHint v2 的最小注入单元是什么？



### `reposkill_agent/memory/matching.py`

- 时长：18 分钟
- 前置依赖：`memory/models.py`
- 检查点：
  - holdout-support 配对如何做？
  - test signal 如何提取？



### `reposkill_agent/memory/retriever.py`

- 时长：22 分钟
- 前置依赖：`memory/matching.py`
- 检查点：候选 memory 如何排序、裁剪、注入？



### `reposkill_agent/memory/episodic.py`

- 时长：8 分钟
- 前置依赖：无
- 检查点：episodic 落盘到哪些文件？



### `reposkill_agent/memory/procedural.py`

- 时长：6 分钟
- 前置依赖：无
- 检查点：procedural 记录何时追加？



### `reposkill_agent/memory/repo_profile.py`

- 时长：6 分钟
- 前置依赖：无
- 检查点：repo profile 是 map 结构还是单条记录？



### `reposkill_agent/memory/consolidator.py`

- 时长：14 分钟
- 前置依赖：`memory/*store.py`、`core/contracts.py`
- 检查点：run 结果如何转为 episodic/procedural/profile？



## 2.3 Router + Context + LLM 结构化输出



### `reposkill_agent/eval/injection_policy.py`

- 时长：20 分钟
- 前置依赖：`skills/validator.py`、`memory/retriever.py`
- 检查点：
  - 每个 category 对应什么注入策略？
  - warmup tasks 是怎么选出来的？



### `reposkill_agent/core/context_expansion.py`

- 时长：12 分钟
- 前置依赖：`eval/graph_runner.py`
- 检查点：扩路径规则与上限约束是什么？



### `reposkill_agent/llm/schemas.py`

- 时长：8 分钟
- 前置依赖：无
- 检查点：PatchPlan 关键字段有哪些？



### `reposkill_agent/llm/prompts.py`

- 时长：14 分钟
- 前置依赖：`llm/schemas.py`、`skills/validator.py`、`memory/retriever.py`
- 检查点：skills/memory/context 如何拼到 prompt？



### `reposkill_agent/agents/llm_developer.py`

- 时长：20 分钟
- 前置依赖：`llm/prompts.py`、`llm/schemas.py`
- 检查点：parse error / repair retry / needs_more_context 怎么处理？

---



## 3) 角色协作层（35-50 分钟）



### `reposkill_agent/agents/manager.py`

- 时长：8 分钟
- 前置依赖：`core/task_graph.py`
- 检查点：manager 负责哪些节点？



### `reposkill_agent/agents/locator.py`

- 时长：12 分钟
- 前置依赖：`core/context_expansion.py`
- 检查点：locator 输出如何影响后续 patch？



### `reposkill_agent/agents/developer.py`

- 时长：8 分钟
- 前置依赖：无
- 检查点：deterministic developer 与 LLM developer 的职责差异？



### `reposkill_agent/agents/qa.py`

- 时长：6 分钟
- 前置依赖：无
- 检查点：QA 判定结果如何回填？



### `reposkill_agent/agents/memory_curator.py`

- 时长：4 分钟
- 前置依赖：`memory/consolidator.py`
- 检查点：为什么仅成功 run 生成 procedural？

---



## 4) Benchmark 与报告口径（40-60 分钟）



### `benchmarks/tasks/phase7_medium_48.yaml`

- 时长：20 分钟
- 前置依赖：`eval/task_category.py`
- 检查点：
  - 各标签分布如何？
  - support/repeated 任务怎么标记？



### `reposkill_agent/eval/task_category.py`

- 时长：6 分钟
- 前置依赖：无
- 检查点：primary category 优先级是什么？



### `reposkill_agent/eval/report.py`

- 时长：16 分钟
- 前置依赖：`eval/llm_ablation.py`
- 检查点：
  - by-category 聚合口径如何定义？
  - mean/std 是怎么得出的？



### `reports/phase7-variance-summary.md`

- 时长：10 分钟
- 前置依赖：`eval/report.py`
- 检查点：为什么用 mean±std 而不是单次成绩？



### `reports/phase7-positive-gain-summary.md`

- 时长：8 分钟
- 前置依赖：`phase7-variance-summary.md`
- 检查点：最终叙事和 limitations 是否一致？

---



## 5) 脚本与基线补充（30-45 分钟）



### `scripts/run_phase6_ablation.py`

- 时长：8 分钟
- 前置依赖：`eval/ablation.py`
- 检查点：A0-A5 与 L0-L5 的关系是什么？



### `reposkill_agent/eval/ablation.py`

- 时长：12 分钟
- 前置依赖：`eval/graph_runner.py`
- 检查点：deterministic 层和 LLM 层的差异是什么？



### `scripts/run_external_baselines.py`

- 时长：8 分钟
- 前置依赖：`baselines/contracts.py`
- 检查点：optional baseline 的 skip-with-reason 在哪处理？



### `reposkill_agent/baselines/*`

- 时长：10-15 分钟
- 前置依赖：`scripts/run_external_baselines.py`
- 检查点：vanilla_deepseek、openhands、swe-agent、aider 的接入边界？

---



## 6) 测试索引（按阅读阶段回看）



### 6.1 读完主链路后

- `tests/test_graph_runner.py`
- `tests/test_llm_ablation.py`
- `tests/test_llm_call_state.py`



### 6.2 读完 Skill/Memory 后

- `tests/test_skills.py`
- `tests/test_skill_memory_v2.py`
- `tests/test_memory.py`
- `tests/test_memory_matching.py`
- `tests/test_injection_policy.py`



### 6.3 读完 Context/LLM 后

- `tests/test_context_expansion.py`
- `tests/test_llm_developer.py`
- `tests/test_llm_client.py`



### 6.4 读完 Benchmark 后

- `tests/test_phase7_benchmark.py`
- `tests/test_mechanism_smoke.py`

---



## 7) 两种可执行阅读路线



### 路线 A：3 天快速过主干

- Day 1：第 0 + 1 节
- Day 2：第 2 节（Skill/Memory/Router）
- Day 3：第 4 + 6 节（口径 + 测试验证）



### 路线 B：7 天深入

- D1：0 节（地图）
- D2：1 节（主链路）
- D3：2.1（Skill）
- D4：2.2（Memory）
- D5：2.3 + 3（Router/LLM/Agents）
- D6：4（benchmark+report）
- D7：5 + 6（baseline + tests 回归）

---



## 8) 读到一半卡住时，先看这 5 个文件

1. `reposkill_agent/eval/graph_runner.py`
2. `reposkill_agent/eval/injection_policy.py`
3. `reposkill_agent/skills/validator.py`
4. `reposkill_agent/memory/retriever.py`
5. `reposkill_agent/core/context_expansion.py`

这 5 个基本决定了 L5 的行为和方差来源。