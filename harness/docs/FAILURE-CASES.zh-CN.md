# 失败案例分析

> 说明：以下是基于当前 repo 级任务设计的红acted 示例，不是线上真实统计。

## 1. `medium_rename_symbol`

- 现象：测试在 import 阶段失败，helper 函数名未对齐。
- 典型原因：模型改了调用方，但没改定义方。
- 说明：这类失败适合展示 trace，因为问题通常能在第一轮 `read_file` 后定位到跨文件符号不一致。

## 2. `hard_cross_file_api`

- 现象：返回格式改对了，但缺失用户路径仍然抛错。
- 典型原因：只修了 happy path。
- 说明：这类任务能说明为什么需要更严格裁判和 failure-specific task。

## 3. `hard_report_transform`

- 现象：脚本能跑，但生成物结构不对，或者只写了 summary 没有完整表格。
- 典型原因：模型完成了“看起来像结果”的输出，但没满足结构约束。
- 说明：适合展示 `command_success` + `file_contains` / `multi_assert` 的组合判定价值。

## 4. `medium_todo_feature`

- 现象：补了部分字段，但数据结构不一致，测试仍失败。
- 典型原因：局部修改没有和已有测试约定保持一致。

## 5. `easy_config_json`

- 现象：JSON 语法正确，但类型不对，比如数字写成字符串。
- 典型原因：弱裁判容易放过。
- 说明：这正是 `json_equals` 要解决的问题。

## 可讲结论

这个项目不是只看“模型有没有写文件”，而是看：

1. 写的内容对不对
2. 结构对不对
3. 测试对不对
4. 安全策略收紧后，代价是多少

---

## 6. 稳定性叙事（真实多 run，2026-06-25 C 批次）

> 来源：`python scripts/run_eval.py --dataset datasets/repo_tasks.json --configs baseline --runs 5`  
> 报告：`reports/report_20260625T095943.md`

### Unstable Tasks（0 < passes < runs）

| Task ID | Passes | Runs | 推测原因 |
|---------|--------|------|----------|
| `hard_report_transform` | 2/5 | 5 | 多步生成 + 结构约束严；模型偶发跳过 `run_command` 验证或表格格式偏差 |
| `medium_multi_file_sync` | 4/5 | 5 | 跨文件同步依赖一次性改全；单轮漏改 `settings.py` 即 FAIL |

### 如何对外表述

- 结论基于 **`--runs 5` + Unstable Tasks 段**，不单凭单次 100%。
- C 批次 4 个新 hard 任务本轮 **5/5 全过**（`hard_long_context_chain` 等），区分度主要由 **`hard_report_transform` 持续 flaky** 与任务集扩容提供。
- 工程上：CI 可对 unstable 任务加 `--runs 3` gate 或单独 nightly 多 run；面试中主动声明 API 方差与 bootstrap CI 限制（见 `docs/SOLID-ROADMAP.zh-CN.md` §2.2）。

---

## 7. 自动生成 taxonomy

SWE-bench / scaffold eval 的失败分类可从 CSV 自动生成：

```bash
python scripts/gen_failure_taxonomy.py \
  --csv reports/report_20260626T194843.csv \
  --csv reports/report_20260626T101113.csv
```

产出：`reports/examples/failure_taxonomy.md`（按 failure_reason、assert 类型、config、代表任务聚合）。

