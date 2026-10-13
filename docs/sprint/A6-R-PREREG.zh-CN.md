# A6-R 预注册

日期：2026-10-13。

来源：`coding-harness/docs/sprint/A6-R-PLAN.zh-CN.md`。下面"实验设计"一节是该计划第 1 节的原文，逐字照抄，没有增删指标。之后的"输入文件约定"和"脚本的实现口径"按计划第 6 节补写，只说明分析脚本怎么读数据、怎么算上面已经列出的量，不新增指标。

分析脚本：`scripts/analyze_a6_retry.py`。diff 归一化：`scripts/a6_diff.py`。两者在任何真实 A6 数据出现之前提交，冻结 tag `a6-retry-freeze`。

---

## 1. 实验设计（预注册内容，agent 侧原样写进预注册文件）

**题和第一次尝试**

- 第一次尝试 = A5 `runs/a5-main/<task>/b0/r1..r3` 里 `solved=false` 且不是 `infra_error` 的运行。按 OPTIONS 复算应为 53 次、22 道题。构建脚本复算得到的数如果不是 53/22，停下写 CHECKPOINT，不要自行解释。
- 不用 r4、不用 B2、不用 `.infra<n>` 目录。

**两组**

- R0：第二次尝试，prompt 与 A5 B0 完全相同（`prompt_sha256` 必须等于该题 A5 B0 的值）。
- R1：第二次尝试，prompt = A5 B0 的 prompt + 第 3 节的"上次尝试记录"。
- 其余全部相同：`configs/sprint/b0-v2.yaml`、同一 clean 镜像 digest、同一 grader、40 次调用上限、`PARALLEL=3`。

**槽位和样本量**

- 每次第一次尝试 × 每组 × 3 次 = 53 × 2 × 3 = 318 次运行。
- 槽位路径：`runs/a6-retry/<task>/<arm>/<first>/r<k>`，`arm ∈ {r0, r1}`，`first` 形如 `b0r2`，`k ∈ {1,2,3}`。R0 的槽位也按 first 编号，只是为了两组每题运行数相同，R0 的 prompt 和 first 无关。
- 318 个槽位按 (task, arm, first, k) 排序后用种子 `20261013` 打乱，单一队列交错跑，两组同期。

**主分析（只有一个）**

- 有效运行 = 非 `infra_error`。每题每组有效运行少于 2 次的题不进入主分析。
- d_t = 该题 R1 有效运行的解出率 − R0 有效运行的解出率（题内先对所有槽位平均）。
- 统计量 = 22 道题 d_t 的平均。按题符号翻转置换检验 10000 次（双侧），按题 bootstrap 95% 区间 10000 次，种子都是 `20261013`。
- 结论口径：p < 0.05 且区间不含 0 才说"检出效应"。否则报点估计和区间，说"未检出大于 X 的效应"。
- 事先算好的功效（OPTIONS 模拟，假设每次失败运行同一加性提升）：+10pp 约 54%，+15pp 约 85%，+20pp 约 98%。报告里照抄，不事后重算。

**次要指标（全部描述性，不做检验，不进结论句）**

1. diff 重复率：第二次尝试的最终 diff 与对应第一次尝试 diff 完全相同（按第 3 节的归一化）的比例，R1 vs R0。
2. 文件复用：第二次尝试改动的非测试文件与第一次尝试有交集的比例。
3. `first_edit_step` 的平均和中位数。
4. `model_calls` 平均；用满 40 次调用的比例。
5. 花费平均。
6. 档位分解：A5 B0 0/3 档 13 道、中间档 9 道各自的 d_t 平均。只描述，不作为效应证据。

**第二阶段触发规则（写死，第一阶段结果出来后不改）**

- 若主统计量点估计 ≥ +5pp 且区间含 0：允许另立 A6-R2 计划（新题、新镜像，合并分析按题聚合）。否则不做第二阶段。
- 本计划不包含第二阶段的任何实现。

**停止条件（任一满足就不再启动新运行，等在跑的结束后写 CHECKPOINT）**

- 累计 `infra_error` 超过已完成运行数的 10%；
- 任何 `answer_isolation_pass=false` 或 source-only 校验失败；
- grader 报 `missing` 或崩溃；
- R0 的 `prompt_sha256` 与 A5 B0 不同，或 R1 实际发给模型的第一条 user 消息不等于"A5 B0 prompt + 冻结清单里该 first 的记录全文"；
- 模型名或 base_url 主机与 canary 记录不同；
- 累计花费达到 210 CNY（`TOTAL_CAP`）。预计 172 元。

---

## 输入文件约定

### `a6-retry-runs.json`（harness 交付，schema `a6.retry-runs.v1`）

顶层字段：

| 字段 | 说明 |
| --- | --- |
| `schema` | 固定 `"a6.retry-runs.v1"`，其他值拒收 |
| `scope` | 正式数据为 `"a6-retry"`。`"mock"`、`"step7-mock"` 或 `mock: true` 拒收。`"synthetic"` 只用于合成数据，报告标题会标明 |
| `attempts_sha256` | 生成时所用 `a6-attempts.json` 的 `handoff_sha256` |
| `runs` | 列表，每个槽位一行（应为 318 行）。退役的 `.infra<n>` 目录不列 |

