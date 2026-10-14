# Solid D-2 · 收尾与展示闭环（Composer 2.5 用）

> **执行模型**：Composer 2.5（机械实现 + 文档，与 A/B/C 同性质）。  
> **与 D-1 的关系**：D-1（SWE-bench 接入，Codex 执行）见 `docs/SOLID-D1-SWEBENCH-EXECUTION.zh-CN.md`。**本文可与 D-1 并行**：用现有 eval 数据即可开工。仅 §3 演示脚本与 §4 文档收口的「区分度亮点」需要 D-1 的 SWE-bench 数字——若 D-1 尚未完成，先用占位标注，待 D-1 出数后回填（不阻塞其余实现）。  
> **上游**：`docs/SOLID-ROADMAP.zh-CN.md`、各批次 CLOSEOUT。  
> **环境**：`C:\Users\Administrator\.conda\envs\coding-harness\python.exe`；测试加 `--basetemp $env:TEMP\coding-harness-pytest`。  
> **基线**：当前 **139 passed**；每项改动后保持全绿。

---

## 0. 本文范围（5 项）

1. P0-4 B — 失败 taxonomy 自动生成
2. P0-3 C — 多模型矩阵 eval
3. P0-4 C — 演示脚本（30s + 2min）
4. 文档总收口 — INTERVIEW-DEMO 整合 A–D
5. **P0-1 D — 评测异常轮检测（402/provider 故障免疫）** ← 本次新增，**优先做（D-1 返工重跑依赖它）**

每完成 1 项：跑全量 pytest → 绿 → 在 `docs/SOLID-ROADMAP.zh-CN.md` §3/§4 对应行标完成日期与证据路径。

---

## 1. P0-4 B：失败 taxonomy 自动生成

**目标**：从 eval 输出自动产出一页失败分类，替代手工维护。

**实现**（`scripts/gen_failure_taxonomy.py`）

- 输入：一个或多个 eval CSV（`reports/*.csv`）。
- 按维度聚合失败：
  - `failure_reason`（timeout / tool_error / step_limit / model_parse_error / cancelled）。
  - `expected_failures` 文本归类（哪类 assert 最常挂：command_success / file_contains / ...）。
  - 按 `tags` 分组失败率。
- 输出 Markdown：`reports/examples/failure_taxonomy.md`——「失败类型分布表 + 每类 1–2 代表任务 + 推测原因」。

**测试**（`tests/test_failure_taxonomy.py`）

- 构造假 CSV → 产出 taxonomy 含预期分类与计数。

**验收**
```bash
python scripts/gen_failure_taxonomy.py --csv reports/report_20260625T095943.csv
```
产出 `reports/examples/failure_taxonomy.md`，分类与计数正确。

---

## 2. P0-3 C：多模型矩阵 eval

**目标**：同 harness、同数据集跑 ≥ 2 模型，证明 **harness 与模型解耦** + eval 能横向对比模型。

**实现**

- 新增 `configs/baseline_modelB.yaml`：**仅** `llm.model` 不同，其余与 `baseline.yaml` 对齐。
  - 模型 B 选 `.env` 里可用的另一型号。
- `scripts/run_eval.py` 已支持多 config：`--configs baseline baseline_modelB`。
- 报告增「Model Matrix」视角：同任务集下两模型的成功率/步数/成本对比（成本列 C 批次已支持）。

**诚实约束（重要）**

- 若环境**只有一个模型可用**：**不要伪造第二模型数据**。实现矩阵**结构**（config + report 段），用单模型跑通，报告明确标注「第二模型待接入，矩阵为结构占位」。

**测试**（`tests/test_runner.py`）

- 多 config 报告含 per-config model 列（基于已有 Run Metadata）。

**验收**
```bash
python scripts/run_eval.py --dataset datasets/repo_tasks.json \
  --configs baseline baseline_modelB --runs 3 --cost-per-1k 0.5
```
报告含双模型对比（或单模型 + 占位说明）。

---

## 3. P0-4 C：演示脚本（30s + 2min）

**产物**（`docs/DEMO-SCRIPT.zh-CN.md`）

