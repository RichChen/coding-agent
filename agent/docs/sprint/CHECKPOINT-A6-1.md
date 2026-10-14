# CHECKPOINT-A6-1（coding-agent 侧）

日期：2026-10-13。依据 `coding-harness/docs/sprint/A6-R-PLAN.zh-CN.md` 第 6 节 A6-1，遵守第 1、7 节。

## 提交和 tag

| 提交 | 内容 |
| --- | --- |
| `b69dc98` | `docs/sprint/A6-R-PREREG.zh-CN.md`：计划第 1 节原文 + 输入文件约定 + 脚本的实现口径 |
| `ca4afb6` | `scripts/a6_diff.py` 第一版（按计划第 3 节自写）、`scripts/handoff_sha.py`、`tests/test_a6_diff.py` |
| `a4c005d` | `scripts/analyze_a6_retry.py`、`scripts/make_a6_synthetic.py`、`tests/test_analyze_a6_retry.py` |
| `eb068af` | `docs/sprint/A6-R-SYNTHETIC-REPORT.md` |
| `095ed17` | diff 归一化换成 harness 的逐字复制，预注册的归一化口径同步改写（第 1 节没动） |
| `e9aeddd` | 合成数据报告补一句对齐后重跑结果不变 |

- tag `a6-retry-freeze` → `e9aeddd`（轻量 tag，和 `a5-main-freeze` 一样）。
- 分析脚本和生成器在 `a4c005d` 提交时，仓库里和 harness 里都没有任何 A6 运行数据。
- 没有 push。没有改 coding-harness。没有调用模型，花费 0。

## 预注册

- 第 1 节逐字照抄。`tests/test_analyze_a6_retry.py::test_prereg_keeps_plan_section_one_verbatim` 从 harness 计划里切出第 1 节，检查它是预注册文件的子串（LF 归一化后），通过。
- 补写的两部分：`a6-retry-runs.json`（schema `a6.retry-runs.v1`）的字段约定；脚本怎么算第 1 节已有的量（分母、null 的处理、档位的判定、第二阶段触发的判定、diff 归一化）。没有新增指标。

## 分析脚本

`python scripts/analyze_a6_retry.py --runs <a6-retry-runs.json> --attempts <a6-attempts.json> --harness-root <coding-harness> --out <report.md>`

- 主分析：每题 R1、R0 有效运行解出率之差，22 题平均，符号翻转 10000 次和 bootstrap 10000 次，种子 20261013。统计函数照抄 `analyze_a5_main.py`，测试用 A5 的种子核对两边输出相同。
- 结论句：p < 0.05 且区间不含 0 才写"检出效应"，否则写"未检出大于 X 个百分点的效应"并给点估计和区间。功效一句照抄。第二阶段触发按第 1 节规则判定。
- 次要指标 1–6 只描述。diff 重复率读两边的 `candidate-delta.json` 和原始源码，不读 `grader-result.json`。
- 输入核对：第一次尝试数（预期 53/22）、槽位行数、缺的、重复的、清单外的槽位、`run_dir` 与槽位不符、R1 的 `attempt_sha256` 与清单不符、R0 的 `prompt_sha256` 与 A5 B0 不符、两个交接文件的 `handoff_sha256` 以及 runs 里记录的清单 sha 是否一致。`scope` 为 mock 或任一行 `mock` 不是 `false` 时直接 STOP。

## diff 归一化和 harness 的比对

- 第一版（`ca4afb6`）在 harness 还没有构建脚本时按计划第 3 节写。之后 harness 提交了 `scripts/build_a6_attempts.py`（`ce0b0ff`），比对测试随即失败。两边有四处不同：
  - 测试路径规则：harness 把任意一级 `testing/` 目录都算测试目录，`test_` 开头的文件不要求 `.py` 后缀；
  - 无法按 UTF-8 解码的文件：harness 写 `Binary file <path> differs`，第一版用替换字符；
  - 结尾换行：harness 忽略只差结尾换行的改动，不写 `\ No newline at end of file`；
  - 记录里的 diff 段去掉末尾换行，空 diff 写 `none`。这一条只影响记录文本。
