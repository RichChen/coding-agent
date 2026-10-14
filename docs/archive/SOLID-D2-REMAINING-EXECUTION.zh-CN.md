# Solid D-2 · 遗留修复 + 失败 Taxonomy + 多模型矩阵（Composer 执行）

> **执行模型**：Composer（机械实现 + 一次小规模 eval + git 提交）。  
> **范围**：本文**只做 4 件事**——① git 提交 D-1 全部落盘改动；② 修报告 Unstable Tasks 重复行 bug；③ 失败 taxonomy 自动生成；④ 多模型矩阵 eval。**不含**演示脚本（DEMO-SCRIPT）与 INTERVIEW-DEMO 大改（D-1 污染叙事已在上轮整合，勿覆盖）。  
> **上游**：`docs/SOLID-ROADMAP.zh-CN.md` §4 D-2 第 17–18 项；`docs/changes/SOLID-D1-SCAFFOLD-CLOSEOUT.zh-CN.md`（Phase 0 checkpoint 未提交）。  
> **环境**：`C:\Users\Administrator\.conda\envs\coding-harness\python.exe`；pytest 加 `--basetemp $env:TEMP\coding-harness-pytest`。  
> **基线**：当前 **145 passed**（含防作弊单测）；每项改动后保持全绿。

---

## 0. 背景（为什么要做）

| 项 | 现状 | 目标 |
|----|------|------|
| Git | D-1 防作弊 + scaffold + 污染探针等**全部只在工作区**，composer 环境 `git` 不在 PATH | 找到 git 可执行文件并提交，形成可复现 checkpoint |
| Unstable Tasks | 多 config 报告（如 baseline + plan_act）同一 task 出现**两次**，无 Config 列（见 `report_20260626T194843.md` 中 23117 重复） | 按 config 分列展示，不再像 bug |
| 失败 taxonomy | `docs/FAILURE-CASES.zh-CN.md` 为手工示例 | 从 eval CSV **自动生成**一页分类 + 代表任务 |
| 多模型矩阵 | 仅跑过 deepseek-v4-pro | 同 harness 跑 ≥2 模型，证 **harness 与模型解耦** |

---

## Phase 0 — Git 提交（D-1 全部落盘改动）

### 0.1 定位 git

当前 shell 里 `git` 可能不在 PATH。按序尝试：

```powershell
# 常见 Windows 安装路径
$gitCandidates = @(
  "git",
  "C:\Program Files\Git\bin\git.exe",
  "C:\Program Files (x86)\Git\bin\git.exe"
)
foreach ($g in $gitCandidates) { if (Get-Command $g -ErrorAction SilentlyContinue) { & $g --version; break } }
```

找到可用路径后，下文一律用 `$GIT` 代指（或把 git 目录临时加入本次 shell 的 PATH）。

### 0.2 提交范围

**应纳入本次 commit 的 D-1 工作**（若尚未提交）：

- 防作弊：`scripts/build_swebench_lite_subset.py`（`--refresh-protected`）、`datasets/swebench_lite_tasks.json`（`protected_paths`）、`src/eval/runner.py`（`_restore_protected_paths`）、`tests/test_runner.py`
- Scaffold：`src/config/schema.py`、`src/harness/factory.py`、`configs/baseline.yaml`、`configs/plan_act_permissive.yaml`
- 污染探针：`scripts/contamination_probe.py`、`reports/contamination_probe.md` + `.json`
- 文档：`docs/CONTAMINATION-NOTES.zh-CN.md`、`docs/changes/SOLID-D1-*-CLOSEOUT*.md`、`docs/SOLID-D1-*.md`、`docs/INTERVIEW-DEMO.zh-CN.md`（D-1 节）、`docs/SOLID-ROADMAP.zh-CN.md` 相关更新

**不要提交**：`.env`、`.swebench_envs/`、`.tmp/`、`traces/` 大体积产物（应在 `.gitignore` 中）。