- **30 秒版**：一句话定位（可控/可观测/可评测的单 Agent Coding Harness）+ 3 个最强证据点：
  - plan_act 单变量 **+5.6%**（无 confound）
  - compact 效率 **-13.6% 耗时**（成功率不回归）
  - SWE-bench 区分度（**数字待 D-1 回填**；未完成时写「真实 benchmark 区分度，见 swebench_lite_real.md」占位）
- **2 分钟版**：
  1. 架构一句话（loop / policy / eval / trace）。
  2. 现场跑一个任务（给命令），打开 events JSONL 走查 `plan_created → plan_updated → run_end`。
  3. 展示一份对比报告（含 bootstrap CI + significance 结论）。
  4. 失败案例：打开 `failure_taxonomy.md`（§1 产物）讲一个 flaky 任务及应对。
- 每步标注「打开哪个文件 / 跑哪条命令 / 讲什么」，可直接照读。

**验收**：脚本内引用的文件/命令真实存在且可跑；30s/2min 两版自洽；SWE-bench 处若 D-1 未完成则保留占位标记。

---

## 4. 文档总收口：INTERVIEW-DEMO 整合 A–D

**改 `docs/INTERVIEW-DEMO.zh-CN.md`**

- 整合 A–D 全部关键证据为**最终面试材料**：
  - 能力矩阵（plan_act / context / subagent / policy / streaming）+ 各一句话 + 证据路径。
  - 三个数字亮点：plan_act +5.6%、compact -13.6% 耗时、SWE-bench 区分度（D-1 数字回填）。
  - 工程深度点：argv 安全边界、错误分类驱动 retry、cancel token、成本可观测。
  - 指向 `DEMO-SCRIPT.zh-CN.md`、`SOLID-ROADMAP.zh-CN.md`、`failure_taxonomy.md`。
- `docs/SOLID-ROADMAP.zh-CN.md` 顶部状态区标注「A–D 批次完成」（D-1 完成后再标全）。

**验收**：INTERVIEW-DEMO 自成闭环，5 分钟可看懂项目全貌与证据。

---

## 5. P0-1 D：评测异常轮检测（402/provider 故障免疫）

**背景**：D-1 打磨重跑时，`plan_act_permissive` 的 run3~run5 因 `HTTP 402 Insufficient Balance` 整轮坍塌（每个任务 1 步、~440ms、0/10），但报告把这些“故障轮”当真实数据算进 mean/std/CI，得出**方向错误**的“倾向显著”。必须让评测对 provider 故障免疫：自动识别异常轮、从统计中剔除、并显式标注。

**目标**：再遇 402/429/5xx 整轮坍塌时，报告**不被污染**，且能一眼看出“有 N 轮异常已剔除”。

### 5.1 异常轮判据（`src/eval/metrics.py`）

per-run 对象为 `EvalMetrics`，已有 `success_rate`(float) / `avg_steps`(float) / `model_error_count`(int) / `total_tasks`。新增纯函数：

```python
def is_degenerate_run(run: EvalMetrics, *, step_floor: float = 1.5) -> bool:
    """整轮坍塌判定：几乎没推进就全挂，强烈暗示 provider 故障而非模型能力。"""
    if run.total_tasks == 0:
        return False
    near_zero_progress = run.avg_steps <= step_floor      # 平均 1 步左右
    all_failed = run.success_rate == 0.0
    model_error_heavy = run.model_error_count >= max(1, run.total_tasks // 2)
    return all_failed and (near_zero_progress or model_error_heavy)
```

> 判据偏保守：要求“成功率=0”且（“几乎没推进”或“过半 model_error”），避免把“真实全失败但有充分尝试”的硬轮误杀。

### 5.2 聚合层剔除（`src/eval/metrics.py` 的 `aggregate`）

当前 `aggregate` 用 `runs` 全量算 mean/std 与 `success_rate_ci = bootstrap_mean_ci([m.success_rate for m in runs])`。改为：

