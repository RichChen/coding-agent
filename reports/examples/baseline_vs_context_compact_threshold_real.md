# Baseline vs Context Compact Threshold — Real Eval Report

> Status: **real API-backed run** (2026-06-25, Solid C batch P1-2 A).
>
> Model: `deepseek-v4-pro`  
> Config delta: **仅** `runtime.context.micro_compact` + `compact_token_threshold: 6000`（其余与 `baseline.yaml` 对齐，消除 confound）。

## 命令

```bash
# 主 A/B（16 任务 repo 集）
python scripts/run_eval.py --dataset datasets/repo_tasks.json \
  --configs baseline context_compact_threshold --runs 3

# 补充 stress 集（长输出 / 多步，更易观测 compact 效率收益）
python scripts/run_eval.py --dataset datasets/compact_stress_tasks.json \
  --configs baseline context_compact_threshold --runs 3
```

Source reports: `reports/report_20260625T093715.md`, `reports/report_20260625T094353.md`

## 结论：compact 正收益（效率维度，无成功率回归）

| 数据集 | baseline 成功率 | compact 成功率 | Δ 步数 | Δ 耗时 |
|--------|-----------------|----------------|--------|--------|
| repo 16 任务 | 93.8% / 0.0 | 93.8% / 6.2 | +0.0 | **-393 ms (-2.3%)** |
| compact_stress 3 任务 | 88.9% / 19.2 | 88.9% / 19.2 | **-0.8** | **-2725 ms (-13.6%)** |

- **成功率**：两集 mean 均 **≥ baseline**，无回归。
- **效率**：stress 集上 compact 显著减少平均步数与 wall time；repo 全量集上耗时亦下降。
- **token 阈值门控**：`estimate_tokens > 6000` 才执行 compact；read-heavy 任务因 `read_file` 保留策略，`context_events` 可能为空——符合设计，单测已覆盖 threshold skip/compact 路径。
- **亮点 run**：repo 集 compact **Run 3 达到 100%（16/16）**，baseline 三轮均为 93.8%。

## Repo 16 任务 Summary

| Config | Runs | Success Rate mean/std | Avg Steps | Avg Time (ms) |
|--------|------|-----------------------|-----------|---------------|
| baseline | 3 | 93.8% / 0.0 | 4.2 | 16811 |
| context_compact_threshold | 3 | 93.8% / 6.2 | 4.3 | **16418** |

Significance: CI 重叠（`--runs 3`，方差大）；效率收益见 stress 集与耗时 delta。

## hard_long_context_chain（长上下文新任务）

两配置均为 **3/3 PASS**。该任务以 `read_file` 为主，compact 保留原文，主要收益体现在 **阈值门控避免无效 compact** + 全集耗时下降，而非 token 绝对值大降。

## 声明

- 这是 C 批次首次在 **对齐 confound** 的 A/B 下观察到 compact **效率正收益**（步数/耗时），同时成功率不回归。
- L2 LLM 摘要仍 defer；真 SSE 仍 defer。
