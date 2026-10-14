# CHECKPOINT-A6-1b：审计后修改、runner、preflight、mock（coding-harness）

日期：2026-10-13。花费：0 CNY。没有调用真实模型，没有启动 provider。A5 的运行目录只读，`run_a5_main.py` 没有改。依据 `docs/sprint/AUDIT-A6-1.zh-CN.md` 第 4 节和 `A6-R-PLAN.zh-CN.md` 第 5 节 A6-1 第 3–6 步。

**结果：** 审计第 4 节的 4 项都已完成。preflight 22/22 题通过；mock 端到端 4 个槽位跑通，注入核对 4/4；agent 仓库 `a6-retry-freeze-r1` 上的分析脚本读了 mock 的 runs 文件，按设计因 mock 而 STOP。两种 Python 环境下各跑两次全量测试，全部通过。没有打 freeze tag，没有 push。

## 各步提交

| 提交 | 内容 |
| --- | --- |
| `4c35bdf` | 审计文件和 A6-1b 启动 prompt 原样入库 |
| `4bfd6f3` | "Files changed" 的 test-only 写法；泄漏计数改为描述；渲染不读私有材料的测试 |
| `27a7a0a` | 53 份记录和清单 `docs/sprint/a6-attempts/`、`docs/sprint/a6-attempts.json` |
| `69178cc` | `scripts/run_a6_retry.py` 和 `tests/test_run_a6_retry.py` |
| 本提交 | mock 的 runs 文件、本 CHECKPOINT、PROGRESS |

## 1. 渲染不依赖私有材料（审计第 4 节第 1 条）

`tests/test_build_a6_attempts.py` 新增两组测试，每组都分"不可读"和"垃圾内容"两种情况：

- `test_records_do_not_depend_on_private_material`（合成数据）：先正常构建，再在磁盘上把 private 文件换成目录（不可读）或垃圾字节，把校准 JSON 换成垃圾字节，然后对每次第一次尝试调用 `render_record`，输出与正常构建写出的文件逐字节相同。
- `test_the_53_records_do_not_depend_on_private_material`（真实数据，A5 运行目录存在时才跑）：拦截 `open`、`io.open`（`Path.read_text`/`read_bytes` 都经过它），凡是打开 `runs/sprint5-main-private/` 或 `docs/sprint/main-calibration/` 下的文件，要么抛 `PermissionError`，要么返回垃圾内容。在这种状态下渲染 53 份，sha256 与已提交清单逐份相同。

两组测试都断言渲染期间打开私有路径的次数为 0，也断言 `private_material` 在同样条件下会报错，以此证明拦截确实生效。真实私有文件没有改动。

## 2. "Files changed" 和重建（审计第 4 节第 2 条）

- 新常量 `TEST_ONLY = "none (only test files were changed; see the diff)"`，并纳入 `template_sha256()`。非测试文件为空、但 `changed_files` 不为空时用它；`changed_files` 为空时仍写 `none (no source changes were submitted)`。53 次第一次尝试里，`changed_files` 与 delta 的 `changed ∪ deleted` 逐份一致，两种判定方式结果相同。
- 泄漏检查第 1–4 项照常计数，写进清单和 `runs/a6-retry-logs/leak-check.json`，只作描述。清单去掉了 `leak_blocking`，构建脚本有命中时不再以非零退出。
- 重建后只有 2 份记录变了：django__django-15973 b0r3、sphinx-doc__sphinx-9258 b0r2，两份的 Files changed 现在都是新写法，下面的 diff 不变。核对方法：把 `TEST_ONLY` 换回旧文字重新渲染，53 份里只有这 2 份不同；`CHECKPOINT-A6-1.md` 里贴出的 3 份全文与新文件逐字节相同。
- 泄漏计数不变：34 / 58 / 0 / 113。字节数 688–8192，中位 2664。

