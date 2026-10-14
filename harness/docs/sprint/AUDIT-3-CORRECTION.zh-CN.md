# 第三轮审计矫正与后续计划

日期：2026-09-25。
读者：接手审计和计划工作的 agent（包括 Codex 线程 `01a0d7ca`），以及两个执行 agent。
它的地位：这份文件**覆盖** Codex 第三轮审计报告里与下文冲突的结论和建议。第三轮计划书、CHECKPOINT-3 的原文不改。

## 1. 最重要的发现：agent 能看到隐藏测试（第二、三轮都存在）

**事实**（审计时逐项核对过）：

- dev 集的 baseline 镜像是用 `baseline.tar.gz` 构建的（`scripts/preflight_a5_repo_baseline.py` 第 382–383 行）。在 `apply_patch_tree()` 里，`baseline` = 原始代码 + **test patch**；`known-good` = baseline + gold patch。
- `BaselineImageBackend.start()` 把 `/opt/repo` 原样复制到 agent 的 `/workspace`。所以 agent 的工作区里**已经有了这道题的 F2P 测试**。
- 以 `runs/sprint3-b0/*/r1` 为例：
  - sympy-11400：`staging/original` 里没有 `test_ccode_sinc`，`staging/baseline` 里有。agent 用 `search_code` 搜到了它，读了它，还执行了 `pytest sympy/printing/tests/test_ccode.py::test_ccode_sinc`，一共 14 条事件。
  - sklearn-10949：同样的情况，agent 直接运行了 F2P 测试 `test_check_dataframe_warns_on_dtype`。
  - django-11039：agent 直接运行了 F2P 测试 `test_sqlmigrate_for_non_transactional_databases`。

**后果：**

- 这违反了总合同和各轮计划书的硬约束："test patch 和 F2P / P2P 不能出现在 agent 的工作区里"。
- `b0-v1` 的 32/42，以及第二轮的 6/12，都是在"**能看到隐藏测试**"这个条件下得到的。它们**不能作为 B0 基线**，只能作为"测试可见"条件下的参考数据保留。
- v4 记忆卡片的轨迹也来自这些运行。卡片里的 `tests` 字段写的就是源题自己的 F2P 测试名，`validated_fix` 标签是在有测试答案的条件下得到的。卡片本身不会泄漏目标题的答案，因为源题和目标题不相交；但记忆的质量被高估了。**v4 必须等修复后的新运行出来，再重建。**

**责任：** 第二轮计划书写的是"参照 preflight 从 `/opt/repo` 复制到 `/workspace`"，但当时没有核对 `/opt/repo` 里装的是什么。这是计划本身的错误。执行 agent 和 Codex 的审计也都没有发现这个问题。

## 2. 对 Codex 第三轮审计的矫正

Codex 的审计大部分是准确的：B0 的数字、v4 没有转成 final、CHECKPOINT-3 里把 gold 失败的题数写成 6（实际是 7）、未跟踪的诊断脚本、thinking 不做，都核对无误。它也没有改动任何文件。需要矫正的是下面几条。

### 2.1 pilot 校准"0/20 接受"的原因，是镜像和 grader 不匹配，不是题目本身不适合

`runs/sprint3-pilot-calibrate/results.jsonl` 里，有打分结果的 16 道题，**每一道的空改动结果和 gold 结果都完全相同**（F2P 和 P2P 的计数一模一样）。gold patch 对结果没有任何影响，所以这不可能是题目的问题。原因如下：

- pilot 的镜像大多是 `coding-harness-a5-known-good@...`，也就是 gold **已经打在 `/opt/repo` 里**。其余的是 `a5-recheck` 和 `a5-pytest`，后者根本没有 `/opt/repo`。
- 旧的 pilot 校准（`scripts/calibrate_a5_image_grader.py`）标准是："known-good 镜像能跑通 F2P，并且整个仓库都能被收集"。它**从来没有验证过"在这个镜像里空改动会失败"**。所以旧的"19/20 grader_ready"和新 `ImageGrader` 要求的"/opt/repo 是未修复的代码"根本不是同一个东西。
- 按当前 `runs/sprint3-pilot-calibrate/results.jsonl` 的原始计数，16 道有打分结果的题都满足空改动与 gold 的 F2P/P2P 计数完全相同：其中 8 道两者的 F2P 有通过，8 道两者的 F2P 都没有通过。这里不再沿用旧表里的 9/7 文字；结论仍然是 gold 对结果没有产生作用，说明镜像和打分链路不匹配。

