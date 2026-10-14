# RepoSkillAgent 代码阅读顺序与问题清单模板

> 用途：帮助你系统地阅读当前项目代码，并在阅读过程中产出可复盘笔记。  
> 建议配合：`README.md`、`docs/current-evidence.md`、`docs/project-chronology.zh-CN.md`

---

## 一、推荐阅读顺序（先全局，再主链路，再机制）

### Step 0：先建立全局地图（30~60 分钟）

1. `README.md`
2. `docs/current-evidence.md`
3. `docs/project-chronology.zh-CN.md`

目标：先明确项目想证明什么、主结论来自哪一层评测、哪些是开发历史。

---

### Step 1：主执行链路（最重要）

1. `scripts/run_llm_ablation.py`
2. `reposkill_agent/eval/llm_ablation.py`
3. `reposkill_agent/eval/graph_runner.py`
4. `reposkill_agent/core/contracts.py`

目标：搞清一个 task 从输入到报告输出的完整生命周期。

---

### Step 2：Agent 协作层

1. `reposkill_agent/agents/manager.py`
2. `reposkill_agent/agents/locator.py`
3. `reposkill_agent/agents/llm_developer.py`
4. `reposkill_agent/agents/qa.py`（若存在）

目标：理解谁做决策、谁做定位、谁写 patch、谁判定失败。

---

### Step 3：LLM 接口与结构化输出

1. `reposkill_agent/llm/model_client.py`（或同名 client）
2. `reposkill_agent/llm/prompts.py`
3. `reposkill_agent/llm/schemas.py`

目标：理解 PatchPlan schema 如何约束模型行为，parse/repair 如何兜底。

---

### Step 4：机制核心（Skill / Memory / Router / Context）

#### 4.1 Skill
- `reposkill_agent/skills/models.py`
- `reposkill_agent/skills/retriever.py`
- `reposkill_agent/skills/validator.py`
- `reposkill_agent/skills/domain.py`
- `reposkill_agent/skills/library/*.md`

#### 4.2 Memory
- `reposkill_agent/memory/models.py`
- `reposkill_agent/memory/retriever.py`
- `reposkill_agent/memory/matching.py`
- `reposkill_agent/agents/memory_curator.py`

#### 4.3 Router + Context
- `reposkill_agent/eval/injection_policy.py`
- `reposkill_agent/core/context_expansion.py`

目标：理解 L5 为什么比 L2 有增益，以及增益来自哪些子机制。

---

### Step 5：Benchmark 与报告口径

1. `benchmarks/tasks/phase7_medium_48.yaml`
2. `reposkill_agent/eval/task_category.py`
3. `reposkill_agent/eval/report.py`
4. `reports/phase7-variance-summary.md`
5. `reports/phase7-positive-gain-summary.md`

目标：避免“只看分数不懂口径”。

---

### Step 6：测试回读（验证理解）

建议优先：
- `tests/test_injection_policy.py`
- `tests/test_mechanism_smoke.py`
- `tests` 下 skill/memory/context 相关测试

目标：看作者“最怕哪类回归”，反向理解设计边界。

---

## 二、带问题清单的阅读模板（可直接复制使用）

> 用法：每读一个文件，复制一段模板填写。问题数量可按文件复杂度增减，不要求固定。

### 文件阅读记录模板

```markdown
## [文件路径]

### 1) 文件职责
- 这个文件在系统中的唯一职责是什么？
- 它的上游调用方是谁？下游依赖是谁？

### 2) 关键类型 / 函数
- 关键类或函数：
- 每个函数的输入、输出、副作用：

### 3) 决策点（最重要）
- 这个文件在哪些地方“做了选择”？（例如：是否注入、是否replan、是否repair）
- 默认策略是什么？边界条件是什么？

### 4) 失败与兜底
- 可能失败在哪里？
- 失败后如何处理？（重试、降级、跳过、打标）

### 5) 指标与可观测性
- 这里产生或影响了哪些 metrics？
- 这些指标最终会出现在什么报告里？

### 6) 与 Phase 7.1 结果的关系
- 它对 L5-L2 的差值可能有什么影响？
- 它更可能影响哪个子类（skill_heavy / memory_heavy / context_heavy / multi_file_api）？

### 7) 我的疑问
- [ ] 疑问 1
- [ ] 疑问 2

### 8) 一句话总结
- 
```