- `095ed17` 把 `is_test_path`、`_lf_text`、`_lines`、`normalized_diff`、`head`、`original_reader`、`TEST_DIRS`、`TRUNCATED` 从 harness 逐字复制过来，做法在 tag 之前。
- 比对结果：
  - `test_copied_functions_match_the_harness_builder`：上面 8 个定义与 harness `ce0b0ff` 的 AST 完全相同；
  - `test_diff_matches_the_harness_records_byte_for_byte`：从 `runs/a5-main` 和 `staging/original` 重算 53 份记录的 "Final diff" 段，和 harness 磁盘上的 `docs/sprint/a6-attempts/*.txt` 逐字节相同，53/53。
- 注意：比对时 harness 的 `a6-attempts/` 和 `a6-attempts.json` 还是未跟踪文件（harness `96db678` 的 CHECKPOINT 因泄漏检查 1–2 有命中停下等审计）。harness 如果重新生成记录或改动归一化，要重跑 `python -m pytest tests/test_a6_diff.py`。
- 用复制后的规则复算：A5 B0 r1–r3 失败运行 53 次、22 道题；其中 11 次没改非测试源码，和 OPTIONS 一致。

## 合成数据

详见 `docs/sprint/A6-R-SYNTHETIC-REPORT.md`。三套都是 22 题、53 次第一次尝试、318 个槽位，各含 2 个 infra_error。

| 真效应 | 平均 d_t | 双侧 p | 95% 区间 | 脚本结论 |
| --- | --- | --- | --- | --- |
| 0 | 0.0145 | 0.6552 | -0.0385 到 0.0676 | 未检出大于 20.9 个百分点的效应 |
| +15pp | 0.1313 | 0.0142 | 0.0404 到 0.2260 | 检出效应 |
| +30pp | 0.3308 | 0.0000 | 0.2551 到 0.4116 | 检出效应 |

- 三套点估计都在真效应 ±0.10 以内（判据在跑之前写进生成器）。
- 零效应时 p 不显著。另跑 200 套零效应数据，12 套 p < 0.05（6.0%）。
- 对齐 diff 之后重跑，三份报告逐字节不变。

## 测试

- `python -m pytest -q -p no:cacheprovider`：361 passed，1 skipped（338.7s），系统 Python。
- 本轮第一次全量运行时还出现过 85 个 error，集中在 `test_memory_record_store.py`、`test_memory_cards_v5.py`、`test_memory_sources.py` 等与本轮无关的文件。这些文件单独跑通过，之后两次全量运行都没有再出现，原因没有查明。
- 新增测试：`tests/test_a6_diff.py` 21 个，`tests/test_analyze_a6_retry.py` 14 个，没有跳过。

## 需要审计决定的事

1. **结论句里的 X。** 按 A5 写法取 2.8×0.35/√N，22 题时是 20.9 个百分点，比功效表里 85% 功效对应的 15pp 大。零效应时报告会写"未检出大于 20.9 个百分点的效应"。如果审计要换成别的定义（例如区间上限），需要冻结后单独提交。
2. **`a6-attempts.json` 的键名。** 预注册写的是顶层 `attempts` 列表；harness 实际把计数放在 `attempts`（53），列表放在 `records`。脚本两种都接受，已用 harness 磁盘上的文件实测读出 53 份、22 道题、每份 64 位 sha。预注册文字没有改。
3. **测试文件规则来自 harness。** 任意一级 `testing/` 目录都算测试目录，所以 `sphinx/testing/`、`sympy/testing/` 下的文件不算源码。这会影响"Files changed"一段和次要指标 2。53 份第一次尝试的 `changed_files` 里没有任何非首级 `testing/` 目录下的文件（没改非测试源码的仍是 11 次）。
4. **`a6-retry-runs.json` 的字段**按预注册"输入文件约定"一节写，harness 的 A6 runner 交付时需要对上：每行要有 `task_id`、`repo`、`arm`、`first`、`k`、`run_dir`、`mock`、`status`、`solved`、`model_calls`、`first_edit_step`、`cost_cny`、`changed_files`、`prompt_sha256`、`retry`，顶层要有 `schema`、`scope`、`attempts_sha256`。

`docs/memory-v2/` 是本轮之前就存在的未跟踪目录，没有动，也没有提交。

停下等审计。
