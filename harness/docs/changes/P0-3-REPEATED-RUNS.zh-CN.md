# P0-3 重复运行统计改进记录

## 状态

已完成第三步最小交付：`run_eval` 支持重复运行，报告支持 mean/std，CSV 展开到 run 级别。

本阶段没有实现 bootstrap CI，也没有继续进入 Planner / Context / Agent-as-Tool。

## 改动范围

### Metrics

修改 `src/eval/metrics.py`：

- 保留原有 `EvalMetrics`，兼容单次运行。
- 新增：
  - `MetricStats`
  - `RepeatedEvalMetrics`
  - `aggregate_repeated_metrics()`

`RepeatedEvalMetrics` 统计字段：

- `success_rate.mean/std`
- `avg_steps.mean/std`
- `avg_elapsed_ms.mean/std`
- `avg_tokens.mean/std`
- `tool_failure_rate.mean/std`
- `policy_block_count.mean/std`

### EvalRunner

修改 `src/eval/runner.py`：

- `run_all(configs, judge_fn=None, runs=1)`
- `runs=1` 时保持旧行为。
- `runs>1` 时对每个 config 重复执行多次，返回 repeated metrics。

### ReportGenerator

重写 `src/eval/report.py`：

- 单次运行：保持原有 summary / failure breakdown / per-task results。
- 重复运行：输出 repeated run summary、mean/std、per-run results。
- CSV 增加 `run_index` 列。
- 报表中的 PASS/FAIL 改为 ASCII，避免乱码。

### CLI

修改 `scripts/run_eval.py`：

- 新增 `--runs` 参数。
- stdout 兼容单次/重复运行两种模式。

### 测试

修改 `tests/test_runner.py`：

- 增加 repeated metrics 聚合测试。
- 增加 repeated report 生成测试。

## 验证命令

建议运行：

```bash
python -m pytest tests/test_runner.py -q --basetemp .pytest_tmp
```

检查 CLI 帮助：

```bash
python scripts/run_eval.py --help
```

## 回退方式

如需回退本阶段改动：

1. 在 `src/eval/metrics.py` 中删除：
   - `MetricStats`
   - `RepeatedEvalMetrics`
   - `_stats`
   - `aggregate_repeated_metrics`
2. 在 `src/eval/runner.py` 中把 `run_all` 恢复为单次聚合。
3. 恢复旧版 `src/eval/report.py` 单次报告逻辑。
4. 从 `scripts/run_eval.py` 删除 `--runs`。
5. 从 `tests/test_runner.py` 删除 repeated metrics / repeated report 测试。

## 下一步建议

如果要继续按方案推进，下一步应做 P0 的收尾：

- 用 `--runs` 跑一份 baseline/hardened 的轻量对比。
- 如果需要，再补 bootstrap CI，但这不属于本次最小交付。
