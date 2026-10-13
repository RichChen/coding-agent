# CHECKPOINT-A6-1b（coding-agent 侧）

日期：2026-10-13。依据 harness `docs/sprint/AUDIT-A6-1.zh-CN.md` 第 1、3 节。

## 提交和 tag

| 提交 | 内容 |
| --- | --- |
| `199047a` | 结论句里的 X 改为 2.8×s_obs/√N，结论句写出 95% 区间上限；`a6-attempts.json` 只认 `records`，`attempts` 必须是等于列表长度的整数；预注册"输入文件约定"和"脚本的实现口径"两处同步改写；测试和合成数据生成器跟着改 |
| `01db102` | 重跑合成数据，更新 `A6-R-SYNTHETIC-REPORT.md` |

- `a6-retry-freeze` 不动，仍指向 `e9aeddd`。
- 新 tag `a6-retry-freeze-r1` → `01db102`（轻量 tag）。harness 的冻结记录引用这个 tag。
- 预注册第 1 节没有改，逐字检查的测试照常通过。
- 没有 push。没有改 coding-harness。没有调用模型，花费 0。仓库和 harness 里都还没有真实 A6 运行数据。

## 审计第 3 节第 1 条：X

- X = 2.8 × s_obs / √N，s_obs 是进入主分析的 d_t 的样本标准差（分母 N − 1），写法和 A5 脚本的 `data_floor_points` 相同，测试核对两边输出一致。
- 未检出时，结论句写成："未检出大于 X 个百分点的效应（2.8×s/√N）；95% 区间上限 U 个百分点。点估计 …，95% 区间 … 到 …"。
- 报告主分析一节新增三行：s_obs、数据检测下限 X、95% 区间上限。去掉了原来的"设计检测下限（2.8×0.35/√N）"。
- 功效句照抄不动。"检出效应"的判定（p < 0.05 且区间不含 0）不变。

## 审计第 3 节第 2 条：`a6-attempts.json`

- 预注册改为：列表在顶层 `records`，计数在顶层 `attempts`（整数，必须等于 `records` 的长度），每项至少有 `task`、`first`、`sha256`。
- 脚本只认这种结构。没有 `records` 列表时 STOP `records_not_a_list`；计数缺失或不符时 STOP `attempts_count_mismatch`；条目里没有 `task` 字段（例如只有 `task_id`）或 `first` 格式不对时 STOP `bad_attempt_entry`。
- 用 harness 已提交的清单实测（`27a7a0a`，`handoff_sha256` = `bd93252922c990ec61071caecb5a6bf5e604202cbbcf30d296f2b875794dd3ce`，与 harness 提交说明里的 `bd932529` 一致）：读出 53 份、22 道题。这一项写成了测试 `test_harness_attempts_manifest_loads`。

## 审计第 2 节之后的记录比对

harness 已提交 `4bfd6f3`（改 "Files changed" 的 none 文字，改了 `build_a6_attempts.py`）和 `27a7a0a`（53 份记录和清单）。比对时 harness 工作区里这些文件是干净的，`build_a6_attempts.py` 最近一次改动是 `4bfd6f3`。重跑 `tests/test_a6_diff.py`：

- 复制的 8 个定义（`is_test_path`、`_lf_text`、`_lines`、`normalized_diff`、`head`、`original_reader`、`TEST_DIRS`、`TRUNCATED`）和 harness 当前构建脚本的语法树完全相同，`4bfd6f3` 没有动 diff 部分。
- 53 份已提交记录的 "Final diff" 段从 `runs/a5-main` 和 `staging/original` 重算，逐字节相同，53/53。
- 两个测试都实际运行了，没有跳过。

## 合成数据（重跑）

详见 `docs/sprint/A6-R-SYNTHETIC-REPORT.md`。

| 真效应 | 平均 d_t | p | 95% 区间 | s_obs | X | 区间上限 | 结论 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 0.0145 | 0.6552 | -0.0385 到 0.0676 | 0.1292 | 7.7pp | 6.8pp | 未检出 |
| +15pp | 0.1313 | 0.0142 | 0.0404 到 0.2260 | 0.2289 | 13.7pp | 22.6pp | 检出效应 |
| +30pp | 0.3308 | 0.0000 | 0.2551 到 0.4116 | 0.1936 | 11.6pp | 41.2pp | 检出效应 |

- 三套结论和第一版相同，三套都不满足第二阶段触发条件。200 套零效应仍是 12 套 p < 0.05（6.0%）。
- 逐行比较新旧报告，只有两类行变了：一是主分析里 X 相关的几行；二是合成清单改成 `records` 加计数之后，`a6-attempts.json` 的 sha 变了，`a6-retry-runs.json` 里记录的这个 sha 也跟着变，所以两个交接 sha 都变了。点估计、p、区间、逐题表、次要指标都没变。
- 零效应时 X 从 20.9pp 变为 7.7pp。

## 全量测试（两次）

| 次 | 命令 | 结果 | 用时 |
| --- | --- | --- | --- |
| 1 | `python -m pytest -q -p no:cacheprovider` | 363 passed，1 skipped | 304.3s |
| 2 | `python -m pytest -q`（和上轮出 85 个 error 那次同一条命令） | 363 passed，1 skipped | 495.7s |

85 个 error 两次都没有复现。上一轮出 error 之后一共跑过四次全量，都没有 error：上一轮两次带 `-p no:cacheprovider`（第一次有比对测试失败，当轮已修），本轮两次如上。原命令 `python -m pytest -q` 在出错之后只跑过本轮这一次。原因没有查明。系统 Python，没有另建 `.venv`。

## 留给下一轮

- harness 的 runner（`69178cc`）写出的 `a6-retry-runs.json` 还没交过来。审计第 4 节第 3 条要 harness 用 mock scope 的文件跑一次本脚本，预期结果是 `STOP mock_input`。
- 本脚本要求 `a6-retry-runs.json` 里的 `attempts_sha256` 和清单的 `handoff_sha256` 一致，不一致不会 STOP，只在报告开头标"不一致"。

停下等审计。