**结论：** 不要换 pilot。要为 pilot 题准备**和 dev 同一种构建方式的镜像**，再重新校准（见第 3 节 R4-3）。只有在正确的镜像上校准仍然失败的题，才按固定规则从分母中剔除或替换。

**额外警告：** 绝对不能把 known-good 镜像交给 `BaselineImageBackend` 作为 agent 的工作区，那等于把 gold 答案直接给了模型。

### 2.2 不要在当前数据上构建 v4 final，也不要开始 memory smoke 或 A5-lite

Codex 建议的第一步是"读取已经存在的 `memory-source-runs.json`，构建 v4 final"，第三步是"跑 B0/B2/B3 smoke"。在第 1 节的泄漏修复之前，这两步都会把错误继续往下传。**全部暂停。**

另外，coding-agent 的 CHECKPOINT-3（12:24）早于 harness 产出交接文件的时间（13:47）。它停下来的时机是按计划书执行的，不是"慢了一步"。而且因为第 1 节的问题，现在反而不应该用那个交接文件。

### 2.3 不要增加实验变体

Codex 建议把失败尝试做成"负面导航变体"，把 unverified 单独做成对照组，把 relocated 和 valid 分开成不同条件。这会让实验矩阵成倍增大，而记忆源一共只有 15 道。

决定如下：

- 首轮实验只比较 **B0 和 B2**。
- B2 **只注入 `validated_fix` 卡片**。这一点采纳 Codex 的意见；`failed_attempt` 和 `unverified` 不注入。
- `relocated` / `unknown` 只在 summary 里记录，不单独成为一个实验条件。
- B1 和 B3 等 B2 出现信号之后再说。

### 2.4 测试时的 `WinError 5` 是运行环境的 ACL 问题，不是业务代码的问题

`git status` 在两个仓库里都会报大量的 `Permission denied`，涉及 `docs/upgrade/evidence/**/session/` 和 `coding-agent/traces/pre_harness_*`。这些目录是早先在沙箱里运行时创建的，ACL 受限。在沙箱里跑 pytest 看到的 `WinError 5` 是同一个原因。

- 不要因此把"测试结果"判定为失败。应该在能正常读取这些文件的环境里重新运行，或者使用仓库内可写的 `--basetemp`。
- `event_extract.resolve_value()` 捕获 `PermissionError`，并记为 `artifact_unreadable`：这是一处可以顺手做的小改动，**不单独立项**。
- ACL 本身的修复（重置这些目录的权限）需要人工在非沙箱的终端里做，不要让 agent 批量改权限。

### 2.5 优先级：先保证实验有效，再管工程卫生

Codex 列出的绝对路径、未跟踪的诊断脚本这类问题，属于工程卫生。在这个单机研究项目里：

- 4 个诊断脚本：提交到 `scripts/diagnostics/`，或者删掉，二选一，顺手处理即可。
- 交接文件里的绝对路径：**本阶段不改**。

审计时的优先级顺序：**答案隔离 > 打分是否有效（空改动失败、gold 通过、gold 确实改变了结果）> 实验设计 > 花费 > 工程卫生。** 不要把这几类问题混在一起、按同等权重列出来。

## 3. 后续整体计划

### R4（下一轮）：修正实验有效性，大约 17 CNY

**harness：**

1. **agent 工作区和镜像都不能暴露测试补丁。** 优先用原始源码归档（不含 test patch/gold patch）构建新的 agent baseline image；不能把旧的 `baseline.tar.gz` 或 known-good image 直接交给 agent，因为即使 workspace 恢复，模型仍可通过 `run_command` 读取镜像里的 `/opt/repo`。在过渡检查中，`BaselineImageBackend.start()` 仍按 receipt 的 `test_patch_paths` 把工作区恢复成 `staging/original`，并由宿主机做隔离校验；但只要 `/opt/repo` 仍含测试补丁，就不得启动模型。`test_patch_paths` 只在宿主机上使用，不写进 prompt，也不写进工具输出。然后：
   - 每次运行开始时做一次**答案隔离检查**：工作区里这些文件的 sha256 必须和 original 完全一致，不一致就让这次运行失败。检查结果写进 summary。
   - 导出 delta 时，把"恢复成 original"这一步本身造成的差异排除掉。只有模型真的改动了这些文件时，才算进 delta，并记进 `test_files_touched`。
   - grader 不变：仍然是先应用 delta，再用 test patch 覆盖。
   - 零模型测试：对 14 道 dev 题逐一验证，工作区里搜不到任何 F2P 测试名。
