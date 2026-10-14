# CHECKPOINT-A6-1c（coding-agent 侧）

日期：2026-10-13。依据 harness `docs/sprint/AUDIT-A6-1b.zh-CN.md` 第 2 节。

## tag

| tag | commit |
| --- | --- |
| `a6-retry-freeze-r2`（本轮新打，轻量 tag） | `6c67739`（`6c67739e8816621826493d9ef4ca4da64508ac37`） |
| `a6-retry-freeze-r1`（不动） | `01db102` |
| `a6-retry-freeze`（不动） | `e9aeddd` |

## 提交

| 提交 | 内容 |
| --- | --- |
| `c5d5348` | 交接 sha 不一致时 STOP；预注册"输入文件约定"补写这条规则；新增两个测试 |
| `6c67739` | 合成数据报告补一条修订说明（重跑结果不变） |

预注册第 1 节没有改，逐字检查的测试照常通过。没有 push。没有改 coding-harness。没有调用模型，花费 0。两边都还没有真实 A6 运行数据。

## 改了什么

`scripts/analyze_a6_retry.py`：

- `a6-retry-runs.json` 的 `attempts_sha256` 和 `--attempts` 文件实际的 `handoff_sha256` 不同时，STOP `attempts_sha_mismatch`，不写报告。`render_report` 拿到清单 sha 时也做同一个检查，所以合成数据生成器和命令行走同一条规则。报告开头原来那句"不一致"的标注去掉了，现在只可能出现"一致"。
- 新增可选参数 `--expect-runs-sha`、`--expect-attempts-sha`。给出时先和两个文件实际的 `handoff_sha256` 比较，再读文件内容；不同就 STOP，理由分别是 `runs_sha_unexpected`、`attempts_sha_unexpected`。
- 预注册"输入文件约定"一节写明这两条，并写明 A6-4 运行时两个期望 sha 都要给，取 harness CHECKPOINT-A6-3 和清单里报的值。

新增测试（`tests/test_analyze_a6_retry.py`）：

- `test_cli_stops_when_runs_name_another_manifest`：把合成 runs 文件里的 `attempts_sha256` 改成别的值，命令行返回 2，输出 `STOP attempts_sha_mismatch`，不写报告；直接调用 `render_report` 也抛同样的错误。
- `test_cli_checks_the_expected_handoff_shas`：runs 期望 sha 错 → `STOP runs_sha_unexpected`；清单期望 sha 错 → `STOP attempts_sha_unexpected`；runs 对、清单错 → `STOP attempts_sha_unexpected`；三种都不写报告。两个都对时正常出报告。

## 合成数据（重跑）

`python scripts/make_a6_synthetic.py --out .tmp/a6-synthetic-r2`。三份报告和 `a6-retry-freeze-r1` 时的逐字节相同，`A6-R-SYNTHETIC-REPORT.md` 里附的输出仍然有效。

| 真效应 | 平均 d_t | p | 95% 区间 | 结论 |
| --- | --- | --- | --- | --- |
| 0 | 0.0145 | 0.6552 | -0.0385 到 0.0676 | 未检出大于 7.7 个百分点的效应，区间上限 6.8 |
| +15pp | 0.1313 | 0.0142 | 0.0404 到 0.2260 | 检出效应 |
| +30pp | 0.3308 | 0.0000 | 0.2551 到 0.4116 | 检出效应 |

200 套零效应数据仍是 12 套 p < 0.05（6.0%）。

## 测试

- `python -m pytest -q`：365 passed，1 skipped（160.5s），系统 Python。没有 error。
- A6 相关的 `tests/test_analyze_a6_retry.py` 18 个、`tests/test_a6_diff.py` 21 个全部运行，没有跳过；对 harness 已提交的 53 份记录的逐字节比对仍然通过。

停下等审计。
