# P0-4 展示材料改进记录

## 状态

已完成第四步最小交付：新增面试/交接用证据包，包括示例报告、红acted trace、失败案例分析和面试讲解稿。

注意：当前环境没有真实 API-backed eval 输出，因此本阶段新增的报告数字明确标注为 redacted example，不应作为最终实验结论使用。

## 新增文件

### 示例报告

- `reports/examples/baseline_vs_hardened_real.md`
- `reports/examples/baseline_vs_hardened_real.csv`

用途：

- 展示 baseline/hardened 报告应该长什么样。
- 展示 mean/std、delta、失败案例表格的讲法。
- 等真实 API 运行完成后，用真实报告替换其中的 placeholder 数字。

### 示例 trace

- `docs/examples/real_trace_redacted.jsonl`

用途：

- 展示一个 Agent run 的 step trace 结构。
- 包含 `read_file`、`write_file` 和 `run_summary`。
- 明确标注为 redacted example。

### 面试材料

- `docs/FAILURE-CASES.zh-CN.md`
- `docs/INTERVIEW-DEMO.zh-CN.md`

用途：

- 快速解释典型失败类型。
- 提供 30 秒和 2 分钟项目讲法。

## 验证命令

校验 JSONL 每行可解析：

```bash
python -c "import json; [json.loads(line) for line in open('docs/examples/real_trace_redacted.jsonl', encoding='utf-8') if line.strip()]; print('trace jsonl ok')"
```

校验 CSV 可解析：

```bash
python -c "import csv; rows=list(csv.DictReader(open('reports/examples/baseline_vs_hardened_real.csv', encoding='utf-8'))); print(len(rows), rows[0]['task_id'])"
```

## 后续替换真实结果的步骤

1. 配置真实 LLM API。
2. 运行：

```bash
python scripts/run_eval.py --dataset datasets/repo_tasks.json --compare --runs 3
```

3. 将生成的 Markdown/CSV 复制到 `reports/examples/`。
4. 从真实 trace 中选 1 条成功案例和 2-3 条失败案例，脱敏后替换 `docs/examples/real_trace_redacted.jsonl`。
5. 更新 `docs/FAILURE-CASES.zh-CN.md` 中的失败案例。

## 回退方式

如需回退本阶段改动，删除：

- `reports/examples/baseline_vs_hardened_real.md`
- `reports/examples/baseline_vs_hardened_real.csv`
- `docs/examples/real_trace_redacted.jsonl`
- `docs/FAILURE-CASES.zh-CN.md`
- `docs/INTERVIEW-DEMO.zh-CN.md`
- `docs/changes/P0-4-DEMO-PACK.zh-CN.md`

## 下一步建议

P0 四步已经形成闭环：

1. repo 级任务集
2. 严格裁判
3. repeated runs
4. 展示材料

下一阶段可以进入 P1-1：显式 Planner 最小版。
