# coding-harness 第三轮计划书：修正打分链路，冻结 B0，接入记忆

日期：2026-09-25。执行者：挂在 `D:\crq\src\coding-harness` 的 Cursor agent。
前置：`HARNESS-SPRINT-2.zh-CN.md` 和 `CHECKPOINT-2.md`。第一轮第 1 节的硬约束继续有效，除非本文另有说明。
配套：`D:\crq\src\coding-agent\docs\sprint\AGENT-MEMORY-3.zh-CN.md`。两边通过第 3 节的两个交接文件协作。

## 0. 审计结论：第二轮的结果与需要更正的地方

第二轮有效：agent 跑在装好依赖的 baseline 镜像里，改动能完整收集，grader 在镜像内打分并经过空改动 / gold 校准。B0 在 12 道 dev 题上解出 6 道，平均每题约 0.37 CNY。5227 重放后确认解出。

审计时逐条核对了 `runs/sprint2-b0/`，有三处结论需要更正或补充：

1. **sklearn 三题 P2P 为 0 的原因不是 `.so` 混进 delta。** 保存下来的三份 `candidate-delta.json` 各自只有 1 个 `.py` 文件（`ridge.py`、`validation.py`、`mixture/base.py`），没有 `.so`，三个文件都能被 `ast.parse` 解析。`grader-result.json` 里 29–45 条用例全部是 `missing`，同时 `receipt_complete=True`，说明 pytest 正常结束但没有收集到这些测试。第二轮校准（`runs/sprint2-calibrate/results.jsonl`）用的是同一个 `ImageGrader` 和同一个 `prepare_repo_runtime`，这三题的 gold 都通过了。所以最可能的原因是**模型的改动在导入时就出错**（`ast.parse` 查不出 NameError、ImportError 这类运行期错误），也可能是两次评测之间有某种环境差异。现在无法判断，因为 `ImageGrader` 没有把收据里的 `collection_errors` 和 `runner_error` 写进结果。**先诊断，再决定修什么。**
2. **sympy-11870 的 `delta_lost` 是终止路径的问题。** 结果 artifact 里 `termination_kind=step_deadline`。`AgentLoop.run()` 的 `finally` 里是 `backend.close(snapshot=result is not None and backend.active)`（`src/runtime/loop.py` 第 459 行附近），`snapshot_error` 为空，说明导出根本没有执行，很可能是 deadline 路径下 `backend.active` 已经是 False。另外 `configs/sprint/b0.yaml` 里 `policy.command.timeout_seconds=120`，和 `runtime.step_timeout_seconds=120` 相等，而单步时长 = 模型调用 + 工具执行，所以一条慢测试就会让整个运行以 `step_deadline` 结束，而不是作为"命令超时"返回给模型。
3. **`stop_reason` 仍然 12 题都是 `unknown`。** `_stop_reason()` 优先读 `run.finished` 事件的 payload，而这个 payload 被外置成了 `{"artifact_ref": ...}`，里面没有 `failure_reason`。真实值在 `session/artifacts/<sha>` 里，`plain(result)` 里也有。

另外：`verify_memory()` 还在用旧的 `RepositoryGrader`（受 `MAX_FILES` 限制），和 dev 评测不是同一条路径。

**thinking 不在本轮范围。** `src/llm/client.py` 只接受 `thinking: disabled`，报错信息是 "reasoning replay is not implemented"。前两轮计划书没核对这一点就写了 thinking 对照，这是计划的错误。本轮以及之后的计划，在单独立项实现"reasoning 回传"之前，不再安排 thinking 相关的运行。

本轮目标：**把打分链路里剩下的错误修干净，把 B0 冻结成可复现的基线并测出方差，准备好 pilot 的新打分，把记忆插件接入 runner，并在 dev 集上先做一次记忆的冒烟对照。**

## 1. 本轮规则补充

- **花费原则：钱要花在能产出有效证据的运行上。** 本轮真实模型花费上限 **40 CNY**，单次运行上限 1 CNY。每一步开跑前在 PROGRESS 里写下预计花费，跑完写实际花费。第 1–4 步和第 6、7 步不花模型钱。
- 继续往 `docs/sprint/PROGRESS.md` 追加记录，标题用"第三轮 第 N 步"。开工前先提交本计划书和第二轮计划书（两份目前都未跟踪），再打 tag `sprint3-start`。
- 20 道 pilot 题的 hold-out 不变：**不在 pilot 题上跑任何模型**。第 6 步只对 pilot 题做零模型校准，需要单独的脚本，`run_swe_task.py` 里对 `HOLDOUT` 的拒绝逻辑保持不动。
- CHECKPOINT-2 里关于 `.so` 的解释，在第 1 步诊断出结果后，到 PROGRESS 里写一条更正，不要改写 CHECKPOINT-2 原文。
- thinking：见第 0 节，不做。