| 项 | 旧值（A6-1，未提交） | 新值（`27a7a0a`） |
| --- | --- | --- |
| 模板 sha（`template_sha256`） | `72f666b651f55bf56f18c7481d276f0550b944c25e4c05d2d783c679c49bf239` | `7bed7ba8560276be361c3840393baefdf103f954ad4dbcf8636f0de1e021b32e` |
| 清单 `handoff_sha256` | `a324ab61f649d9f5c42ebf63866e763b9dff3a5775b726c7d1eefad0ee3e4a2d` | `bd93252922c990ec61071caecb5a6bf5e604202cbbcf30d296f2b875794dd3ce` |

按审计第 2 节，4 份 `delta_lost` 记录不改，在此列出：django__django-13964 b0r2、django__django-15022 b0r2、pytest-dev__pytest-5840 b0r3、sphinx-doc__sphinx-8120 b0r2。这 4 份都用满了 40 次调用，`changed_files` 为空，Files changed 和 diff 都写 none。

## 3. runner：`scripts/run_a6_retry.py`

用法：`--preflight`、`--mock --mock-slots`、`--canary`、`--slot <task>/<arm>/<first>/r<k>`（可重复）、`--runs-file`（只从已有 summary 重写 runs 文件），不带参数则跑完整队列。

**槽位。** 53 份记录 × {r0, r1} × k∈{1,2,3} = 318 个槽位，按 (task, arm, first, k) 排序后用 `random.Random(20261013).shuffle` 打乱，单一队列，`PARALLEL=3`（取自 `run_a5_main`），profile `configs/sprint/b0-v2.yaml`，`TOTAL_CAP = 210`。输出 `runs/a6-retry/<task>/<arm>/<first>/r<k>`，mock 写到 `runs/a6-retry-mock/`。

**启动时。** 清单的 schema、`template_sha256`（必须等于当前代码）、53/22 复算都要对上；每道题用 `build_prompt` 渲染 R0 prompt，sha 必须等于该 first 在清单里记录的 A5 `prompt_sha256`；R1 prompt 必须严格等于 R0 prompt + `"\n\n"` + 记录全文（记录按清单 sha 读回）。

**R1 每次运行前**，从清单重新读记录，并核对 sha 和启动时缓存的全文。

**每次运行后（停止条件，任一满足就不再启动新运行）：**

- `run_a5_main.run_checks`：infra_error ≥ 3 且超过已完成数的 10%；`answer_isolation_pass=false`（source-only 失败也落在这里，`run_task` 写 `answer_isolation_failed`）；grader 报 `missing`；grader 崩溃；`harness_tool_errors > 0`。
- 注入核对（每次非 infra 运行）：summary 的 `retry` 等于期望值；`prompt_sha256` 等于期望 prompt 的 sha（R0 就是 A5 B0 的 sha）；从 `events.jsonl` 读出的第一条 user 消息（artifact 引用按 sha 读回）与期望全文逐字相同。
- 模型身份：根目录下所有 summary 只能有一个 (name, base_url_host)，出现 `changed_to` 也停。canary 是正式目录里最早的几次运行，所以"与 canary 相同"等价于全体一致。
- 累计花费 ≥ 210 CNY（统计根目录下全部 summary，包括退役的 infra 和 canary）。

infra 重跑同 A5：目录改名为 `r<k>.infra<n>`，每个槽位最多 2 次（直接用 `retire_infra`）。

**`retry` 字段：** R0 为 `{arm: "r0", first, attempt_sha256: null}`，R1 为 `{arm: "r1", first, attempt_sha256: <记录 sha>}`。

