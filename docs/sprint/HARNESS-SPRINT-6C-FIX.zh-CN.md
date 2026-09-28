# HARNESS R6 修订 3：补上 issue 文本，B0 重新开始

日期：2026-09-29。依据：CHECKPOINT-6a（修订 2 之后的 B0 停止）审计。

## 审计结论：0/36 的根因是 agent 没有拿到 issue

- **现象。** pool 运行的 user prompt 里，`Public issue:` 下面只有一行占位文字 `Public issue for <task_id>`（38 个字符）。dev 运行拿到的是完整的 SWE-bench `problem_statement`（例如 django-10914 有 1022 个字符）。
- **原因。**
  - `scripts/select_main_targets.py` 写私有文件时只保存了 `instance_id`、`FAIL_TO_PASS`、`PASS_TO_PASS`、`patch`、`test_patch`，漏掉了 `problem_statement`。
  - `run_a5_main.py` 的 `materialize_runner_task` 在取不到时，静默回退成了占位文字（`private.get("problem_statement") or ("Public issue for " + task["id"])`）。
- **影响范围。** `runs/a5-main/` 下的 38 份 `events.jsonl`（36 个正式槽位加 2 个 infra 槽位）全部是占位文字。修订 2 之前作废的 25 次运行也是一样。
- **其他部分没有问题。** 我对比了 dev 和 pool 的运行：system prompt 完全相同，user prompt 模板相同（issue 之前的部分），`config_hash` 相同。差异只有镜像 digest（本来就不同）和 artifact 配额（R5 修 StoreError 时调大的）。所以 issue 文本是唯一的实质差异。
- **为什么之前没有发现。**
  - 预检和 mock 端到端只检查了 public task 能否生成、有没有泄漏私有字段，没有检查内容是否为空。
  - canary 的检查项都是基础设施项。
  - 没有人读过一次 pool 运行的真实 prompt。

  审计也有责任：R5 审计时我读过 `materialize_runner_task` 这一段，没有指出这个静默回退。

## 执行顺序

H1 → H9。全部通过后不用停下，直接做 canary 和全量 B0，完成后停在 CHECKPOINT-6a。

## H1 补齐 issue 文本

1. 从 `princeton-nlp/SWE-bench_Verified`（split `test`，与选题时相同）读取这 60 道题的 `problem_statement`，写到 `runs/sprint5-main-public/<id>.json`，字段包括：
   - `issue_text`：原样保存，不 strip，不追加 `hints_text`，和 dev 口径一致；
   - `issue_sha256`；
   - `repo_ref`。
2. 在 `docs/sprint/main-issues.json` 里记录每道题的 `issue_sha256`、字符数，以及数据集的 fingerprint 或 revision。
3. **选题不变。** 60 道 id 列表的 sha 必须仍是 `d4caaa48…`，56 道合格列表不变。`select_main_targets.py` 以后生成私有文件时也要写 public 文件，但本轮不重新选题。
4. `materialize_runner_task` 改为读取这份 public 文件，不再从私有文件取 issue。

## H2 去掉静默回退

1. `materialize_runner_task`：public 文件不存在、`issue_text` 为空、或者 sha 和 `main-issues.json` 不一致，都报错。
2. `public_issue`：`issue_text` 为空或匹配 `^Public issue for ` 时报错。
3. 在 runner、prompt 构造、public task 生成相关的代码里，找出类似 `x or "<占位>"` 的回退（issue、repo、revision、test command 等），都改成缺失即报错。在 CHECKPOINT 里列出改了哪几处。
4. 加测试。

## H3 预检检查 prompt 内容

`--preflight` 新增一步：对每道合格题渲染完整的 user prompt，检查以下各项：

- prompt 里包含原样的 `issue_text`；
- sha 和数据集一致；
- 长度大于 0；
- 不含私有字段的内容（沿用已有的检查）。

**必须 56/56 通过。** CHECKPOINT 里报告 issue 字符数的最小值、中位数和最大值。

另外做一项一致性检查：用当前代码为 14 道 dev 题渲染 prompt，结果必须和 `runs/sprint4-b0-v2/<id>/r1/events.jsonl` 里记录的 user prompt 逐字相同。这样可以证明 dev 和 pool 的 prompt 口径一致。

## H4 summary 记录 prompt 指纹

summary 里新增 `issue_sha256` 和 `prompt_sha256`。canary 检查项新增"`issue_sha256` 等于 `main-issues.json` 里的值"，并在 CHECKPOINT 里贴出每道 canary 的 issue 前 200 个字符，供人工核对。

## H5 故障警报（预注册）

全量 B0 里（不含 canary），完成的正式运行达到 30 次时，如果解出数为 0，就停下等审计。

这一条只用来发现 harness 故障，不改变实验设计：触发后只允许排查 harness，不允许因此调整题目、profile 或卡片。写进冻结修订。

## H6 候选改动导致的 missing 不再触发停止

批准 CHECKPOINT 里建议的规则：

- 如果 grader receipt 的 `runner_error` 或收集阶段的 traceback 里，最内层属于项目的栈帧所在文件是本次候选改动里修改过的文件，就把这次运行记为普通失败（`solved=false`），并记录 `grader_candidate_error`，不停止。
- 其他 missing 照常停止。
- 加测试：候选改动引入 `IndentationError` 时判为普通失败；候选改动为空、但出现 missing 时仍然停止。

## H7 作废已有运行

1. 把 `runs/a5-main/` 下的全部运行（36 个正式槽位、2 个 infra 槽位、`b0-report.json`）移到 `runs/a5-main-void/r2-no-issue/`，只移动，不删除，并写 `README.md`。
2. 作废规则：修订 3 之前的全部 B0 运行，不论结果。
3. 已花的 24.055 元记为作废开销，不计入实验。

## H8 预算

- B0 软上限 120 元，`TOTAL_CAP` 230 元，只统计 `runs/a5-main/` 下的花费。
- `PARALLEL` 仍为 3。

## H9 冻结修订 3

`A5-MAIN-FREEZE.md` 新增"修订 3"一节，写明：

- 根因；
- H1–H8 的提交；
- `main-issues.json` 的 sha；
- 作废规则；
- 故障警报规则；
- 候选改动错误规则。

全量测试通过后打 tag `a5-main-freeze-r3`，旧 tag 保留。

## 之后（不用停下）

1. **canary 每个 repo 各取一道。** 取按 `created_at` 排序后的下中位题，共 5 道，各跑一次真实 B0 r1。

   检查项：原有的全部检查项，加上 `harness_tool_errors == 0` 和 issue sha 一致。
2. 通过后跑全量 B0。
3. 以下情况停下，写 CHECKPOINT-6a：
   - 停止条件触发（包括 H5 的故障警报）；
   - 预检或 canary 不通过；
   - B0 跑完。

   CHECKPOINT-6a 里报告每个 repo 的解出率。

不要开始 B2。coding-agent 侧不需要操作。
