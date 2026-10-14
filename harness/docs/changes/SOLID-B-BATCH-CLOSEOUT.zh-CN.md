# Solid B 层批次收尾（2026-06-25）

> 按 `docs/SOLID-B-BATCH-EXECUTION.zh-CN.md` 顺序完成 5 项 B/A 层加固。

## 测试

```bash
C:\Users\Administrator\.conda\envs\coding-harness\python.exe -m pytest tests -q --basetemp $env:TEMP\coding-harness-pytest
```

**结果：131 passed**（基线 112 → +19 新测）

## 逐项改动与证据

### P2-2 阶段A — argv 命令执行 + env 白名单

| 改动 | 路径 |
|------|------|
| `CommandPolicy.check_argv` | `src/policy/rules.py` |
| `run_command` 双模式 + `command_executed` 事件 | `src/tools/command.py` |
| `prefer_argv` / `env_whitelist` schema | `src/config/schema.py`, `src/harness/factory.py` |
| Config | `configs/hardened_argv.yaml` |
| 单测 | `tests/test_command.py` |
| 真实 eval | `reports/examples/hardened_argv_repo_tasks_real.md`（91.7%, 12 任务） |

### P0-1 A — 评测集扩到 12 + tag + oracle

| 改动 | 路径 |
|------|------|
| 新增 3 任务 + fixture | `easy_read_answer`, `medium_subagent_locate`, `medium_multi_file_sync` |
| `TaskResult.tags` + runner 透传 | `src/eval/metrics.py`, `src/eval/runner.py` |
| Success Rate by Tag | `src/eval/report.py` |
| Oracle CI 脚本 | `scripts/check_dataset_oracle.py` |
| 跳过 `.oracle` 复制 | `EvalRunner._copy_fixture_dir` |
| 单测 | `tests/test_dataset_oracle.py`, `tests/test_runner.py::TestTagGrouping` |
| 真实 eval | baseline 12/12 PASS · `reports/report_20260625T081337.md` |

### P0-2 B — AST 裁判 + flaky 检测

| 改动 | 路径 |
|------|------|
| `python_ast_valid` / `python_defines` | `src/eval/runner.py` |
| Unstable Tasks 报告段 | `src/eval/report.py` |
| 单测 | `tests/test_runner.py::TestAstJudges`, `TestUnstableTasks` |

### P1-1 B — suggested_tools + 结构化 replan + schema_ok 修复

| 改动 | 路径 |
|------|------|
| `PlanStep.suggested_tools` + 推进优先交集 | `src/runtime/planner.py` |
| `findings_provided` 弱校验修复 | `src/tools/subagent.py` |
| 单测 | `tests/test_planner.py`, `tests/test_subagent.py` |
| 真实 eval v2 | `reports/examples/baseline_vs_plan_act_permissive_v2_real.md`（94.4% vs **100.0%**） |

### P0-3 A — 实验元数据 + 显著性结论

| 改动 | 路径 |
|------|------|
| Run Metadata（commit/model/config-hash） | `scripts/run_eval.py`, `src/eval/report.py` |
| Significance 一句话 + delta CI 免责声明 | `src/eval/report.py` |
| 单测 | `tests/test_runner.py::TestReportMetadata` |
| 真实 eval | `reports/report_20260625T083221.md`（baseline vs hardened ×3，含 Significance） |

## Eval 报告索引

| 实验 | 报告 |
|------|------|
| hardened_argv（12 任务） | `reports/examples/hardened_argv_repo_tasks_real.md` |
| baseline 12 任务 | `reports/report_20260625T081337.md` |
| baseline vs hardened ×3 + 元数据 | `reports/report_20260625T083221.md` |
| plan_act_permissive v2 ×3 | `reports/examples/baseline_vs_plan_act_permissive_v2_real.md` |

## 未做 / 留 C 层

- 真 SSE streaming、cancel token（P2-1 C）
- L2 LLM 摘要、递归 subagent（CODEX defer）
- 外部 benchmark（P0-1 C）
- per-task 热力图、成本列（P0-3 B）
