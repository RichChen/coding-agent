# 方案 A 收尾记录（P0 缺口 + 展示同步）

## 状态

已完成方案 A 全部项（2026-06-25）。

## 1. 裁判补强

### `command_output` 校验 exit code

- `src/eval/runner.py`：默认 `require_exit_zero: true`
- 非零 exit 判 FAIL，即使 stdout 含关键词
- 可显式 `require_exit_zero: false` 保持旧行为

### `yaml_contains`

- 解析 YAML 文件，在 dump 文本中检查 keywords
- 测试：`tests/test_runner.py::TestEnhancedJudges::test_yaml_contains`

## 2. Bootstrap 95% CI

新增：

- `src/eval/bootstrap.py`
- `tests/test_bootstrap.py`

集成：

- `RepeatedEvalMetrics.success_rate_ci`（run 级 resampling）
- 报告 Markdown：`Bootstrap 95% CI` 段（单 run 为 per-task；重复 run 为 run resampling + 可选 delta CI）

## 3. 长任务 compact 专项

新增：

- `datasets/compact_stress_tasks.json`（3 条 hard 任务）
- `tests/fixtures/repos/hard_multi_read_chain/`（多文件阅读链）

真实 eval 见 `reports/examples/baseline_vs_context_compact_stress_real.md`（2026-06-25 跑分：3 任务 baseline/context_compact 均为 66.7%，无回归）。

## 4. 文档同步

- `docs/INTERVIEW-DEMO.zh-CN.md` — 同步真实跑分数字
- `docs/changes/CODEX-DEFERRED-GAPS.zh-CN.md` — 四类待 Codex 决策缺口

## 5. 验证

```bash
C:\Users\Administrator\.conda\envs\coding-harness\python.exe -m pytest tests -q
python scripts/run_eval.py --dataset datasets/compact_stress_tasks.json --configs baseline context_compact
python scripts/run_eval.py --dataset datasets/repo_tasks.json --compare --runs 3
```

## P0 缺口闭合状态

| 项 | 状态 |
|----|------|
| bootstrap CI | ✅ |
| yaml_contains | ✅ |
| command_output exit code | ✅ |
| INTERVIEW-DEMO 数字 | ✅ |
| 长任务 compact eval | ✅（compact_stress_tasks） |