### 0.3 命令

```powershell
cd D:\crq\src\coding-harness
& $GIT status
& $GIT diff --stat
& $GIT add -A
# 若 status 显示 .env 被 staged，git reset HEAD .env 后再 commit
& $GIT commit -m "$(cat <<'EOF'
feat(d1): SWE-bench subset, anti-cheat, scaffold expansion, contamination probe

- Restore protected test files from fixture before judging
- Enable run_command/edit_file with symmetric budget (max_steps=40)
- Add contamination probe with repeated sampling (reports/contamination_probe.md)
- Document evaluation validity limits (docs/CONTAMINATION-NOTES.zh-CN.md)

EOF
)"
& $GIT status
```

若 git 完全不可用：在 CLOSEOUT 中如实记录「未提交」及原因，**不阻塞** Phase 1–4。

### ✅ Phase 0 验收
- [ ] `git log -1` 可见上述 commit，或 CLOSEOUT 注明 git 不可用。

---

## Phase 1 — 修 Unstable Tasks 重复行 bug

### 1.1 根因

`src/eval/report.py` 在生成 `## Unstable Tasks` 时：

```python
for m in metrics_list:
    unstable.extend(unstable_tasks(m))
```

多 config 对比时，**同一 task_id 会被 baseline 与 plan_act 各追加一行**，表头又无 Config 列 → 读者误以为重复是 bug。

### 1.2 修复

1. 改为带 config 的元组：`(config_name, task_id, passes, runs)`。
2. 表头改为：`| Config | Task ID | Passes | Runs |`。
3. 仅当 `run_count > 1` 时输出该段（逻辑不变）。

示例：

```python
unstable: list[tuple[str, str, int, int]] = []
for m in metrics_list:
    for task_id, passes, runs in unstable_tasks(m):
        unstable.append((m.config_name, task_id, passes, runs))
# ...
for config_name, task_id, passes, runs in unstable:
    lines.append(f"| {config_name} | {task_id} | {passes} | {runs} |")
```

### 1.3 测试

在 `tests/test_runner.py` 的 `TestUnstableTasks` 或 `TestReportMetadata` 中新增：

- 构造 **两个** `RepeatedEvalMetrics`（baseline / plan_act），同一 task `t1` 在两边均为 1/2 通过。
- 生成报告后断言：`Unstable Tasks` 表含 **两行**，分别带 `baseline` 与 `plan_act`，且 **不含**无 Config 的旧格式重复歧义。

可选：对已有 `report_20260626T194843.csv` 用 `ReportGenerator` 重生成 md（若项目有从 CSV 回放工具则跳过；至少单测覆盖）。

### ✅ Phase 1 验收
- [ ] `python -m pytest tests/test_runner.py -q --basetemp $env:TEMP\coding-harness-pytest` 全绿。
- [ ] 新生成的双 config 报告中 Unstable 段含 Config 列，23117 类任务不再「无标识重复」。

---

## Phase 2 — 失败 taxonomy 自动生成（P0-4 B）

### 2.1 新建 `scripts/gen_failure_taxonomy.py`

**CLI**：

```bash
python scripts/gen_failure_taxonomy.py \
  --csv reports/report_20260626T194843.csv \
  --csv reports/report_20260626T101113.csv \
  --out reports/examples/failure_taxonomy.md
```

- `--csv` 可重复，合并多份 eval 结果（用于 scaffold vs REWORK 对照）。
- `--out` 默认 `reports/examples/failure_taxonomy.md`。

**输入 CSV 列**（与 `run_eval` 产出一致）：`config, run_index, task_id, success, expected_check, steps, elapsed_ms, tokens, tool_failures, policy_blocks, failure_reason, expected_failures, trace_file`。

**只统计「失败」行**：`expected_check == False`（或 CSV 里为 `False` 字符串）。成功行跳过。

**聚合维度**（Markdown 各一节）：