**`a6-retry-runs.json`：** 每个已有 summary 的槽位一行，字段与 agent 预注册"输入文件约定"完全一致：`task_id, repo, arm, first, k, run_dir, mock, status, solved, model_calls, first_edit_step, cost_cny, stop_reason, changed_files, prompt_sha256, retry`。退役的 `.infra<n>` 不列。顶层有 `schema: "a6.retry-runs.v1"`、`scope`（正式为 `"a6-retry"`，mock 为 `"mock"`）、`attempts_sha256`（清单 `handoff_sha256`），另加 `slots_expected`（318）；mock 文件多一个 `note`。审计第 4 节第 3 条的列表里没有 `stop_reason`，但预注册里有，按指示以预注册为准。正式文件只在完整队列跑完且没有停止时自动写出，写入前每行 summary 都要通过和续跑相同的核对（mock、profile、variant、retry）。

**canary 规则（为 A6-2 预先实现，冻结后不用再改 runner）：** 队列中第一个、第二个 R0 槽位，加第一个、第二个 R1 槽位，按队列顺序跑。当前清单下是 django__django-15022/r1/b0r2/r3、pytest-dev__pytest-7324/r0/b0r2/r3、sphinx-doc__sphinx-7590/r0/b0r1/r3、sympy__sympy-19040/r1/b0r3/r3，正好是队列的前 4 个。

**测试：** `tests/test_run_a6_retry.py` 23 个，用假的 `run_task` 写 summary 和 events。覆盖：打乱规则、canary 和 mock 选槽、R0/R1 期望 prompt、A5 sha 或记录被改时拒绝启动、完整跑通（含 artifact 引用的 events）、R1/R0 prompt 不一致即停、第一条 user 消息被改即停、启动后记录被改则不跑、infra 重跑上限、infra 比例、花费上限、模型身份变化、隔离失败和工具错误、续跑拒收不属于该槽位的 summary、runs 文件字段与预注册逐字段一致、mock 文件 scope、清单模板 sha 不符时拒收、已提交清单给出 318 个槽位。

## 4. preflight

`python scripts/run_a6_retry.py --preflight`，报告写到 `runs/a6-retry-logs/preflight.json` 和 `preflight-pool.json`，模型调用 0 次。

| 检查 | 结果 |
| --- | --- |
| 22 道题的池检查（`run_a5_main.preflight`：answer isolation、`/opt/repo` source-only 哈希、grader id 数与校准一致、prompt 检查、工具冒烟） | 22/22；工具冒烟 22/22（Python 3.6 3 道、3.8 1 道、3.9 18 道） |
| clean 镜像 digest 与 A5 B0 r1–r3 summary 一致 | 22/22（source-only 校验要用这个 digest 起容器，所以 digest 在本机确实存在） |
| dev prompt 与 sprint-4 记录逐字节相同 | 14/14 |
| R0 prompt sha = A5 B0 `prompt_sha256` | 53/53 |
| R1 prompt = A5 prompt + 空行 + 记录全文 | 53/53 |
| 53 份记录 sha 与清单一致，且从 A5 运行目录重新渲染逐字节相同 | 53/53 |
| 槽位数 | 318 |

第一次运行 preflight 时，Docker Desktop 在跑完第一道题后停了，其余 21 道题失败，终端里能看到的报错都是连不上 Docker API。重启 Docker Desktop 后重跑，全部通过。上表是第二次的结果（报告文件已被覆盖）。

## 5. mock 端到端

`python scripts/run_a6_retry.py --mock --mock-slots`：`_MockLLM`，真实 clean 镜像和 grader。选槽规则是按队列顺序走，某组还不满 2 个且 repo 没用过就取。用时约 70 秒。

| 槽位 | status | 调用 | 花费 | 隔离 | digest | 第一条 user 消息 | 独立复核 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| pytest-dev__pytest-7324/r0/b0r2/r3 | fail | 1 | 0.000 | 通过 | 一致 | 935 字节 | 通过 |
| sphinx-doc__sphinx-7590/r0/b0r1/r3 | fail | 1 | 0.000 | 通过 | 一致 | 1066 字节 | 通过 |
| django__django-15022/r1/b0r2/r3 | fail | 1 | 0.000 | 通过 | 一致 | 2381 字节 | 通过 |
| sympy__sympy-19040/r1/b0r3/r3 | fail | 1 | 0.000 | 通过 | 一致 | 3946 字节 | 通过 |

