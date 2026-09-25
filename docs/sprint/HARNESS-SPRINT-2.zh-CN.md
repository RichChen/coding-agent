# coding-harness 第二轮计划书：环境与打分链路

日期：2026-09-25。执行者：挂在 `D:\crq\src\coding-harness` 的 Cursor agent。
前置：第一轮 `HARNESS-CAPABILITY-SPRINT.zh-CN.md` 和 `CHECKPOINT-1.md`。第一轮的工作方式和硬约束（第 1 节 6 条）继续有效，除非本文另有说明。
配套：`D:\crq\src\coding-agent\docs\sprint\AGENT-MEMORY-2.zh-CN.md`。

## 0. 审计结论：第一轮真正卡在哪

第一轮的工具改造是有效的：3 道题的模型都用上了 offset 读取和 `search_code`，并且都在第 17–28 次调用左右开始改代码。但 CHECKPOINT-1 里"5221、5227 没改代码"的结论**不对**。审计时逐条查了 `runs/step2-b0c/*/events.jsonl`：

- 5221 调了 `search_replace` 修改 `src/_pytest/python.py`，5227 修改了 `src/_pytest/logging.py` 的 `DEFAULT_LOG_FORMAT`。两题都还额外写了 `changelog/*.rst`。
- `A5ImageBackend.export_delta` 调用 typed-tree 导出时，`allowed_paths` 用的是 **gold patch 的文件列表**（`run_swe_task.py` 里的 `editable = binding["gold_patch_paths"]`）。只要改动碰到列表外的文件（比如 changelog），就会抛出 `candidate changed unassigned paths`。异常被 `close()` 吞进 `snapshot_error`，`candidate_delta` 保持为 `None`，结果 grader 评的是**原始代码**，summary 也看不出异常。用 gold 文件列表当白名单，本身也不符合 SWE-bench 的做法（应当应用模型的完整补丁）。

其余问题：

1. **agent 跑在 transport 镜像里，没有依赖**（receipt 里的 `transport_image_digest`）。grader 跑在已经装好依赖的 baseline 镜像里（`baseline_image_digest`）。三题的模型分别花了 5–13 次调用，在断网环境下 `pip install`、`find / -name six.py`、手写 stub。5103 就是在不能跑测试的情况下把 import 改坏的。
2. **grader 走的是一条没校准过的新路径**。`RepositoryGrader` 把整棵树从宿主机上传进容器，会撞上 `src/execution/docker.py` 的 `MAX_FILES=2048` 和 `TRANSFER_LIMIT=8MB`，而且未修改的代码都复现不了基线（5103 的 P2P 只有 20/64）。之前 19 道 pilot 题校准通过的路径是 `scripts/preflight_a5_repo_baseline.py` 里的 `run_pytest`：在 baseline 镜像里从预装好的 `/opt/repo` 复制到 `/workspace` 再跑，不上传源码树。具体用法见 `scripts/calibrate_a5_image_grader.py`，证据在 `docs/upgrade/evidence/A5-pilot-grader-readiness-20260923-07`。
3. **summary 统计有 bug**：
   - `tool_calls` 恒为 0，因为统计的是 payload 里的 `tool_calls`，实际事件类型是 `tool.intent`；
   - `first_edit_step` 填的是事件序号 `seq`，不是模型调用轮次；
   - `stop_reason` 常为 `unknown`。
4. **`.gitignore` 第 31 行的 `!docs/upgrade/evidence/**/*.json`** 把 11 个 `private-spec.json` 放了回来。它们目前未跟踪，执行 `git add -A` 就会被提交。

本轮目标：**让 agent 能在装好依赖的环境里跑测试，改动能完整收集，grader 在镜像里用校准过的方式打分**，然后在扩大后的 dev 集上重跑 B0。

## 1. 本轮规则补充

- 第一轮累计花费 1.798 CNY。**本轮真实模型花费上限 15 CNY**，单次运行上限：thinking 关闭时 1 CNY，开启时 1.5 CNY。第 0 步到第 4 步不花模型钱。
- 继续往 `docs/sprint/PROGRESS.md` 追加记录，标题用"第二轮 第 N 步"。开工前打 tag `sprint2-start`。
- 20 道 pilot 题的 hold-out 不变。
- 旧的 `A5ImageBackend` 和 `RepositoryGrader` 不删除，本轮新增实现，`run_swe_task.py` 改为调用新实现。