---

## 三、核心文件专用问题（建议优先回答）

### A. `reposkill_agent/eval/graph_runner.py`

- TaskGraph 的节点顺序和终止条件是什么？
- replan 在什么条件下触发，最多几次？
- `needs_more_context` 如何触发 context expansion？
- 哪些 metrics 在这里汇总到 row 级结果？

### B. `reposkill_agent/eval/injection_policy.py`

- 每个 category 对应什么 augmentation policy？
- 为什么 `skill_primary` 与 `memory_primary` 要分离？
- context recovery 为什么常用 minimal route？
- 哪些 route 直接影响了 5.7→5.8 的修复？

### C. `reposkill_agent/skills/validator.py`

- evidence gating 的硬条件有哪些？
- domain mismatch 如何判定？
- negative transfer 的阈值和抑制逻辑是什么？
- `EVIDENCE_TAG_ALIASES` 如何影响 phase7 标签任务？

### D. `reposkill_agent/memory/matching.py`

- holdout 与 support 如何配对？
- procedural memory 的适用条件如何判断？
- `REPO_CONVENTIONS` 在提示中扮演什么角色？
- test signal 抽取规则会不会引入误导？

### E. `reposkill_agent/core/context_expansion.py`

- requested_context 从哪里提取？
- 扩路径规则有哪些（tests、same package、expected_files parent）？
- 每轮和总量限制如何防止越权读取？

### F. `reposkill_agent/llm/schemas.py` + `prompts.py`

- PatchPlan 结构字段是否足够表达多文件补丁？
- 哪些字段最容易导致 parse error？
- repair retry 的输入是否最小化、是否泄露风险低？

### G. `reposkill_agent/eval/llm_ablation.py`

- L0/L2/L5 实际打开了哪些能力开关？
- 哪些配置只在 L5 生效，可能带来方差上升？

### H. `reposkill_agent/eval/report.py`

- `success_rate`、`parse_err`、`skill_neg_transfer` 的统计口径是什么？
- by-category 是按 primary category 还是按 tag 包含？
- 这会如何影响 `multi_file_api` 的解读？

---

## 四、阅读输出模板（读完后写 1 页总结）

```markdown
# RepoSkillAgent 代码阅读总结（版本：YYYY-MM-DD）

## 1. 我理解的主链路
- 

## 2. 我理解的 L5 增益来源（按重要性排序）
1. 
2. 
3. 

## 3. 我理解的主要方差来源
- 

## 4. 还不确定的问题
- 

## 5. 若进入下一阶段，我会先做的三件事
1. 
2. 
3. 
```

---

## 五、推荐阅读节奏（可选）

- **Day 1**：Step 0 + Step 1（全局 + 主链路）
- **Day 2**：Step 2 + Step 3 + Step 4（agent + LLM + 机制）
- **Day 3**：Step 5 + Step 6（benchmark + 报告 + 测试）

如果时间紧，至少完成：
- `README.md`
- `eval/graph_runner.py`
- `eval/injection_policy.py`
- `skills/validator.py`
- `memory/matching.py`
- `reports/phase7-variance-summary.md`

---

## 六、常见误区提醒

- 不要只看 `reports/*.md`，一定要对照 `eval/*` 的统计口径。
- 不要把 tag 包含和 primary category 混为一谈。
- 不要把 `phase6_tiny_24` 结果当主证据。
- 不要用单次 run 下结论，优先看 Batch 5.10 的 mean +/- std。
