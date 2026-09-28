# CHECKPOINT-6

## 6a：冻结与 B0

日期：2026-09-28。依据 `docs/sprint/HARNESS-SPRINT-6.zh-CN.md` 第 0–2 步。

**结论：第 1 步 canary 触发了停止条件（sphinx-8593 answer isolation 失败），第 2 步没有开始。** 真实花费 0.687 元。`main-b0-runs.json` 没有生成。coding-agent 暂时不要开始构建 v6 卡片。

### 第 0 步

| 项 | 结果 | 提交 |
| --- | --- | --- |
| 1. infra_error 重跑 | 槽位移到 `r<k>.infra<n>` 后原地重跑，每个槽位最多重跑 2 次，第三次保留并列入报告；`write_b0_handoff` 只读 `r1..r3`；非 infra 失败不重跑 | `2b1d244` |
| 2. `PARALLEL` | 4，B0 和 B2 相同 | `2b1d244` |
| 3. 模型记录 | summary 记录请求的模型名和 base_url host，不记 key；运行中途模型变了写 `model.changed_to`，runner 停止 | `2b1d244` |
| 4. step7-mock 交接 | 只在 `note` 末尾补了路径说明 | `2b1d244` |
| 5. 冻结记录 | `docs/sprint/A5-MAIN-FREEZE.md`，56 道 id 列表另存为 `docs/sprint/main-accepted-ids.txt` | `02c8671` |
| 6. tag | 全量测试 314 passed、199 skipped，harness `a5-main-freeze` → `02c8671` | |

第 2 步的停止条件在冻结之前就写进了 `run_a5_main.py`：每开始一次新运行之前检查一遍，已经在跑的运行跑完为止，然后写 `<phase>-report.json`。

有一个交互要说明：infra_error 的停止线按"已完成运行的 10%"字面实现，所以最早的几次运行里只要出现 1 次 infra_error 就会停（1/1 > 10%）。实际上要完成大约 10 次以上运行后，infra 重跑才可能发生。

### 第 1 步 canary

中位题：每个仓库的合格题按 `created_at` 排序后取中间那道。sklearn 有 10 道，取下中位（第 5 道）。

| 题 | created_at | 结果 | 模型调用 | 花费 | 停止原因 |
| --- | --- | --- | --- | --- | --- |
| django-13964 | 2021-02-02 | 未解出 | 40 | 0.574 | `max_model_calls` |
| sklearn-13142 | 2019-02-12 | 解出 | 16 | 0.113 | `completed` |
| sphinx-8593 | 2020-12-27 | `answer_isolation_failed` | 0 | 0.000 | `opt/repo source-only hash mismatch` |

django 和 sklearn 两次运行通过了全部检查：`mock: false`，`profile: b0-v2`，模型是 `deepseek-flash` @ `api.deepseek.com`，`answer_isolation_pass: true`，grader id 数和校准 JSON 一致（django F2P 1、P2P 36；sklearn F2P 2、P2P 54），没有 `missing`，花费记在各自的 `cny-ledger.json` 里，没有 infra_error。两次运行的 git 记录是 harness `02c8671`、coding-agent `1053203`，都是干净的。

sphinx-8593 在调用模型之前就停了，这是运行前的镜像比对检查。

### 停止原因：构建和运行用了不同的 source-only 比对规则

主池镜像是 `scripts/sprint5_prepare_main.py` 构建的。构建时，SWE-bench 规格里 `pre_install` 用 `sed` 改写的文件会被排除在 source-only 比对之外（第 169–174 行）。sphinx 的 `pre_install` 会改写 `setup.py` 和 `tox.ini`（依赖版本锁定），所以构建时判合格，`docs/sprint/clean-images/sphinx-doc__sphinx-8593.json` 里记录的是 `source_only_match: true`。

运行时，`scripts/run_swe_task.py` 第 566 行调用 `source_only_check(image, manifest)`，没有传这份排除集合。我在同一个镜像里重新跑了一遍比对：1463 个文件中，只有 `setup.py` 和 `tox.ini` 两个对不上。源码压缩包的 tree hash 仍是构建时的 `35681e93…`，镜像本身没有变化。

按同样的规则把 56 道合格题过了一遍，会在运行时失败的有 12 道：

| 被改写的文件 | 题 |
| --- | --- |
| `setup.py`、`tox.ini` | sphinx 7440、7590、7910、8120、8459、8593、9258、9461、9673 |
| `tox.ini` | sphinx 10323、10614 |
| `setup.cfg` | pytest-8399 |

在不修改代码的前提下直接跑第 2 步，这 12 道题会在第一次运行时就触发停止。

step 7 和 P5 的 mock 运行没有发现这个问题，因为它们用的题里没有 sphinx，也没有 pytest-8399。

### 修复建议（没有实施，等审计决定）

这需要改 runner，已经在冻结之后，所以要单独提交，并且要确认对已完成运行的影响。有两种做法：

1. 运行时使用和构建时相同的排除集合：把 `sprint5_prepare_main.py` 里推导 `rewritten` 的逻辑抽成一个共用函数，`run_task` 调用它。改动最小，但这些文件不再被校验。
2. 更严格的做法：对被改写的文件，把 `sed` 应用到压缩包里的原文件上，得到期望内容，再和镜像里的文件比 hash。这样这几个文件仍然被校验。

两种做法对已完成的运行都没有影响：django-13964 和 sklearn-13142 的 `pre_install` 里没有改写源码文件，比对结果不变。

还有一个续跑问题要一起决定。`runs/a5-main/sphinx-doc__sphinx-8593/b0/r1/summary.json` 是一份真实的、`profile: b0-v2` 的 B0 summary，状态是 `answer_isolation_failed`。runner 会把它当成已完成的运行，而且 `halt_reason` 会扫描这个 phase 下的所有 summary，所以修复之后直接续跑还是会立刻停下。这份证据需要移出 `runs/a5-main/`（只移动、不删除），或者由审计给出别的处理规则，之后这个槽位才能重新跑。

### 6a 要求的统计

| 项 | 值 |
| --- | --- |
| B0 有效运行 | 2（canary），全量 B0 没有开始 |
| 解出 | 1/2（sklearn 1/1，django 0/1，sphinx 没有有效运行） |
| 每题 k/3 分布 | 不适用（每题最多 1 次运行） |
| infra_error | 0，没有重跑记录 |
| 花费 | 0.687 元（B0 软上限 80，总上限 150） |
| 平均模型调用 | 28（40 和 16） |
| 超时 | 0（django 是用完 40 次模型调用） |
| `main-b0-runs.json` sha | 没有生成 |

报告在 `runs/a5-main/b0-report.json`，canary 日志在 `runs/a5-main-logs/canary.log`。

停在这里等审计，没有开始第 2 步，没有看 B2，也没有开始 B2。