## 2. 分步计划

### 第 0 步：先堵漏洞（不花钱）

1. 修 `.gitignore`：在 `!docs/upgrade/evidence/**/*.json` **之后**加一条 `docs/upgrade/evidence/**/private*`。用 `git check-ignore -v` 验证 `docs/upgrade/evidence/H3/final/private-spec.json` 已被忽略，`git status` 里不再出现这 11 个文件。
2. 修 summary 统计：
   - `tool_calls` 按 `tool.intent` 事件计数；
   - `first_edit_step` 改成第一次编辑类 `tool.intent` 之前已发生的 `model.started` 次数（从 1 开始）；
   - `stop_reason` 从 `run.finished` 的 payload 或 result 的 `failure_reason` / `stop_reason` 取；取不到就写 `unknown` 并附上原始字段。
3. 在 summary 里新增 `snapshot_error` 字段，以及一条硬检查：**事件流里出现过编辑类工具调用、但收集到的改动为空，就把 status 设为 `delta_lost` 并在 stdout 醒目打印**，不能再静默当成"没改"。
4. 补单元测试，并提交。

### 第 1 步：agent 运行环境改成 baseline 镜像

新增 `src/execution/baseline_image_backend.py`，类名建议 `BaselineImageBackend(DockerExecutionBackend)`：

- `start()`：`super().start({})` 之后，在容器里执行 `cp -a /opt/repo/. /workspace/`，参照 `preflight_a5_repo_baseline.py` 第 249 行附近的做法。必须确认复制后 `/workspace` 里可以正常 `import` 并运行该仓库的测试（editable 安装的路径指向 `/workspace`）。
- `export_delta()`：在容器里运行一段 Python 脚本（通过 `exec -i` 用 stdin 传入），对比 `/workspace` 和 `/opt/repo`，输出 `changed`（含内容的 base64）和 `deleted`。忽略 `__pycache__`、`*.pyc`、`.pytest_cache`、`*.egg-info`，以及运行时生成的 `.coverage`、`/tmp` 等。**收集全部改动，不用 gold 白名单**。设置上限（比如 200 个文件、4MB），超出时报 `delta_too_large` 错误，不能静默丢弃。
- `close(snapshot=True)`：沿用 `A5ImageBackend` 的约定，先导出 delta，再关闭。导出失败时的错误写进 `snapshot_error`，并由 runner 写进 summary。
- 资源、断网、只读挂载等安全设置和 `A5ImageBackend` 保持一致。

`run_swe_task.py` 改用这个 backend，镜像用 receipt 里的 `baseline_image_digest`。任务 prompt（`public_issue()`）里补一段如实的环境说明："依赖已预装，没有网络，不要 pip install；在仓库根目录用 `python -m pytest <测试路径>` 跑测试"（django 写 `python tests/runtests.py <模块>`）。**不要**加"不要写 changelog"这类针对评分的提示。

零模型验证：用 mock LLM 在容器里执行一次 `search_replace`，再额外写一个 changelog 文件，确认两处改动都出现在 delta 里；再对 django 题做同样的验证。

### 第 2 步：镜像内 grader

新增 `src/eval/image_grader.py`，参照 `run_pytest`、`calibrate_a5_image_grader.py` 以及 `classify_receipt` 的判定逻辑：

1. 用 baseline 镜像起一个新容器，从 `/opt/repo` 复制到 `/workspace`。
2. 写入 delta 里的全部改动，然后**用 test patch 覆盖测试文件**（和 SWE-bench 一样，test patch 优先）。summary 里记下模型动过哪些测试文件、哪些配置文件（`conftest.py`、`setup.cfg` 等），只记录，不拒绝。
3. 只运行 F2P + P2P 的 nodeid。pytest 系用现有 observer；django 用 `scripts/a5_django_observer.py`。
4. 结果判定沿用"按收据逐条认定，不看退出码或打印的计数"的原则：输出每条 nodeid 的结果，F2P 通过数和总数、P2P 通过数和总数；`solved` 定义为 F2P 全部通过且 P2P 没有新增失败。
5. 不再上传整棵树，所以不受 2048 个文件和 8MB 的限制。