1. **按 `failure_reason`**：`step_limit` / `timeout` / `tool_error` / `model_parse_error` / `none`（agent 跑完但 judge 挂）/ 其他。计数 + 占比。
2. **按 assert 类型**（从 `expected_failures` 文本解析）：若含 `command_success failed` → `command_success`；`file_contains` / `multi_assert` 等同理；无法解析 → `unknown`。
3. **按 config**：baseline vs plan_act 失败率对比（可选，多 CSV 时尤其有用）。
4. **按 task_id Top N**：失败次数最多的任务 + 每类 1 代表行的 `failure_reason` + `expected_failures` 首行摘要（截断 120 字）。

**输出结构**（`failure_taxonomy.md`）：

```markdown
# Failure Taxonomy (auto-generated)
Generated: ...
Sources: report_....csv, ...

## By failure_reason
| Reason | Count | Share |

## By assert type (from expected_failures)
| Assert type | Count | Share |

## By config (if multiple)
| Config | Failures | Total rows | Fail rate |

## Representative tasks (top failures)
| Task ID | Config | Count | Dominant reason | Sample expected_failure |

## Notes
- 2–4 句解读：例如 scaffold 跑中 step_limit 占比高、tool_fail 与 run_command 自测相关等（基于真实计数写，勿编造）。
- 指向 `docs/CONTAMINATION-NOTES.zh-CN.md`：绝对成功率不作能力指标。
```

实现保持**纯 stdlib**（`csv` + `re` + `pathlib`），无 pandas 依赖。

### 2.2 测试 `tests/test_failure_taxonomy.py`

- 构造 5–10 行假 CSV（含 step_limit、command_success failed、多 config）。
- 跑 generator → 断言输出含预期 reason 计数、assert 类型、代表 task_id。

### 2.3 与手工文档关系

- **不删除** `docs/FAILURE-CASES.zh-CN.md`（保留 repo 任务叙事示例）。
- 在 `FAILURE-CASES.zh-CN.md` 末尾加一小节「自动生成 taxonomy」指向 `reports/examples/failure_taxonomy.md` 及 regen 命令（2–3 行即可）。

### ✅ Phase 2 验收
```bash
python scripts/gen_failure_taxonomy.py \
  --csv reports/report_20260626T194843.csv \
  --csv reports/report_20260626T101113.csv
python -m pytest tests/test_failure_taxonomy.py -q --basetemp $env:TEMP\coding-harness-pytest
```
- [ ] `reports/examples/failure_taxonomy.md` 存在，数字与 CSV 一致。
- [ ] 全量 pytest 仍绿。

---

## Phase 3 — 多模型矩阵 eval（P0-3 C）

### 3.1 目标

同 harness、同数据集、**仅 `llm.model` 不同**，横向对比成功率/步数/成本，证明 eval 基础设施与模型解耦。

### 3.2 新增 config

**`configs/baseline_modelB.yaml`**：从 `configs/baseline.yaml` 复制，**只改**：

```yaml
llm:
  model: "${LLM_MODEL_B:deepseek-chat}"
```

其余（runtime / policy / tools）与 baseline **完全一致**。若 `.env` 有 `LLM_MODEL_B` 则用之，否则默认 `deepseek-chat`（与 v4-pro 同 DeepSeek OpenAI 兼容端点，**无需第二 API key**）。

在 `.env.example` 增加注释行（可选）：

```
# Optional second model for matrix eval
# LLM_MODEL_B=deepseek-chat
```

### 3.3 报告：Model Matrix 段

`src/eval/report.py`：当 `run_metadata["configs"]` 中 **≥2 个不同 model** 且 `len(metrics_list) >= 2` 时，在 `## Mean Delta Comparison` 之后（或 Bootstrap 之前）插入：

```markdown
## Model Matrix

| Config | Model | Success Rate mean | Avg Steps | Avg Time (ms) | Total Tokens |
```