2. **校准增加"gold 必须改变结果"这条检查。** 如果空改动和 gold 的所有 nodeid 结果都一样，就标记为 `delta_has_no_effect`，这道题判定为不合格。dev 集按新规则重新校准一遍（零模型）。
3. **pilot 镜像。** 为 20 道 pilot 题找到或构建**和 dev 相同类型**的 baseline 镜像（用 `preflight_a5_repo_baseline.py` 的流程：`baseline.tar.gz` 加依赖），配合第 1 条的恢复机制。3 道 pytest 题同样处理。然后用 `ImageGrader` 做空改动 / gold 校准，加上第 2 条的检查。这一步不调用模型。
4. **B0 重跑。** 打 tag `b0-v2`，14 题 × 3 次重复，约 16 CNY。`b0-v1` 的结果保留，标注为"测试可见条件"。报告里把 v1 和 v2 并排列出，这个差距本身就是一个有用的数据点，说明"看得到测试"值多少。
5. 处理 4 个诊断脚本，把 CHECKPOINT-3 里 6 和 7 的计数改正写进 PROGRESS。

**coding-agent：**

1. 等 harness 产出新的交接文件（`profile_tag: b0-v2`），再构建 v4 final。在那之前，v4 保持 interim，不再调整。
2. 调整 B2 的注入策略：只注入 `validated_fix`（见 2.3）。dev 留一法的表按新策略重新出一份。
3. 顺手修 `resolve_value()` 的 `PermissionError`（见 2.4）。

**审计节点 R4**，重点检查：

- 答案隔离检查在所有运行里都通过；
- pilot 有多少道题在正确的镜像上校准合格；
- `b0-v2` 的解出率，以及和 `b0-v1` 的差距；
- v4 final 的 `validated_fix` 卡片有多少张。

### R5：第一次正式记忆对照，大约 50–60 CNY

1. dev 留一法冒烟：14 题 × B2 × 1 次，约 6 CNY。只验证链路，看一眼注入内容是否合理。
2. **A5-lite**：在 R4 校准合格的 pilot 题上跑 B0 和 B2，各 3 次重复。按 20 题估算，约 120 次运行，约 47 CNY；题数少了按比例减。
   - 运行前**冻结**：`b0-v2`、v4 final 的 sha256、pilot 题单。
   - 预先写好分析方法：按题配对比较 B0 和 B2 的解出次数，并单独报告"B2 实际注入了卡片"的那部分题。
3. 结论只写数据能支持的。题数很少，所以只报告方向和逐题结果，不写显著性。

### R6 及以后：看 R5 的结果再定

- **B2 有正向信号**：扩充记忆源（sphinx，以及每个仓库补到 5–8 道源题，按 `MEMORY-SOURCE-EXPANSION.md` 的固定规则选题），然后加入 B1 和 B3 做消融，扩大重复次数。
- **没有信号**：先分析原因。是注入的卡片不相关（检索的问题），还是模型没有使用卡片（呈现方式的问题），还是 B0 已经接近上限（题目太简单）。在这个基础上决定是改记忆形态，还是换更难的题。
- **独立的 harness 功能**（不和实验绑在一起，单独立项）：reasoning 回传以支持 thinking；绝对路径和可移植性的清理；ACL 修复。

## 4. 接手这项工作时需要遵守的约定

- 写进计划书的每个技术前提，都要先对照代码或产物核实。"镜像里 `/opt/repo` 装的是什么"这一类问题，必须实际看过才能写。
- 审计时，先看运行的**事件流**，看 agent 实际看到了什么、做了什么，而不只看汇总数字。
- 看到"空改动 = gold""全部是 missing""全部是 unknown"这类过于整齐的结果时，先怀疑链路，不要先怀疑题目。
- 保持计划简洁，一轮只解决一类核心问题。不要为了完备而增加变体、检查项和交接字段。
