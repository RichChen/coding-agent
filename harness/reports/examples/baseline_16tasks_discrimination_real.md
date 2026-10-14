# Baseline 16-Task Discrimination — Real Eval Report

> Status: **real API-backed run** (2026-06-25, Solid C batch P0-1 C).
>
> Model: `deepseek-v4-pro` via DeepSeek OpenAI-compatible API  
> Command:
> ```bash
> python scripts/run_eval.py --dataset datasets/repo_tasks.json --configs baseline --runs 3
> ```
> Source report: `reports/report_20260625T090900.md`

Dataset: **16 tasks**（12 原任务 + 4 个 C 批次自造 hard：`hard_long_context_chain`、`hard_multi_step_locate`、`hard_regression_fix`、`hard_refactor_keep_green`）

## 区分度结论

| 指标 | B 批次（12 任务） | C 批次（16 任务） |
|------|-------------------|-------------------|
| baseline 成功率 mean/std | 94.4% / 4.8 | **91.7% / 3.6** |
| 撞顶风险 | 接近天花板 | **已拉开** |

- 整体成功率从 94.4% 降至 **91.7%**，恢复 config 间对比空间。
- 遗留 hard 任务 `hard_report_transform`：**0/3 PASS**（持续提供 hard 区分度）。
- C 批次 4 个新 hard 任务本轮 **12/12 PASS**（模型当前能力下偏易，但 oracle 与 multi_assert 校验有效）。
- flaky：`medium_multi_file_sync` **2/3**；`hard_report_transform` **0/3**。

## Summary

| Config | Runs | Tasks | Success Rate mean/std | Avg Steps mean/std | Avg Time mean/std (ms) |
|--------|------|-------|-----------------------|--------------------|------------------------|
| baseline | 3 | 16 | **91.7% / 3.6** | 4.3 / 0.3 | 19240 / 1608 |

## Per-Task Pass Matrix（节选 hard）

| Task ID | R1 | R2 | R3 | Passes |
|---------|----|----|-----|--------|
| hard_report_transform | F | F | F | 0/3 |
| hard_long_context_chain | P | P | P | 3/3 |
| hard_multi_step_locate | P | P | P | 3/3 |
| hard_regression_fix | P | P | P | 3/3 |
| hard_refactor_keep_green | P | P | P | 3/3 |
| medium_multi_file_sync | P | P | F | 2/3 |

## Tag 维度

| Tag | Success Rate | 说明 |
|-----|--------------|------|
| transform / csv / markdown | 0% | `hard_report_transform` 持续 FAIL |
| long-context / multi-step / regression / refactor | 100% | 新 hard 本轮全过 |
| repo | 93.8% | 16 任务聚合 |

## 声明

- `--runs 3`；结论受 API 方差影响，需结合 bootstrap CI。
- 区分度恢复主要来自 **任务集扩容 + 遗留 hard FAIL**，而非新 hard 任务本身的低通过率。
- Oracle 校验：`python scripts/check_dataset_oracle.py` → 7 任务 PASS。