## 2. 分步计划

### 第 1 步：grader 诊断信息与 sklearn 重新打分（不花钱）

1. `ImageGrader.evaluate()` 把收据的诊断信息写进结果：`collected` 数量、`collection_errors`（每条截断到 2KB，最多 20 条）、`runner_error`、`exit_code`，以及 `execution.stderr` 的末尾 4KB。这些只写进宿主机上的 `grader-result.json`，不进入 agent 的工作区或 prompt。
2. 写一个零模型脚本（比如 `scripts/regrade_saved_delta.py`），对指定运行目录里保存的 `candidate-delta.json` 重新调用 `ImageGrader`，输出到 `grader-result.regrade.json`，不覆盖原文件。
3. 对 sklearn 10297、10949、11281 重新打分，看 `collection_errors` 里是什么。
   - 如果是模型的改动在导入期报错，这三题就是**真实的模型失败**，结果保留为 fail，并在 PROGRESS 里写明错误类型。
   - 如果是环境问题（比如扩展模块导入失败），就找出校准路径和运行路径的差异并修好，再重新打分，同时重做这三题的 gold 校准，确认仍然通过。
4. 防御性改动：`EXPORT_DELTA` 跳过编译产物（`*.so`、`*.pyd`、`*.o`、`*.dylib`，以及 `build/` 目录）。在 summary 里记录被跳过的文件数，不能静默丢弃源码文件。补单元测试。

### 第 2 步：终止路径也必须导出改动（不花钱）

1. 先确认 11870 为什么没有导出：`step_deadline` 触发时 `backend.active` 是什么状态，容器是否已被杀掉，是谁杀的。写进 PROGRESS。
2. 修复目标：**不管运行是正常结束，还是因为 step / run deadline、预算耗尽、工具异常结束，只要容器还能访问，就先导出 delta，再清理。** 如果容器确实已经不在了，就把 `snapshot_error` 写成明确的 `container_gone_before_snapshot`，不能留空。
3. 超时关系调整，写进新的 profile `configs/sprint/b0-v1.yaml`，旧的 `b0.yaml` 不动：
   - `policy.command.timeout_seconds` 保持 120；`runtime.step_timeout_seconds` 从 120 提高到 300（必须明显大于"命令超时 + 一次模型调用"）；`total_timeout_seconds` 按 40 次调用重新估算，建议 2400。
   - 命令超时时，工具结果要把"命令在 120 秒后超时，输出已截断"如实返回给模型，运行继续。用 mock LLM 加一条 `sleep 200` 命令验证：运行不因 step_deadline 结束，模型能收到超时结果。
4. 单元测试：用 fake backend，模拟"编辑之后触发 step_deadline"，断言 `candidate_delta` 不为空。
5. 11870 用事件重放补打分：参照第二轮对 5227 的做法，把 `tool.intent` 里的编辑按顺序在 baseline 镜像里重放，导出 delta，再用 `ImageGrader` 打分。结果写进 PROGRESS。

### 第 3 步：`stop_reason` 和 `verify_memory`（不花钱）

1. `_stop_reason()` 改为：先读 `plain(result)` 里的 `failure_reason` 和 `termination_kind`；取不到时，如果 `run.finished` 的 payload 是 `artifact_ref`，就到 `session/artifacts/` 里解引用。补一个测试夹具，其中 `run.finished` 的 payload 是 artifact 引用。
2. 顺手修 `apply_delta()`：它按 `change["content"]` 解码，但 `BaselineImageBackend` 导出的 `changed` 值是 base64 字符串。两种格式都要支持，或者删掉已经不用的旧路径。
3. `verify_memory()` 改用 `ImageGrader`（和 dev 评测同一条路径），只对有 baseline 镜像并通过校准的源题打分。5221 在第二轮校准里 gold 的 F2P 是 0/2，记为 `grader_unavailable`，原因写 `gold_fails_calibration`。更新 `docs/sprint/memory-source-verification.json`。

### 第 4 步：冻结 B0 profile（不花钱）

1. dev 集加入第二轮校准已通过、但没有纳入的 `scikit-learn__scikit-learn-10508` 和 `scikit-learn__scikit-learn-11040`，共 14 题。其中 11040 是记忆源题，本身就应该有新环境下的轨迹。
2. 确认 `b0-v1.yaml` 和 `prompts/swe_b0.md` 的最终内容，用 mock 跑通一次 14 题（零模型，只验证链路和打分）。
3. 提交，打 tag `b0-v1`。**从这里开始到第三轮结束，不再修改 B0 的 prompt、工具集、profile 和 grader 判定逻辑。** 如果发现必须修改的 bug，修完后打 `b0-v1.1`，前面的运行作废重跑，并在 PROGRESS 里写明原因。

