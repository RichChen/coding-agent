# AGENT R6：v6 卡片与预注册分析

日期：2026-09-28。依据：`coding-harness/docs/sprint/A5-MAIN-DESIGN.zh-CN.md`、R5 补丁审计。本轮不调用模型。

执行顺序：第 0 步（现在做）→ 等 harness 的 CHECKPOINT-6a → 第 1 步 → 停下等审计 → 等 harness 的 CHECKPOINT-6 → 第 2 步 → 停下。

## 第 0 步 冻结前修正（现在做）

1. **解出率的分母。** `analyze_a5_main.py` 里的 `_rate` 现在返回 `solved / 3.0`，这等于把 infra_error 当成未解出，和预注册的"infra_error 不计入分母"不一致。改成 `solved / n_valid`，其中 `n_valid` 是非 infra_error 的运行数。"有效运行少于 2 次的题不进入主要分析"这条规则不变。报告里的说明文字也同步改。加测试：2 次有效且都解出的题，解出率是 1.0。
2. **failed_attempt 的回退。** 构建卡片时，如果某道题没有解出，取**编号最小的非 infra_error 运行**作为 `failed_attempt`。如果全部是 infra_error，这道题不出卡，并在 manifest 里列出。加测试。
3. **清理测试副产物。** 删除未跟踪的 `reports/llm/20260928_065715/` 和 `reports/external_baselines/20260928_065707/`（都是 mock 测试生成的），并还原 `traces/graph_summary.json`。如果是某个测试会往仓库里写 `reports/`，就把它改成写临时目录。
4. 全量测试通过，工作区干净，打 tag `a5-main-freeze`。在 CHECKPOINT-6 里记下 tag 对应的 commit，harness 侧会读取它。

## 第 1 步 v6 卡片（harness 写完 CHECKPOINT-6a、生成 `main-b0-runs.json` 之后）

1. 用 `scripts/build_memory_cards.py`，同时传入两份 `--handoff`：harness 的 `docs/sprint/memory-source-runs.json`（dev）和 `docs/sprint/main-b0-runs.json`（pool B0），生成 `benchmarks/a5/memory-cards-v6.jsonl` 和 manifest，`status: final`。
2. 规则和 v5 完全一样，不因为看了 B0 结果而改动：每道源题一张卡；有解出就取编号最小的解出运行，标为 `validated_fix`；否则按第 0 步的回退规则处理。
3. 在 CHECKPOINT-6 里写明：
   - 卡片总数，每个 repo 的 `validated_fix` / `failed_attempt` 数量；
   - `cards_sha256`，两份交接的发布 sha；
   - **预期可注入表**：对 56 道 pool 题，按时间过滤规则（同 repo、`created_at` 更早、排除自己），列出有多少张 `validated_fix` 候选卡。这张表只用卡片和日期计算，不涉及任何 B2 结果。候选为 0 的题在 B2 里必然注入 0，这决定了次要分析大概能覆盖多少道题。
4. 提交后停下等审计。

## 第 2 步 分析（harness 写完 CHECKPOINT-6 之后）

1. 用 `scripts/analyze_a5_main.py` 读取 harness 的 `runs/a5-main/`，生成 `docs/sprint/A5-MAIN-RESULTS.zh-CN.md`。
2. 主要分析、次要分析和统计方法全部按预注册执行，不增删指标，不改检验方法，不换种子。
3. 可以额外加一节**描述性**结果：按 repo 分组的解出率、花费和调用数。标题必须写明"描述性，非预注册"，不做显著性检验。
4. 把报告里的主结论原样复制到 CHECKPOINT-6。停下等审计。

## 约束

不调用模型；不改 coding-harness 仓库；小步提交；不 force push；不删除旧证据；卡片和分析规则在看到数据之后不改。