- 计算 `valid_runs = [r for r in runs if not is_degenerate_run(r)]`、`degenerate_runs = 其余`。
- **mean/std/CI/avg_steps 等统计全部基于 `valid_runs`**。
- `RepeatedEvalMetrics` 新增字段：`degenerate_run_indices: list[int]`（1-based，对应原始 runs 顺序）、`valid_run_count: int`。
- **保留 `runs` 全量**（Per-Run Results 仍展示所有轮，含异常轮，只是打标）。
- 边界：若 `len(valid_runs) < 2`，仍可出 mean，但 `success_rate_ci` 置 `None`（CI 无意义），交由报告层标注“有效轮不足，显著性 withheld”。

### 5.3 报告层（`src/eval/report.py`）

1. 新增 **「## Anomalous Runs」** 段（仅当存在异常轮时）：

```
## Anomalous Runs
> 检测到 N 个异常轮（疑似 provider 故障：成功率=0 且几乎无推进/高 model_error），已从均值/方差/CI 中剔除。
| Config | Run | Success Rate | Avg Steps | Model Errors | 判定 |
```

2. **Repeated Run Summary 增列或脚注**：标注 `有效轮 valid/total`（如 `5/5` 或 `2/5`）。
3. `significance_conclusion()`：当任一 config `valid_run_count < 2` 或 `success_rate_ci is None` 时，返回 `"有效轮不足（含异常轮剔除），显著性结论 withheld，请补跑。"`，**不得**输出“倾向显著”。
4. Per-Run Results 表给异常轮加标记列（如末列 `⚠ degenerate`）。

### 5.4 测试（`tests/test_report.py` 或 `tests/test_metrics.py`）

- 构造 5 个 run 的 `RepeatedEvalMetrics`，其中 3 个 `success_rate=0, avg_steps=1.0` → 断言：
  - `is_degenerate_run` 命中那 3 个、未误伤正常轮。
  - 聚合后 mean 仅基于 2 个有效轮；`degenerate_run_indices == [3,4,5]`。
  - `valid_run_count == 2` 时 `success_rate_ci is None`，报告出现 “withheld” 而非“倾向显著”。
- 构造“真实全失败但 avg_steps=15”的轮 → 断言**不**判为异常（避免误杀硬轮）。

**验收**
```bash
python -m pytest tests/test_metrics.py tests/test_report.py -q --basetemp $env:TEMP\coding-harness-pytest
```
全绿；用旧的 `report_20260625T180202.csv` 复算时，run3~5 被标异常并从显著性中剔除。

---

## 6. 收尾

- 全部完成后：全量 `pytest tests -q` 绿；更新 `docs/SOLID-ROADMAP.zh-CN.md` §3/§4（标 D-2 项完成，含 §5 异常轮检测）。
- 新增 `docs/changes/SOLID-D2-CLOSEOUT.zh-CN.md`：实际改动、测试数、报告路径、未做项。
- 与 D-1 协调：演示脚本与 INTERVIEW-DEMO 的 SWE-bench 数字，待 D-1 返工重跑出数后回填确认。

## 7. 不在本文范围

- SWE-bench 接入与返工（见 D-1 / D-1-REWORK）。
- 真 SSE、L2 摘要、多 worker、P2-2 Docker（仍 defer）。

## 8. 给 Composer 的一句话起点

> 按 `docs/SOLID-D2-CLOSEOUT-EXECUTION.zh-CN.md` 执行收尾 5 项。**先做 §5 异常轮检测**（D-1 返工重跑依赖它免疫 402）：在 `metrics.py` 加 `is_degenerate_run` 并让 `aggregate` 的 mean/std/CI 只基于有效轮、保留全量 runs 打标，`report.py` 加「Anomalous Runs」段且有效轮不足时显著性 withheld，配 `test_metrics.py/test_report.py`。再做失败 taxonomy 自动化、多模型矩阵、演示脚本、INTERVIEW-DEMO 整合。可与 D-1 并行；SWE-bench 数字先占位待回填；单模型环境多模型矩阵只做结构 + 占位，不伪造数据。每项做完跑全量 pytest 保持绿（基线 139）；conda 解释器见抬头；完成后更新 ROADMAP 并写 CLOSEOUT。
