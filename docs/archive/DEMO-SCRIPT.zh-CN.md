# 演示脚本（30s + 2min）

> 数字与路径见 `docs/INTERVIEW-DEMO.zh-CN.md` §证据索引；全项目地图见 `docs/SOLID-ROADMAP.zh-CN.md`。

---

## 30 秒版（背下来）

这是一个**可控、可观测、可评测**的单 Agent Coding Harness：配置驱动 loop + policy + 离线 eval + JSONL trace，在模型不可信的前提下量化策略改动。

三条硬证据：**① 机制有效**——同策略单变量 plan_act，repo 12 任务 baseline 94.4% vs plan_act 100%，Δ **+5.6%**（`reports/examples/baseline_vs_plan_act_permissive_v2_real.md`）。**② 效率**——context compact 在 stress 集耗时 **-13.6%**、步数 -0.8，成功率不回归（`reports/examples/baseline_vs_context_compact_threshold_real.md`）。**③ 评估有效性（最强）**——接 SWE-bench Lite 子集后，污染探针 5×重复池化 exact **54.2%**、7/10 多数票定位（无 repo 结构 = 强记忆）；干净 A/B planner **无统计优势**（32% vs 24%，scaffold 后 20% vs 27%，CI 均重叠）；绝对成功率**不作能力指标**（`docs/CONTAMINATION-NOTES.zh-CN.md`）。

---

## 2 分钟版（逐步操作）

### Step 0 — 开场（15s）

「模型会幻觉、会抄测试、会撞预算——harness 的工作是约束工具、记录 trace、用离线 eval 量化策略。今天走一遍：架构 → 单任务 → trace → 报告 → 失败 taxonomy → D-1 污染叙事。」

### Step 1 — 架构速览（20s）

打开或指这四个入口：

| 文件 | 一句话 |
|------|--------|
| `src/runtime/loop.py` | plan-act-observe 主循环 |
| `src/eval/runner.py` | 批量 eval + 判定 + 防作弊 restore |
| `src/tracing/logger.py` | JSONL 逐步 trace |
| `configs/baseline.yaml` | YAML 配置驱动（Pydantic 校验） |

### Step 2 — 现场跑单任务（40s）

**推荐（零成本、不调 SWE-bench）**：

```powershell
cd D:\crq\src\coding-harness
C:\Users\Administrator\.conda\envs\coding-harness\python.exe scripts/run_single.py ^
  "Create hello.py that prints Hello, World!" ^
  --config configs/plan_act_permissive.yaml
```

预期：终端打印 `success=True`、步数与 token；`traces/` 下生成新 JSONL（文件名含时间戳）。

若现场网络不稳，**跳过本步**，直接 Step 3 用脱敏 trace。

### Step 3 — 打开 trace 走查（25s）

打开 `docs/examples/plan_act_events_redacted.jsonl`，指三类 event：

1. `plan_created` — 首轮注入计划  
2. `plan_updated` — 步进后 plan 刷新进 messages  
3. `plan_replanned` — 工具失败后重规划  

（可选：`docs/examples/llm_stream_events_redacted.jsonl` 展示 streaming 元数据。）

### Step 4 — 展示 eval 报告（30s）

打开 **`reports/report_20260626T101113.md`**（SWE-bench 干净 A/B，runs=5）：

- **Repeated Run Summary**：baseline **32.0%** vs plan_act **24.0%** → 指 **Bootstrap 95% CI** 与 **Significance: CI 重叠**  
- 口播：「这是外部基准上的单变量对比，但 CI 重叠 → planner 无统计优势；且后面会讲为什么不能把 32% 当能力指标。」

（若时间充裕，可另开 `reports/report_20260627T033945.md` 指 **Model Matrix**：v4-pro **96.9%** vs deepseek-chat **87.5%**，证 harness 与模型解耦。）

### Step 5 — 失败与 taxonomy（20s）

打开 **`reports/examples/failure_taxonomy.md`**：

- **By failure_reason**：`step_limit` **47.5%**、`none`（agent 跑完 judge 挂）**38.4%**  
- 口播：「scaffold 开了自测后，撞步数墙和 pytest 仍失败是主因——不是『没跑起来』，是『跑完仍不对』。」

### Step 6 — 收束（10s）

「最强亮点在 D-1 方法论：探针量化污染 + 防作弊 + 排除 scaffold confound 后 planner 仍 null——见 `docs/CONTAMINATION-NOTES.zh-CN.md` 与 `docs/INTERVIEW-DEMO.zh-CN.md` D-1 节。」

---

## 附录：常用命令

```powershell
# 单任务 debug（plan_act）
python scripts/run_single.py "Create hello.py that prints Hello, World!" --config configs/plan_act_permissive.yaml

# repo 任务批量 eval（勿现场默认跑 SWE-bench 全量）
python scripts/run_eval.py --dataset datasets/repo_tasks.json --configs baseline --runs 2

# 失败 taxonomy 再生
python scripts/gen_failure_taxonomy.py ^
  --csv reports/report_20260626T194843.csv ^
  --csv reports/report_20260626T101113.csv

# 污染探针（≈零成本，离线 gold）
python scripts/contamination_probe.py --dataset datasets/swebench_lite_tasks.json

# 全量 pytest
python -m pytest tests -q --basetemp $env:TEMP\coding-harness-pytest
```

（Windows 上请将 `python` 换为 `C:\Users\Administrator\.conda\envs\coding-harness\python.exe`。）

---

## 附录：若被追问

**Q：planner 在 SWE-bench 为什么不显著？**  
A：两层原因——① 干净 A/B（REWORK 32% vs 24%）与 scaffold A/B（20% vs 27%）**CI 均重叠**；② 探针证明强 instance 记忆，区分度被污染压缩，小样本上 planner 增益淹没在噪声里。repo 自造任务上同策略单变量 **+5.6%** 只证明**机制**有效，不能外推到 SWE-bench。

**Q：污染怎么办？**  
A：绝对成功率不作能力指标；相对 A/B 在「污染对两边对称」假设下仍有讨论价值。治本：SWE-bench-Live / held-out repo（见 `docs/CONTAMINATION-NOTES.zh-CN.md` §5）。

**Q：hardened 为何降成功率？**  
A：repo 任务 baseline 95.8% vs hardened 87.5%（历史实验）——policy block 与 tool fail 上升是**可量化的安全摩擦**，不是 bug。

**Q：402 / 异常轮怎么处理？**  
A：`is_degenerate_run` 剔除疑似 provider 故障轮，报告 **Anomalous Runs** 段；勿把作废报告 `report_20260625T180202.md` 当结论。

**Q：多模型矩阵说明什么？**  
A：同 harness、只改 `llm.model`，v4-pro **96.9%** vs chat **87.5%**（repo 16，runs=2）——基础设施与模型解耦，换模型不必改 eval 脚本。
