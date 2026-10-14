# SOLID D1 Scaffold 扩张 + 防作弊 + 重跑 A/B 收尾

日期：2026-06-26  
执行文档：`docs/SOLID-D1-SCAFFOLD-EXECUTION.zh-CN.md`

---

## 1) Phase 0 — 防作弊

### 改动文件

| 文件 | 变更 |
|------|------|
| `scripts/build_swebench_lite_subset.py` | `_protected_from_assertions()`、`refresh_protected_paths()`、`--refresh-protected` CLI；`make_task_entry()` 增加 `protected_paths` |
| `datasets/swebench_lite_tasks.json` | 10 个 swebench 任务均回填非空 `protected_paths` |
| `src/eval/runner.py` | `_restore_protected_paths()`；`agent.run()` 之后、判定之前调用 |
| `tests/test_runner.py` | `TestRestoreProtectedPaths`（覆盖篡改恢复 + 空列表 no-op） |

### protected_paths 生成逻辑

从 `expected.assertions[].command` 中用 `[\w./-]+\.py` 抽取 pytest 目标文件，去重、`\`→`/`。例如 24909 → `sympy/physics/units/tests/test_prefixes.py`。

### 验收

- `--refresh-protected`：10/10 非空 ✅
- pytest：**145 passed** ✅
- oracle：`All oracle solutions PASS` ✅
- **Checkpoint commit**：环境无 `git` 命令，**未提交**（改动已落盘）

---

## 2) Phase 1 — Scaffold 扩张（单变量）

### 代码

- `src/config/schema.py`：`CommandConfig.timeout_seconds: int = 30`
- `src/harness/factory.py`：`RunCommandTool(..., timeout_seconds=cmd_cfg.get("timeout_seconds", 30))`

### 两 config 同步值（除 mode/planner 外一致）

| 旋钮 | 新值 |
|------|------|
| `runtime.max_steps` | **40** |
| `runtime.step_timeout_seconds` | **240** |
| `runtime.total_timeout_seconds` | **1200** |
| `policy.command.timeout_seconds` | **180** |
| `tools.enabled` | + `run_command`, `edit_file` |

烟测（flask-4992 单任务）：trace 含 `edit_file` + `run_command`，无 tool not found ✅  
pytest：**145 passed** ✅

---

## 3) Phase 2 — 干净 A/B 结果

**报告**：`reports/report_20260626T194843.md`（runs=3，无 HTTP 402 / 无 degenerate 轮）

| 指标 | baseline | plan_act_permissive | Δ |
|------|----------|---------------------|---|
| Success rate mean/std | **20.0% / 10.0** | **26.7% / 5.8** | **+6.7%** |
| Avg steps mean/std | 35.1 / 1.7 | 34.6 / 1.7 | -0.5 |
| Avg time (ms) | 131784 | 129660 | -2124 |
| Tool fail rate | 40.2% | 37.6% | -2.6% |

**Bootstrap 95% CI**：baseline [10%, 30%]；plan_act [20%, 30%]  
**Significance**：CI 重叠 → **无显著差异**

**Per-Task 亮点**：

| 任务 | baseline | plan_act | 备注 |
|------|----------|----------|------|
| flask-4992 | **3/3** | 2/3 | 恒过任务仍强 |
| sympy-24213 | 1/3 | **3/3** | plan_act 更稳（污染+方差） |
| sympy-23117 | 2/3 | 2/3 | 两边均部分通过 |

### 与 REWORK 历史对照（`report_20260626T101113.md`，runs=5，旧 scaffold）

| 维度 | REWORK | Scaffold（本次） |
|------|--------|------------------|
| baseline 成功率 | 32.0% | 20.0% |
| plan_act 成功率 | 24.0% | 26.7% |
| 方向 | baseline > plan_act (-8%) | plan_act > baseline (+6.7%) |
| 显著性 | CI 重叠 | CI 重叠 |
| 平均步数 | ~22 | ~35 |
| step_limit 失败 | 常见（30 步墙） | 仍见 41/40 触顶 |
| tool_fail_rate | ~18% | ~40% |

**解读三连**：

1. **绝对成功率未因预算+自测明显抬升**——baseline 反而从 32% 降到 20%（runs 更少 + 方差 + 工具探索成本更高）；消除 step/timeout confound 后并未“刷分”。
2. **失败结构变化**：步数从 ~22 升到 ~35，tool_fail_rate 翻倍（run_command/edit_file 探索噪声）；仍有个别 step_limit 触顶，但主因已是能力/污染双峰而非纯预算墙。
3. **消除 confound 后 planner 翻不翻盘？→ 否（统计上）**  
   数值上 plan_act **+6.7%** 反超 baseline（与 REWORK 方向相反），但 **CI 重叠、runs=3 不足以宣称显著**；结合 `docs/CONTAMINATION-NOTES.zh-CN.md`，区分度仍被污染压缩，**不能得出「planner 在干净条件下显著更好」**。

---

## 4) 成本

- Total tokens：**7,489,722**（60 task-runs：10 tasks × 2 configs × 3 runs）
- Est. cost：n/a（未设 `--cost-per-1k`）
- 墙钟：约 **2.3h**（整轮 eval）

---

## 5) 结论

- **防作弊链路已就绪**：判定前从 fixture 恢复受保护测试文件，可安全启用 `run_command`/`write_file`/`edit_file`。
- **Scaffold 扩张完成**：单变量 discipline 保持；工具与预算对称。
- **A/B 最终答案**：在消除 step/timeout/工具 confound 后，**planner 未 statistically 翻盘**；方向性甚至与 REWORK 相反，进一步说明 **10 任务 × 强污染子集上 A/B 区分度不可靠**。
- **下一步（不在本 scope）**：SWE-bench-Live / held-out repo，而非继续堆 scaffold。