`runs` 每行字段（取自该槽位 `summary.json`）：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `task_id` | str | |
| `repo` | str | `owner/name` |
| `arm` | str | `"r0"` 或 `"r1"` |
| `first` | str | 形如 `"b0r2"` |
| `k` | int | 1、2、3 |
| `run_dir` | str | 相对 harness 根目录：`runs/a6-retry/<task>/<arm>/<first>/r<k>` |
| `mock` | bool | 必须为 `false` |
| `status` | str | summary 的 `status`，`"infra_error"` 为无效运行 |
| `solved` | bool | |
| `model_calls` | int | |
| `first_edit_step` | int 或 null | |
| `cost_cny` | str 或 number | |
| `stop_reason` | str | |
| `changed_files` | list[str] | |
| `prompt_sha256` | str | |
| `retry` | object | `{arm, first, attempt_sha256}`；R0 的 `attempt_sha256` 可为 null |

### `a6-attempts.json`（harness 交付）

agent 侧只读顶层 `attempts` 列表，每项至少有 `task`（或 `task_id`）、`first`、`sha256`。字节数、各段字节数、泄漏计数等其他字段不参与分析。

### 只读的其他输入（harness 根目录下）

- 第二次尝试的改动：`<run_dir>/candidate-delta.json`。
- 第一次尝试：`runs/a5-main/<task>/b0/r<k>/summary.json`（`changed_files`）和 `candidate-delta.json`，`first = b0r<k>`。
- A5 B0 档位：`runs/a5-main/<task>/b0/r1..r3/summary.json` 的 `solved` 和 `status`。
- 原始源码：`runs/sprint5-main-images/<task>/staging/original/`（与 `task["original"]` 相同）。
- 不读任何 `grader-result.json`，不读私有材料。

## 脚本的实现口径

这些是把上面的指标落到代码时必须做的选择，写在这里以免看到数据后再选。

**主分析**

- 解出率 = 该题该组非 `infra_error` 运行里的解出次数 ÷ 有效运行数。
- 置换检验和 bootstrap 的写法照 `scripts/analyze_a5_main.py`：符号翻转用 `random.Random(20261013)`，bootstrap 用 `random.Random(20261013 + 1)`，区间取排序后第 ⌊0.025×9999⌋ 和第 ⌈0.975×9999⌉ 个均值。
- "检出效应"：p < 0.05 且 95% 区间下限 > 0 或上限 < 0，两条同时满足。
- 结论句里的 X：照 A5 的写法，取设计检测下限 2.8×0.35/√N 个百分点，N 为进入主分析的题数。报告同时给出点估计和区间。
- 第二阶段触发：点估计 ≥ 0.05 且区间下限 ≤ 0 ≤ 上限。

**次要指标**（都在进入主分析的题的有效运行上，按组汇总到运行级，不做检验）

1. diff 重复率：两边都用 `scripts/a6_diff.py` 生成的完整归一化 diff（不截断）逐字节比较；两边都为空也算相同。第二次尝试缺 `candidate-delta.json` 的运行单列，不进分母。
2. 文件复用：分子是"第二次尝试改动的非测试文件"与"第一次尝试改动的非测试文件"交集非空的运行，分母是有效运行。改动文件取各自 summary 的 `changed_files`，测试文件判定同 diff 归一化。
3. `first_edit_step`：null 不进平均和中位数，单独报 null 的次数。
4. 用满 40 次调用：`model_calls ≥ 40`。
5. 花费：`cost_cny` 转成数值后平均。
6. 档位：A5 B0 r1–r3 有效运行里解出 0 次的题为 "0/3"，其余为 "中间档"。

**diff 归一化**（`scripts/a6_diff.py`，与 harness `scripts/build_a6_attempts.py` 必须逐字节一致）

- 路径里的 `\` 换成 `/`。
- 改动文件集合 = `changed` 的键 ∪ `deleted`；同一路径同时出现在两边时按 `changed` 处理（与 `apply_delta` 一致）。
- `changed` 的值是 base64 字符串，或带 `content` 键（base64）的对象。
- 原文件取原始源码目录下同一路径；不存在视为新建文件（`--- /dev/null`）。`deleted` 写成删除（`+++ /dev/null`）；原文件也不存在则跳过。
- 文本 = 字节按 UTF-8 解码（`errors="replace"`），`\r\n` 和单独的 `\r` 都换成 `\n`。只按 `\n` 切行。
- 归一化后前后内容相同的文件不出现在 diff 里。
- 每个文件用 `difflib.unified_diff`，3 行上下文，文件头 `--- a/<path>`、`+++ b/<path>`，不带时间戳；没有结尾换行的行后面补 `\n\ No newline at end of file\n`。
- 排序键 (是否测试文件, 路径)：非测试文件在前，组内按路径字符串排序。各文件 diff 直接拼接。
- 测试文件：路径的某个目录段是 `tests` 或 `test`，或第一段是 `testing`，或文件名是 `conftest.py`，或文件名以 `test_` 开头且以 `.py` 结尾，或以 `_test.py` 结尾。
- 截断（只用于渲染记录，分析不用）：UTF-8 字节数超过上限时，保留前 `上限 − len("\n[truncated]")` 字节（按 UTF-8 解码时丢掉被切断的字符），再接 `\n[truncated]`。