每行一个 config；Total Tokens 从 repeated runs 聚合（若已有 cost section 逻辑可复用）。

若只跑通单模型（第二模型 API 报错）：**仍输出表**，第二行标注 `n/a (run failed)`，**禁止伪造数据**。

### 3.4 Eval 命令（控制成本）

**不要用** `swebench_lite_tasks.json`（10 任务 × 2 模型太贵）。用轻量集：

```bash
python scripts/run_eval.py \
  --dataset datasets/repo_tasks.json \
  --configs baseline baseline_modelB \
  --runs 2 \
  --cost-per-1k 0.0
```

- `runs=2` 足够展示矩阵结构 + 初步方差；整轮远小于 SWE-bench 全量。
- 若 `baseline_modelB` 调用失败（模型名不可用）：在 CLOSEOUT 记录错误信息，保留 config + 报告占位，**不 retry 超过 1 次**。

### 3.5 测试

`tests/test_report.py` 或 `tests/test_runner.py`：

- 构造两个 `RepeatedEvalMetrics`，`run_metadata` 里 model 分别为 `model-a` / `model-b`。
- 生成报告 → 断言含 `## Model Matrix` 且两 model 均出现。

### ✅ Phase 3 验收
- [ ] `configs/baseline_modelB.yaml` 存在且仅 model 行与 baseline 不同。
- [ ] eval 产出 `reports/report_*.md` 含 Model Matrix 段。
- [ ] pytest 全绿；基线 **≥145 passed**（+ 新增 taxonomy / matrix 测试）。

---

## Phase 4 — 收尾

1. 更新 `docs/SOLID-ROADMAP.zh-CN.md`：
   - §3 P0-4 B 失败 taxonomy → ✅ + `reports/examples/failure_taxonomy.md`
   - §3 P0-3 C 多模型矩阵 → ✅ + 新报告路径（或「结构完成 + 单模型占位」）
   - §4 D-2 第 17–18 项标完成
2. 新增 `docs/changes/SOLID-D2-REMAINING-CLOSEOUT.zh-CN.md`：
   - Phase 0 git 结果
   - Unstable 修复说明
   - taxonomy 样例数字摘要
   - Model Matrix 两模型对比数字（或失败原因）
   - pytest 总数
3. **第二 commit**（Phase 1–4 完成后，若 Phase 0 已提交则分开；若 Phase 0 失败则本 commit 含全部）：
```powershell
& $GIT commit -m "feat(d2): failure taxonomy, model matrix, fix unstable tasks report"
```

---

## 边界 / 不做

- 不重跑 SWE-bench scaffold A/B（已完成，见 `report_20260626T194843.md`）。
- 不写 `DEMO-SCRIPT.zh-CN.md`、不大改 `INTERVIEW-DEMO.zh-CN.md`（D-1 叙事已整合）。
- §5 异常轮检测（402 免疫）**已在 D-1 返工完成**，本文不重复实现。
- 不伪造第二模型跑分；API 失败就诚实占位。

---

## 给 Composer 的一句话起点

> 按 `docs/SOLID-D2-REMAINING-EXECUTION.zh-CN.md` 执行四 Phase：**先找 git 并 commit D-1 全部落盘改动**（防作弊+scaffold+污染探针+文档）；再修 `report.py` Unstable Tasks 加 Config 列并补单测；再实现 `scripts/gen_failure_taxonomy.py` + 测试，对 `report_20260626T194843.csv` 与 `report_20260626T101113.csv` 生成 `reports/examples/failure_taxonomy.md`；再新增 `configs/baseline_modelB.yaml`（仅 model 不同）、`report.py` 的 Model Matrix 段，用 `repo_tasks.json` + `--runs 2` 跑双模型 eval（勿用 swebench 全集）；全量 pytest 保持绿；更新 ROADMAP 并写 `SOLID-D2-REMAINING-CLOSEOUT.zh-CN.md`；最后第二 commit D-2 改动。
