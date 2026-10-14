# coding-agent 第五轮计划书：通用卡片构建和预先写好的分析脚本

日期：2026-09-26。执行者：挂在 `D:\crq\src\coding-agent` 的 Cursor agent。
前置：`AGENT-MEMORY-4.zh-CN.md`、`CHECKPOINT-4.md`。实验设计见 `D:\crq\src\coding-harness\docs\sprint\A5-MAIN-DESIGN.zh-CN.md`（下文简称"设计文档"），本轮工作都服务于它。
配套：`D:\crq\src\coding-harness\docs\sprint\HARNESS-SPRINT-5.zh-CN.md`。

## 0. 第四轮审计结论

第四轮有效，不需要回滚：B2 只注入 `validated_fix`；v4 final 是从隔离后的 `b0-v2` 运行构建的，manifest 的哈希能对上。

变化：实验改为 A5-main（见设计文档）。记忆源不再是固定的 15 道题，而是 **14 道 dev 题 + 题目池里每道题自己的 B0 运行**，按时间顺序、留一法注入。这要求卡片构建不再绑定固定的源题清单，而且每张卡都要带上仓库和时间信息。

## 1. 本轮规则

- 本轮不调用模型，花费 0。
- 开工前提交本计划书，打 tag `mem5-start`。继续往 PROGRESS 追加记录。
- 只读 coding-harness，不修改它。
- 交接文件的 sha256 统一按 harness `docs/sprint/HANDOFF-CONVENTIONS.md` 里的函数计算。如果它还没写好，就先用"UTF-8 + LF 归一化"，等它出来之后再核对一次。

## 2. 分步计划

### 第 1 步：卡片增加 `repo` 和 `created_at`

1. `MemoryCard` 增加 `repo` 和 `created_at`（ISO 8601 格式），两者都来自交接文件（harness 从 SWE-bench 公开元数据里取的）。这两个字段不渲染进卡片正文，只用于过滤。
2. v4 的 14 张卡补上这两个字段，另存为 `memory-cards-v5.jsonl`，并配一个 manifest（status `final`，`build_inputs` 引用 harness 升级后的交接文件 `sprint5.memory-source-runs.v2` 的 sha256）。如果 harness 的新交接文件还没出现，就先生成 interim 版，并写一条 PROGRESS。
3. 测试：两个字段都必须存在，而且格式合法；缺失时构建直接失败，不能填默认值。

### 第 2 步：通用的卡片构建

1. 把 v4 的构建逻辑整理成 `scripts/build_memory_cards.py --handoff <交接文件> --out <jsonl>`。输入可以是任意一份符合 `sprint5.memory-source-runs.v2` 格式的交接文件，不再写死 15 道源题。
2. 规则不变：每道源题取解出的运行里 `repeat` 编号最小的一次，标记为 `validated_fix`；没有解出的就取 `repeat` 编号最小的一次，标记为 `failed_attempt`。
3. 保留断言：交接文件里的每条运行都必须是 `answer_isolation_pass: true`；卡片正文里不能出现 test patch、gold 或隐藏 nodeid。
4. R6 会用它构建 "dev + 题目池" 的卡片集合。本轮先用 dev 的交接文件跑通，结果和第 1 步的 v5 逐字节一致（字段顺序也要一致）。

### 第 3 步：预先写好分析脚本（设计文档第 6 节）

`scripts/analyze_a5_main.py`，输入是 harness 的 R6 运行汇总（每次运行一行：`task_id`、`repo`、`variant`、`repeat`、`solved`、`status`、`cost_cny`、`model_calls`、`first_edit_step`、`memory.injected`），输出一份 markdown 报告：

1. 每道题 B0 和 B2 的 k/3，以及 d_t。
2. 主要分析：所有合格题的平均 d_t；符号翻转置换检验（10000 次，固定随机种子，双侧）；按题 bootstrap 的 95% 置信区间（10000 次，固定种子）。
3. 次要分析：只看 B2 实际注入了至少 1 张卡的题，做同样的统计。另外按仓库分组列出。
4. 花费、模型调用次数、第一次编辑的轮次：B0 和 B2 的对比。
5. 分母规则：`infra_error` 的运行不计入；如果某道题某一组的有效运行少于 2 次，这道题就从主要分析里剔除，并在报告里列出来。
6. 结论措辞按设计文档第 6 节的规定自动生成。置信区间包含 0 时，写"没有检出大于 X 个百分点的效应"。

测试：用合成数据验证，零效应、明显正效应、存在 `infra_error` 这三种情况，报告的数字和措辞都要正确。**不能接触任何真实的 R6 数据**，因为 R6 还没跑。

### 第 4 步：dev 上的按时间留一法离线表

用 v5 卡片和"同仓库 + 更早 + 非本题 + 只取 validated_fix"的规则，重新出一份 dev 14 题的离线选择表：每道题有哪些卡可以注入、分数多少、实际会注入哪几张。这张表是 harness 第 6 步冒烟的离线预期。不调整检索规则。

### 第 5 步：CHECKPOINT-5

写 `docs/sprint/CHECKPOINT-5.md`：

- v5 卡片的 manifest 和哈希；
- 通用构建脚本的对齐验证（和 v5 逐字节一致）；
- 分析脚本在合成数据上的测试结果，附一份合成数据生成的样例报告；
- dev 按时间留一法的离线表；
- 花费。

然后停下，等审计。

## 3. 本轮不做

- 调整检索、`min_score` 或渲染规则（这些会在 A5-main 冻结时一并锁定）。
- 为任何题手写卡片。
- 碰任何 R6 的真实数据。
