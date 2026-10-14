# 新项目起跑说明：字节类 Agent 研发实习目标 + 旧项目边界

> 用途：给“另起炉灶”的新项目做统一底稿。  
> 目标：让新会话一读就知道，**目标 JD 是什么**、**旧项目已经做到了什么**、**新项目该往哪里走**。

---

## 1. 目标 JD 画像

这里的目标岗位可以概括成：**字节类 Agent 研发实习生**，偏“Agent 工程 + 多 Agent + 任务分解 + 评测”。

### 1.1 核心职责

- 构建高效、可靠的 AI Agent。
- 设计 Multi-Agent 系统，支持任务拆解、协作、合并与执行。
- 参与企业级 / 大规模产品的 prompt、工具、工作流优化。
- 参与 LLM Agent 系统研发，探索 planning、memory、skill、workflow。
- 对新方法做验证，不只是写 demo，而是能用指标和 trace 说清楚效果。

### 1.2 常见加分项

- 计算机基础扎实，能解释清楚系统、并发、工程化设计。
- 理解任务分解、自动化规划、Prompt Engineering、Agent 编排。
- 有 Agent / Multi-Agent / AIGC / IDE / 自动化脚本 / 开源项目经验。
- 结构化表达强，能说清楚取舍、边界和指标。
- 有论文、开源、竞赛、研究型项目经历更好。



### 1.3 面试官通常会问什么

- 你怎么让 Agent 更可靠？
- PlanAct 和 ReAct 的区别是什么？
- 为什么要 Multi-Agent，什么时候不该用？
- Skill 和 Memory 怎么设计，怎么检索，怎么更新？
- 评测怎么做，怎么证明不是运气？
- 失败时怎么定位，是模型问题、工具问题还是评测问题？

---



## 2. 旧项目是什么

旧项目 `coding-harness` 的一句话定位是：

> **可控、可观测、可评测的单 Agent Coding Harness。**

它解决的是 **Agent 工程基础设施**，不是完整的 Agent 平台。

### 2.1 已完成能力

- `AgentLoop`：plan-act-observe 单 Agent 循环。
- 工具链：`read_file`、`write_file`、`list_dir`、`run_command`、`search_replace`、`edit_file` 等。
- 沙箱与策略：路径隔离、命令白名单、预算、超时。
- 评测：repo 任务、SWE-bench 子集、multi_assert、bootstrap CI、失败 taxonomy。
- Trace：JSONL trace、事件流、context compact、plan trace、subagent trace。
- 真实 eval：baseline/hardened、plan_act、context compact、subagent readonly、多模型矩阵。



### 2.2 旧项目能力边界

旧项目强在：

- Harness / runtime / eval / trace / policy。
- 让 Agent **可测、可回放、可比较**。
- 把“策略改动”量化成成功率、步数、失败类型、成本。

旧项目不主打：

- 真正的多 Agent 平台化。
- 可持续的长期 memory 系统。
- 可复用 skill library 的自动演化。
- 复杂 DAG planner。
- 真 SSE / 完整产品级 cancel / Docker 隔离。

换句话说：

> 旧项目是“**底座和测量工具**”，不是“最终 Agent 产品”。

---



## 3. 旧项目适合怎么讲

适合讲成：

- 我先把运行时、沙箱、策略、trace、eval 做稳。
- 再逐步引入 Planner、Context、只读 Subagent。
- 用离线评测证明每个改动的收益和代价。

不适合讲成：

- 我已经做了一个完整的 Multi-Agent 平台。
- 我已经解决了长上下文、记忆、技能演化等所有问题。
- 我这个项目已经是生产级 Agent 系统。

---



## 4. 新项目应该做什么

如果你要另起炉灶，建议新项目的主题直接变成：

> **PlanAct + MultiAgent + Skill + Memory 的 Agent 能力项目。**

它不是在旧项目上继续加零件，而是把“Agent 会做事”作为主线。

### 4.1 推荐的新项目骨架

1. **Task Planner**
  - 输出结构化任务图，而不是固定三步计划。
  - 支持一次或少量 replan。
2. **Role-based Multi-Agent**
  - 先做 2 到 3 个角色。
  - 例子：Manager / Analyst / Developer / QA。
  - 每个子 Agent 有明确职责，不要一开始做大平台。
3. **Skill Library**
  - 把常见工作流沉淀成可加载 skill。
  - 例如：定位 import 错误、修测试、跨文件 rename、补回归测试。
4. **Memory System**
  - 先做 episodic memory 和 procedural memory。
  - 让 Agent 能从成功任务里抽取经验，下次复用。
5. **Evaluation**
  - 用一小批 repo 任务做 A/B。
  - 比较：
    - no memory vs memory
    - single agent vs multi-agent
    - no skill vs skill retrieval
  - 指标：success、steps、token、replan 次数、skill 命中率、失败类型。



### 4.2 新项目的合理边界

建议新项目只做：

- 研究型 / 原型型实现。
- 小而清晰的闭环。
- 能讲清楚“某个机制为什么有效”。

暂时不要做：

- 大而全 Agent OS。
- 复杂 UI。
- 完整企业平台化调度。
- 一上来就做多模型路由、分布式 worker、消息总线全套。

---



## 5. 旧项目 vs 新项目


| 维度   | 旧项目                                | 新项目                             |
| ---- | ---------------------------------- | ------------------------------- |
| 核心主题 | Harness / Eval / Trace             | Agent 能力本身                      |
| 关键词  | 可控、可观测、可评测                         | PlanAct、MultiAgent、Skill、Memory |
| 适合回答 | 怎么评测、怎么约束、怎么回归                     | 怎么规划、怎么协作、怎么沉淀经验                |
| 最强证据 | repo eval、SWE-bench、taxonomy、trace | skill/memory 是否提升任务成功率          |
| 风险   | 容易被问“是不是只是工程底座”                    | 容易做大做散、变成 demo                  |


---



## 6. 给新会话的起始提示

把下面这段直接贴到新项目会话里就够了：

```text
我要新建一个面向字节类 Agent 研发实习岗位的项目，主线是 PlanAct + MultiAgent + Skill + Memory。
请先阅读这份 brief：
1) 目标 JD 是构建可靠 Agent、支持任务分解与多 Agent 协作、做 prompt/skill/memory/评测。
2) 旧项目 coding-harness 已经做了 harness/eval/trace/policy/compact/read-only subagent，但不主打真正的多 Agent、长期 memory、skill 演化。
3) 新项目不要可以复刻旧项目的 harness 细节，但是可以适当利用，应该把重点放在 Agent 能力机制本身，并用小规模 repo 任务做 A/B 验证。
```

---



## 7. 一句话结论

旧项目负责证明你会做 **Agent 的基础设施**。  
新项目负责证明你会做 **Agent 的能力机制**。  
这两个项目放在一起，面试叙事会完整很多。