### 第 5 步：B0 三次重复（约 16 CNY）

1. 在 `b0-v1` 上跑 14 题 × 3 次重复 = 42 次，输出到 `runs/sprint3-b0/<task>/r<k>/`。第二轮的结果因为 profile 不同，不计入。
2. 汇总表 `docs/sprint/B0-V1-RESULTS.md`：每题的 solved 次数（k/3）、平均花费、调用次数、第一次编辑的轮次、stop_reason。再给出总体的解出率，以及每题结果在 3 次重复之间的一致程度（3/3、0/3，还是混合）。这个方差数据决定后面 A5 的重复次数。
3. 解出的运行，抽 2 道看一下改动是否合理（不是改测试骗过 grader）。所有运行都检查 `test_files_touched`，列出改过测试文件的运行。
4. 产出交接文件 `docs/sprint/memory-source-runs.json`（格式见第 3 节），供 coding-agent 重建记忆。

### 第 6 步：pilot 目标题的零模型校准

1. 新写 `scripts/calibrate_pilot_image_grader.py`，逻辑和 `scripts/sprint2_calibrate.py` 一样（空改动一次、gold 一次，都用 `ImageGrader`），只针对 20 道 pilot 题，**不运行 agent，不调用模型**。这个脚本不能 import `run_task`，也不能修改 `HOLDOUT`。
2. pilot 题的 receipt 和 baseline 镜像，先在 `docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-07/tasks/<id>/` 以及相关的 preflight 证据目录里找（旧方法已校准 19/20，django-13265 是已知的合同阻塞项，见 `A5-pilot-grader-readiness-20260923-08-planA/plan-a-disposition.json`）。找不到镜像的题，在 PROGRESS 里列出，不要现场重建。
3. 产出 `configs/sprint/pilot-tasks.yaml`，格式和 `dev-tasks.yaml` 一致，包括 `p2p_excluded` 和每题的校准结论。私有字段（F2P / P2P 列表、gold / test patch）只通过 receipt 的 `private_source_binding` 引用，不写进 yaml。
4. 再核对一遍 `.gitignore`：pilot 校准产生的任何 private 文件都不能被跟踪。

### 第 7 步：记忆插件接入 runner（不花钱）

1. 在 `src/policy/reposkill.py` 里新增 `register_memory_cards(...)`，参照已有的 `register_public_memory` 的加载方式（`load_adapter` 加上源码摘要校验），改为从 coding-agent 加载 `reposkill_agent.memory.card_plugin.MemoryCardPlugin` 和 `reposkill_agent.memory.cards.load_memory_cards`。构造参数以 coding-agent 当前代码为准：`variant, cards, repo, issue, target_root, max_bytes=4096, min_score=1.0`。
2. `run_swe_task.py` 支持 `--variant B0|B1|B2|B3` 和 `--cards <jsonl 路径>`：
   - **留一法**：传给插件之前，harness 先把 `source_id == 当前题 id` 的卡片过滤掉。这是硬规则，dev 题本身就是记忆源，不过滤就等于把答案喂给模型。
   - `target_root` 使用当前题的原始源码目录。dev 题用 receipt 旁边的 `staging/original`；pilot 题用 `D:\crq\tmp\a5-targets\<id>`（只从 `source.tar.gz` 解压）。
   - summary 新增 `memory` 字段：variant、卡片文件的 sha256、被过滤掉的卡片 id、实际注入的卡片 id 和字节数、B3 拒绝的卡片 id 及原因。
3. 零模型测试：
   - B0 不注入任何内容；
   - 对某道 dev 题用 B2 时，它自己的卡片一定不会出现；
   - 注入的文本出现在 prompt 里，并且不超过 `max_bytes`；
   - 用 mock 跑一次完整链路。
4. 卡片先用 coding-agent 现有的 `benchmarks/a5/memory-cards-v3.jsonl` 调通。v4 就绪后（第 3 节交接文件出现后）换成 v4。

### 第 8 步：dev 集上的记忆冒烟对照（约 11 CNY）

前提：coding-agent 的 `benchmarks/a5/memory-cards-v4.manifest.json` 已存在，`status` 为 `final`，`cards_sha256` 和卡片文件一致，并且 `build_inputs.memory_source_runs_sha256` 等于第 5 步产出的 `memory-source-runs.json` 的 sha256。如果不满足，先做第 9 步，做完后再检查一次；仍不满足就跳过本步，在 CHECKPOINT-3 里写明。

