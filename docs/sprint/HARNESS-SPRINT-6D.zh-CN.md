# HARNESS R6 第二段：B2 准备与 B2

日期：2026-09-29。依据：CHECKPOINT-6a（B0 完成）审计。

## B0 审计结论

- 115/168 = 68.5% 是可信的，我抽查了以下几点：
  - 115 次解出的运行都改了源码；
  - 没有任何运行改过测试基础设施文件（conftest、runtests、pytest.ini、tox.ini、setup.cfg 等）；
  - 5 次解出的运行改的是 gold 以外的文件，属于替代修法；
  - 只有 sphinx-8593 r1 改动了一个含 P2P 的测试文件，这和 SWE-bench 官方"先应用模型补丁、再覆盖测试补丁"的口径一致。
- **分布呈两极：** 3/3 有 34 道，0/3 有 13 道，中间档只有 9 道。B2 能提升的空间只在 22 道题上。这一点写进报告的局限，但不改变预注册的主要分析。
- **需要处理的问题：** `main-b0-runs.json` 缺少卡片构建需要的字段（`answer_isolation_pass`、`base_commit`、issue 来源）。coding-agent 按现在的文件构建会报 `isolation_failed`。

执行顺序：

1. 第 A 段（现在做）：D1–D4，完成后停下，通知 coding-agent 构建 v6 卡片。
2. 第 C 段（agent 提交 v6 final 并通过审计之后）：D5–D8。

## 第 A 段

### D1 交接文件 v2

`write_b0_handoff` 改为输出 schema `sprint6.main-b0-runs.v2`。每条 run 在原有字段之外新增：

- `answer_isolation_pass`：取自 summary；
- `base_commit`：取自 `main-targets.yaml`；
- `grader_status`：取自 grader-result；
- `run_dir`：相对 harness 根目录；
- `public_task`：`runs/sprint5-main-public/<id>.json`；
- `issue_sha256`：必须等于 `main-issues.json` 里的值。

只读 `r1..r3`，不读 `r4`（见 D3）和 `.infra<n>`。重新生成 `docs/sprint/main-b0-runs.json`，旧文件改名为 `main-b0-runs.v1.json` 保留，并记录新的发布 sha。**不改动任何运行结果。**

### D2 4 次 delta_lost 的归类（只做描述）

django-13964 r2、django-15022 r2、sphinx-8120 r2、pytest-5840 r3：逐次判断属于哪一种——`search == replace` 的空编辑、agent 自己撤回了改动、还是其他原因。结果写进 CHECKPOINT-6，分类规则不改。

### D3 漂移对照臂（预注册）

B0 是凌晨跑的，B2 会在另一个时段跑，API 负载或服务端模型都可能变化。为了能检查这种时间漂移，B2 阶段同时给 56 道题各跑一次额外的 B0，槽位是 `b0/r4`。

1. runner 新增 `--phase b2 --with-b0-drift`：
   - 把 168 个 B2 槽位和 56 个 `b0/r4` 槽位混在一个队列里；
   - 用固定种子 `20260929` 打乱顺序；
   - `PARALLEL` 仍为 3。
2. `b0/r4` 和 r1–r3 用同一个 profile、同一种 B0 变体。它**不进入**交接文件，不参与卡片构建，也不参与主要分析。
3. 续跑、infra 重跑和停止条件对 r4 同样适用。
4. 加测试：队列顺序可复现；交接文件不含 r4。

### D4 冻结修订 4

在 `A5-MAIN-FREEZE.md` 里新增"修订 4"一节，写明 D1、D3 的提交和新交接文件的 sha。全量测试通过后打 tag `a5-main-freeze-r4`。然后停下，通知 coding-agent：交接文件 v2 已就绪。

## 第 C 段（v6 卡片审计通过后）

### D5 核对 v6

开跑前检查 `coding-agent/benchmarks/a5/memory-cards-v6.manifest.json`：

- `status: final`；
- `build_inputs.handoffs` 包含 dev 交接文件和 `main-b0-runs.json`（v2），两者的发布 sha 都和当前文件一致；
- `cards_sha256` 能从文件复算出来。

任何一项不满足就拒绝运行。

### D6 预测注入表（零花费，必须在第一次 B2 运行之前提交）

对 56 道题，按 B2 的真实代码路径执行一遍"时间过滤 + `MemoryCardPlugin` 选卡"，不调用模型。把每道题会注入的卡片 id 和字节数写到 `docs/sprint/b2-predicted-injection.json`，然后提交并记录 sha。

- 这张表是预注册的次要分析分组。它只依赖 issue 和卡片，不依赖任何 B2 结果。
- 另外做一项描述性统计：对每道题，被注入卡片的文本里包含多少行目标题 gold patch 新增的行。只记录，不拦截：来自更早题目的真实记忆本来就可能和后面的修法重叠。
- **停止条件：** 预测注入不少于 1 张卡的题少于 10 道，就停下等审计。

### D7 B2 加漂移对照臂

`run_a5_main.py --phase b2 --with-b0-drift --cards <v6 jsonl>`：

- 已有的停止条件照旧，花费按 `TOTAL_CAP` 230 元计算；
- 新增停止条件：任何一次 B2 运行实际注入的卡片集合和 D6 的预测不一致，就停止（这是确定性检查）；
- H5 故障警报对 B2 同样适用：前 30 次 B2 运行里 0 解出就停止。

### D8 CHECKPOINT-6（停下）

报告内容：

- B2 和 r4 的运行完成情况、infra_error、花费；
- 预测注入与实际注入的一致性；
- 注入统计：注入的题数、平均字节数；
- gold 行重叠的描述统计；
- 全量检查结果：注入的卡片没有晚于目标题的、没有目标题自己的、没有跨 repo 的。

**不计算 B2 相对 B0 的差异，不下结论。** 通知 coding-agent 开始分析。

## 约束

沿用全部硬约束，以及"纯核对口径差异可以自行修正"的授权（仅限核对口径）。任何运行时行为的改动都必须停下。