### 第 3 步：dev 题校准，扩大 dev 集（不花钱）

1. **候选**：`docs/upgrade/evidence/A5-harness-preflight-57-remaining16-baseline/tasks/` 和 `A5-harness-preflight-62-history-baseline-retry/tasks/` 下所有有 `baseline_image_digest` 的题，排除 20 道 pilot 题。django 的题现在也可以用了。
2. **每题跑两次校准**：
   - 空改动：F2P 必须失败，P2P 应当通过；
   - gold patch：F2P 和 P2P 都应当通过。gold patch 从 receipt 的 `private_source_binding` 指向的私有行里读取，只在宿主机的 grader 侧使用。
3. 在 gold 下也不通过的 P2P 视为环境问题，从这道题的 P2P 集合里去掉，并逐条记在 `configs/sprint/dev-tasks.yaml` 里，比如 `p2p_excluded: [...]`，附上原因。F2P 在 gold 下也不通过的题直接不收。
4. **目标**：选出 10–12 道校准通过的题，覆盖 django、sympy、scikit-learn、pytest，每个仓库至少 2 道。更新 `dev-tasks.yaml`，把校准结果（两次运行各自的通过数）写进每道题的条目。
5. **白拿一个验证**：把 5227 事件流里模型的编辑重放出来（按 `tool.intent` 的参数，在 base 树上依次执行 `search_replace` / `write_file`），交给新 grader 打分，结果记进 PROGRESS。这一步用来验证新 grader，同时回答"5227 当时到底修没修对"。5221 也照此处理。

### 第 4 步：重新验证 11 条记忆源（不花钱）

用新 grader 对 11 条记忆源的 `candidate-delta.json` 重新打分。记忆源目录见 `docs/upgrade/evidence/A5-real240-77-harness-preflight/memory-snapshot.jsonl` 的 `source_dir`。输出到原来的 `docs/sprint/memory-source-verification.json`，格式不变：`source_id`、`status`（`pass` / `partial` / `fail` / `grader_unavailable`）、`f2p_passed`、`f2p_total`、`p2p_passed`、`p2p_total`、`reason`。可以增加一个可选字段 `calibrated: true/false`。gold 校准不通过的源题记为 `grader_unavailable`，并写明原因。提交后在 PROGRESS 里写一句，由用户告知 agent 侧。

### 第 5 步：dev 集上重跑 B0（花钱，约 6–8 CNY）

- profile 沿用 `configs/sprint/b0.yaml`（40 次调用、60 步、96k、`thinking: disabled`），只改 backend 和 grader。
- 每道校准通过的 dev 题跑 1 次。每题记录：是否解出、F2P / P2P 结果、首次改代码的轮次、调用次数、工具调用次数、花在环境问题上的调用数（比如 pip 或 find，可以粗略按命令关键词统计）、费用、停止原因。
- **中途检查**：前 3 题跑完先看一眼。如果仍然出现 `delta_lost`，或者模型仍在反复装依赖，就停下来修，不要继续花钱。

### 第 6 步：thinking 对照（花钱，约 4–6 CNY）

从 dev 集里挑 4 道题（最好包括 B0 解出和没解出的），在 `thinking: enabled` 下各跑 1 次。对比解题率、调用次数和单题费用。结果写进 PROGRESS，默认值不做变更，由用户决定。

## 3. 审计节点

写 `docs/sprint/CHECKPOINT-2.md`，一页以内：

- `sprint2-start..HEAD` 的提交列表；
- 校准表：每道候选题的空改动和 gold 结果、被排除的 P2P、是否入选；
- 5227 / 5221 重放的打分结果；
- 新的 `memory-source-verification.json` 摘要：几条 pass、几条 partial 或 fail；
- B0 结果表和 thinking 对照表；
- 累计花费；
- 卡点和下一步建议。

然后停下，等审计。

## 4. 本轮不做的事

- 不跑 20 道 pilot 题，不跑 B1–B3。
- 不切换到 agent 侧的 `MemoryCardPlugin`（留到下一轮）。
- 不改 coding-agent 仓库。
- 不再往 `docs/upgrade/evidence` 写新目录，运行产物放在 `runs/`。
