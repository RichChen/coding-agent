# 审计：A6-1（两侧）

日期：2026-10-13。审计对象：harness `96db678` 的 `CHECKPOINT-A6-1.md`，coding-agent `65d96b7` 的 `CHECKPOINT-A6-1.md`。

**结论：两侧 A6-1 通过，附下面几项修改。** 泄漏检查第 1、2 项的命中不构成泄漏，不阻断；harness 按本文改两处小地方后继续第 3–6 步；agent 侧做两处文字和脚本修改，打新 tag。

审计核对过的内容：两份 CHECKPOINT；`runs/a6-retry-logs/leak-check.json` 的命中分布（与 CHECKPOINT 表格一致：第 1 项 34、第 2 项 58、第 3 项 0、第 4 项 113）；A5 B0 r1–r3 里 4 次 `delta_lost`（django-13964 r2、django-15022 r2、pytest-5840 r3、sphinx-8120 r2，都是用满 40 次、`changed_files` 为空）；agent 侧预注册对 `a6-attempts.json` 键名的写法。没有逐份读 53 份记录。

## 1. 泄漏检查第 1、2 项：接受，不阻断

计划第 4 节"1–3 任何命中都阻断"的本意，是拦住私有材料流进记录。这次的命中都不是这种情况：

- 第 1 项 34 次全部是原始测试文件里已有的测试名或 node id，clean 镜像里 agent 本来就能看到；它们出现在 agent 自己跑出来的测试输出或 diff 上下文里。
- 第 2 项 58 次里，diff 上下文和删除行的 20 次内容都在 agent 改动文件的原始版本里；其余是 agent 自己写出的行，碰巧和隐藏测试相同（主要是 sympy-13091 三份），或者是 agent 自己在命令里写的内容。
- 构建路径不读 grader 结果和私有 patch：私有材料只进 `leak_check`，记录文本只来自第一次运行的 summary、delta、events 和原始源码。

所以判定口径从"文本相同"改为"来源"：**记录里每一段都只能来自第一次运行的产物和原始源码。** 第一次运行本身就能产生这些文本，再交给同一个 agent 不会多给它任何私有信息。

为了让这条口径可以检验，harness 要补一个测试（见第 4 节第 1 条）。第 1–3 项计数照常写进清单和报告，作为描述。

第 4 项（gold 新增行）按原计划只报告。113 次、18 份记录都保留，这是第一次尝试改对了部分细节，属于 A6-R 要测的信息本身。

记录文件和清单可以提交进 git。仓库不进入 agent 的容器，提交里出现和隐藏测试相同的文本，不影响隔离。

## 2. harness 侧实现细节第 1–9 条

全部认可，只有一处要改：

- **第 2 条 "Files changed"。** 只改了测试文件的 2 份记录（django-15973 b0r3、sphinx-9258 b0r2）现在写 `none (no source changes were submitted)`，下面的 diff 却显示有改动，读起来自相矛盾。改为：非测试文件为空、但 delta 里有测试文件时，写 `none (only test files were changed; see the diff)`；delta 为空时仍写原文。其余记录不受影响。这会改动模板 sha 和清单 sha，重建后重报。
- **第 9 条。** R0 的 `retry` 写 `{arm: "r0", first, attempt_sha256: null}`，认可。

4 份 `delta_lost` 记录：包装句写的是"final changes were submitted"，而这几次实际上什么都没收集到。A5 把它们算作失败，记录里 Files changed 和 diff 都如实写了 none，R0、R1 两组都受同样的处理，**不改**。在 CHECKPOINT 里列出这 4 份即可。

## 3. agent 侧需要审计决定的四项

1. **结论句里的 X。** 不要用 A5 的 s=0.35。X 改为 2.8 × s_obs / √N，s_obs 是 A6 实际 d_t 的样本标准差，同时报 95% 区间上限，对应 A5 报告里"数据下限"的写法。第 1 节的功效句照抄不动。
2. **`a6-attempts.json` 的键名。** 以 harness 实际为准：列表在 `records`，计数在 `attempts`。预注册"输入文件约定"一节改成这样（第 1 节不动），脚本只接受 `records`，不再两种都认。
3. **`testing/` 规则。** 认可。
4. **`a6-retry-runs.json` 的字段。** 照 agent 预注册的列表，由 harness 的 runner 实现（见第 4 节第 3 条）。

第一次全量测试出现的 85 个 error 不阻断，但在下一个 CHECKPOINT 里再跑两次全量测试，把结果写上。

agent 侧 tag 沿用 A5 的修订写法：保留 `a6-retry-freeze` 不动，修改后打 `a6-retry-freeze-r1`。harness 的冻结记录引用 `-r1`。

## 4. harness 侧接下来做什么

1. 补测试：私有材料目录（`runs/sprint5-main-private/` 和校准 JSON）不可读或换成垃圾内容时，`render_record` 生成的 53 份记录和正常情况逐字节相同。泄漏检查本身可以在这种情况下报错，测试只针对渲染。
2. 按第 2 节改 "Files changed" 的 none 文字；重建 53 份记录；提交 `docs/sprint/a6-attempts/` 和 `a6-attempts.json`，报新的模板 sha 和清单 `handoff_sha256`。
3. 继续计划第 5 节 A6-1 的第 3–6 步：`run_a6_retry.py`、`--preflight`、mock 端到端、全量测试。runner 写出的 `a6-retry-runs.json` 字段必须和 agent 预注册"输入文件约定"一节一致（`task_id`、`repo`、`arm`、`first`、`k`、`run_dir`、`mock`、`status`、`solved`、`model_calls`、`first_edit_step`、`cost_cny`、`changed_files`、`prompt_sha256`、`retry`；顶层是 `schema`、`scope`、`attempts_sha256`）。mock 端到端要生成一份 mock scope 的 `a6-retry-runs.json`，交给 agent 侧的分析脚本跑一次，确认它能读，而且按设计因为 mock 而 STOP。这一步只读 agent 仓库，不改它。
4. 写 `CHECKPOINT-A6-1b.md`，停下。
