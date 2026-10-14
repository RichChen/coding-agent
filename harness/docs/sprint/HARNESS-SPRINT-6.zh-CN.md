# HARNESS R6：A5-main 正式实验

日期：2026-09-28。依据：`A5-MAIN-DESIGN.zh-CN.md`、R5 补丁审计。

本轮开始真实运行 pool 题：56 道合格题，B0 和 B2 各 3 次，共 336 次。预计花费约 120 CNY，总上限 150 CNY（`TOTAL_CAP`）。

执行顺序：第 0 步 → 第 1 步 → 第 2 步 → **停在 CHECKPOINT-6a** → 等 agent 侧的 v6 卡片和审计 → 第 3 步 → 第 4 步 → CHECKPOINT-6。

## 第 0 步 冻结前的最后修改

1. **infra_error 重跑。** runner 续跑时，如果某个位置（`<task>/<phase>/r<k>`）的 summary 是 `infra_error`：
   - 把整个目录改名为 `r<k>.infra<n>`（n 从 1 开始），然后在原位置重跑。只移动，不删除。
   - 每个位置最多重跑 2 次。第 3 次仍是 `infra_error` 就保留，在报告里列出，由分析侧按"不计入分母"处理。
   - `write_b0_handoff` 只读 `r<k>` 目录，不读 `.infra<n>`。
   - 非 infra 的失败（未解出、超时、预算耗尽）不重跑。
   - 加测试。
2. **固定并发。** B0 和 B2 用同一个 `PARALLEL`，默认 4。第 1 步确认资源够用以后就不再改动。如果改了，要在 CHECKPOINT 里写明，并且两个 phase 必须一致。
3. **summary 记录模型信息。** summary 里记录实际请求的模型名和 base_url 的主机名（不记录 key）。如果模型名在运行中途发生变化，runner 报错停下。
4. `docs/sprint/main-b0-runs.step7-mock.json` 顶部 note 补一句"summary 路径已移到 `runs/a5-main-mock-step7/`"。其他内容不动。
5. 写 `docs/sprint/A5-MAIN-FREEZE.md`，记录以下内容：
   - harness commit；agent 侧 `a5-main-freeze` 指向的 commit（agent 侧先打 tag，commit 从 agent 的 CHECKPOINT 里读）；
   - `main-targets.yaml` 的 sha；56 道合格题 id 列表的 sha；
   - `configs/sprint/b0-v2.yaml` 的 sha；
   - dev 交接文件的 sha；`PARALLEL`；`TOTAL_CAP`。
6. 全量测试通过后，打 tag `a5-main-freeze`（harness 仓库）。之后到 R6 结束，除非遇到停止条件，否则不改 runner、grader、镜像和校准。

## 第 1 步 真实金丝雀（约 1 CNY）

从 56 道里按固定规则选 3 道（每个 repo 按 `created_at` 排序后取中位那一道，只取 django、sklearn、sphinx），各跑 1 次 B0，写到正式目录 `runs/a5-main/`，这些就是正式的 r1。

检查以下各项：summary 有 `mock: false` 和 `profile: b0-v2`；`answer_isolation_pass` 为真；grader 送进去的 id 数和校准 JSON 一致，没有 `missing`；花费进入 CNY 账本；没有 infra_error。

任何一项不满足就停下，写 CHECKPOINT-6a，不进入第 2 步。

## 第 2 步 全量 B0（约 60 CNY）

1. `run_a5_main.py --phase b0`，56 道 × 3 次。
2. **自动停止条件**（满足任意一条就停止启动新运行，等在跑的结束后写 CHECKPOINT-6a）：
   - 累计 infra_error 超过已完成运行数的 10%；
   - 出现任何 `answer_isolation_pass=false`，或出现 source-only 校验失败；
   - grader 报 `missing` 或崩溃；
   - 花费达到 80 CNY。这是 B0 的软上限，正常情况下远达不到。
3. B0 跑完后生成 `docs/sprint/main-b0-runs.json`（schema `sprint6.main-b0-runs.v1`，不带 mock scope），并记下发布 sha。

## CHECKPOINT-6a（停下）

写 `docs/sprint/CHECKPOINT-6.md` 的第一部分：

- B0 总解出次数和每个 repo 的解出率；每道题的 k/3 分布（0/1/2/3 各有几道）；
- infra_error 次数和重跑记录；
- 花费、平均模型调用数、超时次数；
- `main-b0-runs.json` 的发布 sha。

**不要看 B2，也不要开始 B2。** 通知 agent 侧可以构建 v6 卡片，然后停下等审计。

## 第 3 步 全量 B2（审计通过、agent 提交 v6 final 之后）

1. `run_a5_main.py --phase b2 --cards <coding-agent>/benchmarks/a5/memory-cards-v6.jsonl`，56 道 × 3 次。`PARALLEL` 和 B0 保持一致。
2. 开跑前核对 v6 manifest：`build_inputs.handoffs` 里 dev 交接和 `main-b0-runs.json` 的 sha 都要和 harness 当前文件一致，否则拒绝运行。
3. 停止条件和第 2 步一样，花费改为按总上限 150 CNY 计算。
4. 每次 B2 的 summary 里都要有 `filtered_card_ids` 和 `injected`。抽查：没有任何注入卡的 `created_at` 晚于或等于目标题；没有注入当前题自己的卡；没有跨 repo 的卡。以上用脚本检查全部 168 次，不是只看样本。

## 第 4 步 CHECKPOINT-6（停下）

补上 CHECKPOINT-6 的第二部分：

- B2 的运行完成情况、infra_error、花费；
- 注入统计：多少道题至少注入过 1 张卡，平均注入字节数；
- 上面那项全量检查的结果；
- 本轮总花费。

**不在这里计算 B0 和 B2 的差异，也不下结论。** 分析交给 agent 侧的预注册脚本。通知 agent 侧开始分析。

## 约束

- 沿用全部硬约束：密钥不进入 git、日志或打印；gold/test/F2P/P2P 不进入 agent 可见范围；小步提交；不 force push；不删除旧证据；不改 coding-agent 仓库。
- 第 0 步之后，任何代码改动（修 bug）都要单独提交，并在 CHECKPOINT 里写明它影响了哪些已完成的运行。
- 不要因为看到 B0 结果就调整题目、profile 或卡片规则。
