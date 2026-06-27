# SOLID D-2 遗留项收尾

日期：2026-06-27  
执行文档：`docs/SOLID-D2-REMAINING-EXECUTION.zh-CN.md`

---

## Phase 0 — Git（D-1 checkpoint）

- **发现**：`.git` 目录为空，非有效仓库；使用 `C:\Program Files\Git\bin\git.exe` 执行 `git init` 重建。
- **Commit 1**：`b4e14f2` — `feat(d1): SWE-bench subset, anti-cheat, scaffold expansion, contamination probe`
- **Commit 2**：`aeb4ee6` — `feat(d2): failure taxonomy, model matrix, fix unstable tasks report`（5 个 D-2 专属文件；`report.py` / `test_runner.py` 等共享改动含于 commit 1）

---

## Phase 1 — Unstable Tasks 修复

- **根因**：多 config 报告对每 config 各输出 unstable 行，但无 Config 列。
- **修复**：`src/eval/report.py` 改为 `(config_name, task_id, passes, runs)`，表头 `| Config | Task ID | Passes | Runs |`。
- **测试**：`TestUnstableTasks.test_unstable_tasks_table_includes_config_column`

---

## Phase 2 — 失败 taxonomy

- **脚本**：`scripts/gen_failure_taxonomy.py`（stdlib only）
- **产出**：`reports/examples/failure_taxonomy.md`（99 失败行，来源 scaffold + REWORK CSV）
- **摘要**：
  - `step_limit` **47.5%** · `none`（judge 挂）**38.4%** · `timeout` 12.1%
  - assert 类型 100% 为 `command_success`（SWE-bench pytest 判定）
  - baseline / plan_act 失败率 62.5% / 61.3%
- **测试**：`tests/test_failure_taxonomy.py`

---

## Phase 3 — 多模型矩阵

- **Config**：`configs/baseline_modelB.yaml`（仅 `llm.model: ${LLM_MODEL_B:deepseek-chat}` 不同）
- **报告段**：`## Model Matrix`（≥2 不同 model 时插入）
- **Eval**：`datasets/repo_tasks.json` · `--configs baseline baseline_modelB` · `--runs 2`
- **报告**：`reports/report_20260627T033945.md`

| Config | Model | Success Rate mean | Avg Steps | Total Tokens |
|--------|-------|-------------------|-----------|--------------|
| baseline | deepseek-v4-pro | **96.9%** | 6.4 | （见报告） |
| baseline_modelB | deepseek-chat | **87.5%** | 10.1 | （见报告） |

两模型均成功调用，harness 与模型解耦得证（同 config 结构、不同 model 字段即可横向对比）。

---

## 验收

- pytest：**148 passed**
- 无 HTTP 402

---

## 结论

D-2 遗留 17–18 项（失败 taxonomy + 多模型矩阵）与 Unstable 报告 bug 修复均已完成；git 由空仓库重建并完成双 commit。