1. 在 `b0-v1` 上跑 14 题 × B2 × 1 次、14 题 × B3 × 1 次，卡片用 v4，严格留一法。
2. 和第 5 步的 B0 放在一起出一张对照表：每题 B0 的 k/3、B2、B3 的结果、注入了哪些卡片。
3. 这一步只用来验证链路，并看一个很粗的信号，**不作为实验结论**：dev 题同时也是记忆源，而且样本太小。

### 第 9 步（有余力再做）：补 sphinx 记忆源的方案和一次端到端试跑

背景：本地的 20 行历史记录（`coding-agent/reports/upgrade/a5-pilot20-preparation-20260921-v4/private/history/`）里没有 sphinx，现有证据目录里也没有 sphinx 的 baseline 镜像，所以 4 道 sphinx pilot 题一张记忆卡都没有。

1. 写 `docs/sprint/MEMORY-SOURCE-EXPANSION.md`：
   - 数据来源：SWE-bench 官方数据集，写明版本和下载方式。
   - 选题规则：同一个仓库；创建时间早于该仓库所有 pilot 题；不在 HOLDOUT 里；按固定规则选（比如按创建时间取最近的 N 道，或者固定随机种子），**不能参考 pilot 题的 gold 或测试来挑**。
   - 源码 tar 包和镜像的构建流程：复用 `preflight_a5_repo_baseline.py` 里 sphinx-doc 的依赖配置。
   - 预计花费。
2. 按方案对 **1 道** sphinx 源题走完整条链路：取数据、打包源码、构建镜像、零模型校准、跑 1 次 B0。成功后把后续批量扩充写成第四轮的提案，本轮不批量做。

### 第 10 步：CHECKPOINT-3

写 `docs/sprint/CHECKPOINT-3.md`，内容包括：

- 第 1–3 步每个 bug 的根因和修复方式；对 CHECKPOINT-2 的更正。
- `B0-V1-RESULTS.md` 的要点：解出率、方差、改测试文件的情况。
- pilot 校准表：多少道题可用，哪些不可用，原因是什么。
- 记忆接入的测试结果和第 8 步的对照表。
- 本轮花费明细。
- 对 A5-lite 规模的建议：题数、变体、重复次数、预计花费。依据是第 5 步的方差。

然后停下，等审计。

## 3. 与 coding-agent 的交接文件

两边都不修改对方的仓库，只读取对方的交接文件。

**harness → agent：`D:\crq\src\coding-harness\docs\sprint\memory-source-runs.json`**（第 5 步产出，需要提交）

```json
{
  "schema": "sprint3.memory-source-runs.v1",
  "profile_tag": "b0-v1",
  "harness_commit": "<git sha>",
  "label_origin": "source_task_swebench_tests",
  "runs": [
    {
      "source_id": "django__django-10914",
      "repeat": 1,
      "run_dir": "D:/crq/src/coding-harness/runs/sprint3-b0/django__django-10914/r1",
      "layout": "sprint",
      "solved": true,
      "grader_status": "pass",
      "f2p_passed": 1, "f2p_total": 1, "p2p_passed": 0, "p2p_total": 0
    }
  ]
}
```

- `layout: "sprint"` 表示 `events.jsonl` 和 `session/artifacts/` 直接位于 `run_dir` 下，`candidate-delta.json` 的 `changed` 值是 base64 字符串。
- 只包含源题 id、计数和标签，不包含 F2P / P2P 的具体列表、gold patch 或 test patch。
- 14 道 dev 题都要列出，每题 3 条记录。

**agent → harness：`D:\crq\src\coding-agent\benchmarks\a5\memory-cards-v4.jsonl` 和 `memory-cards-v4.manifest.json`**

harness 在第 7、8 步读取。manifest 的主要字段：`cards_sha256`、`status`（`interim` 或 `final`）、`coding_agent_commit`、`sources`（15 道源题及其状态）、`build_inputs.memory_source_runs_sha256`。harness 在每次运行的 summary 里记录 `cards_sha256`。

记忆源一共 15 道：本轮 dev 集的 14 道，加上 pytest-5221（没有新环境运行，沿用旧轨迹）。

## 4. 本轮不做的事

- thinking 对照，以及 reasoning 回传的实现。
- 在 pilot 题上跑任何模型，包括 B0。
- 为了提高 dev 解出率而修改 `b0-v1` 冻结后的 prompt 或工具。
- 批量扩充 sphinx 记忆源（只做方案和 1 道题的试跑）。