- 每个 summary 都有 `mock: true`、`profile: "b0-v2"`、`variant: "B0"` 和 `retry`（R1 的 `attempt_sha256` 等于清单里该记录的 sha），`harness_tool_errors` 为 0，模型为 `mock-model`。
- runner 报告 `runs/a6-retry-mock/mock-report.json`：`halt_reason` 为 null，启动 4 次（R0 2、R1 2），注入核对 4 次，没有 infra，花费 0.000。
- 独立复核另写了一个脚本：R0 的第一条 user 消息 sha 等于 A5 sha，也等于 summary 里的 sha；R1 的第一条 user 消息从 `"\n\n<previous_attempt>\n"` 处切开，前半段 sha 等于 A5 sha，后半段等于记录全文，整条的 sha 等于 summary 里的 sha。
- mock runs 文件：`docs/sprint/a6-retry-runs.mock.json`，4 行，`scope: "mock"`，`attempts_sha256` = `bd932529…`，`handoff_sha256` = `df678c991649133ef09660a6b4f0834de2e3675cb7af4ab1582c63491af1d35a`。

**agent 侧分析脚本。** 本轮开工时，agent 仓库只有 `a6-retry-freeze`；跑完 mock 后再查，`a6-retry-freeze-r1` 已经存在（指向 `01db102`），所以这一步没有跳过。用 `git -C ../coding-agent archive a6-retry-freeze-r1 scripts` 把脚本导出到 `runs/a6-retry-logs/agent-r1/` 再运行，agent 仓库的工作区和 tag 没有动。

```
python runs/a6-retry-logs/agent-r1/scripts/analyze_a6_retry.py --runs docs/sprint/a6-retry-runs.mock.json \
  --attempts docs/sprint/a6-attempts.json --harness-root . --out runs/a6-retry-logs/agent-r1/mock-report.md
STOP mock_input:a6-retry-runs.mock.json      （退出码 2，没有生成报告）
```

补充验证：把 mock 文件的 `scope` 改成 `"a6-retry"`，做一个临时副本（只放在 `runs/` 下，没有提交）再跑，脚本在行级检查停下：`STOP mock_input:runs/a6-retry-mock/django__django-15022/r1/b0r2/r3`。两层拦截都有效。

## 6. 全量测试（各跑两次）

| 环境 | 第一次 | 第二次 |
| --- | --- | --- |
| `.venv` | 661 passed，22 skipped | 661 passed，22 skipped |
| 系统 Python（Anaconda） | 484 passed，199 skipped | 484 passed，199 skipped |

`.venv` 的 661 = 上轮 633 + 本轮新增 28（构建测试 5 个、runner 测试 23 个）。没有失败，也没有 error。系统 Python 多出来的跳过都是缺 pytest-asyncio（177 个）；两种环境共有的跳过是：需显式开启真实 Linux Docker 15 个、需要 Linux 进程组 6 个、需开启 Docker Desktop 1 个。

## 需要审计决定

1. **没有接 `fault_alarm`。** 计划第 5 节第 3 步把它列为可复用函数，但第 1 节的停止条件里没有"连续 N 次全不解出"这一条；而且 A6 的题都是 A5 失败过的，全不解出本身不一定是 harness 故障。runner 只实现第 1 节列出的条件。如果要加，请给出阈值。
2. **`harness_tool_errors > 0` 即停。** 这是复用 `run_checks` 带进来的 A5 规则，第 1 节没有写。保留了下来。
3. runs 文件顶层多了 `slots_expected`，mock 文件多了 `note`；agent 脚本不读这两个字段。
4. `materialize_runner_task` 和 A5 一样，会按同样内容重写 `runs/sprint5-main-runner/<id>/receipt.json`。这不是 A5 的运行目录。

没有打 tag，没有 push。下一步是 A6-2（冻结和 canary），等审计。
