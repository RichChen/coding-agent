# AGENT R6 补充：v6 卡片与分析预注册的补充

日期：2026-09-29。本文件补充 `AGENT-MEMORY-6.zh-CN.md` 的第 1 步和第 2 步。本轮不调用模型。

## 背景

- harness 的 B0 已经跑完：115/168 = 68.5%，每道题的 k/3 分布是：3/3 有 34 道，2/3 有 4 道，1/3 有 5 道，0/3 有 13 道。
- harness 会把交接文件改成 `sprint6.main-b0-runs.v2`，每条 run 新增 `answer_isolation_pass`、`base_commit`、`grader_status`、`run_dir`、`public_task`、`issue_sha256`。
- **等 harness 在 CHECKPOINT-6 里写明"交接文件 v2 已就绪"之后再开始。**

## 第 1 步补充：v6 卡片

1. `load_handoff_document` 接受 `sprint6.main-b0-runs.v2`。v1 的 pool 交接文件要拒绝，因为它缺少隔离字段。
2. pool 来源的 issue 从 `public_task` 指向的文件读取，并核对 `issue_sha256`，不一致就报错。**只允许读取** harness 的这些文件：
   - `docs/sprint/memory-source-runs.json`
   - `docs/sprint/main-b0-runs.json`
   - `docs/sprint/main-issues.json`
   - `configs/sprint/main-targets.yaml`
   - `runs/sprint5-main-public/*.json`
   - 交接文件里列出的 `run_dir`

   不要读取 `runs/sprint5-main-private/`。
3. 卡片内容只能来自 agent 可见的轨迹（`events.jsonl` 里的动作、工具结果）和 `candidate-delta.json`。`grader-result.json` 只能用来读取 status 或 solved，不能把 grader 里的测试 id 或输出写进卡片。加一个检查：卡片文本里不能出现来源题的 F2P/P2P id 原文。检查时可以在内存里临时读取 harness 的私有文件，但不能落盘、不能打印内容，只输出命中计数。
4. 选轨迹的规则不变：取编号最小的解出运行，标为 `validated_fix`；没有解出的，取编号最小的非 infra 运行，标为 `failed_attempt`。
5. 生成 `benchmarks/a5/memory-cards-v6.jsonl` 和 manifest，`status: final`，`build_inputs.handoffs` 里记录两份交接文件的发布 sha。
6. 在 CHECKPOINT-6 里报告：
   - 卡片总数，以及每个 repo 的 `validated_fix` / `failed_attempt` 数量；
   - 卡片字节数的分布；
   - F2P/P2P id 检查的命中数，应为 0。

   原计划里的"预期可注入表"改由 harness 按真实代码路径生成（D6），这里不用做。
7. 提交后停下等审计。

## 第 2 步补充：预注册分析的追加项（在第 1 步里一并提交，必须在 B2 开始之前）

以下追加项写进 `analyze_a5_main.py` 和 `docs/sprint/A5-MAIN-PREREG-ADDENDUM.zh-CN.md`，和 v6 一起提交。

1. **主要分析不变：** 56 道题的配对 d_t，d_t = B2 的 k/3 − B0 的 k/3，只用 r1–r3。
2. **次要分析的分组改为"预测注入 ≥ 1 张卡"的题。** 分组依据是 harness 的 `docs/sprint/b2-predicted-injection.json`，由 issue 和卡片确定性计算，属于处理前的信息。原来的"实际注入"分组保留，作为一致性核对，两者应该完全相同。
3. **漂移检查（描述性）：** 按题配对比较 B0 r4 和 B0 r1–r3 的解出率，报告平均差和 bootstrap 95% 区间。如果区间不包含 0，就在报告的主结论旁边标注"存在时间漂移"。另外报告一个敏感性分析：用 r4 作为同期 B0，计算 B2 的 k/3 − r4 的 0/1 结果的平均值。只做描述，不做检验。
4. **不按 B0 结果分组做推断。** 按 B0 档位（0/3、1–2/3、3/3）分组列出 d_t 只能作为描述性结果，并且必须注明"按 B0 结果分组会受回归均值影响，不可作为效应证据"。原因是 B0 同时是分组依据和对照组，低档题在 B2 里天然会往上回。
5. **报告实际的检测下限：** 除了设计阶段的 ≈2.8·0.35/√N，再报告用本次数据估计的 d_t 标准差算出的下限，两者都列出。
6. 用合成数据测试以上各项，测试不读取 harness 的真实文件。

## 约束

不调用模型；不改 coding-harness 仓库；小步提交；不 force push；不删除旧证据；看到 B2 数据之后不修改分析规则。
