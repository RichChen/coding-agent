# 能力冲刺进度

## 第 0 步：版本控制和清理

日期：2026-09-24。花费：0 CNY。

- `.gitignore` 忽略 `.tmp-*/`、`.a5-test-basetemp/`、`.pytest-tmp/`、`runs/`、`traces/`，以及 evidence 里的 `staging/`、`workspace/`、`original/`、`known-good/`、`baseline/`、`build/`、`full-repo/`、`private*` 和大于等于 200KB 的 json。磁盘上的文件没有删除。`git check-ignore` 抽查：临时目录、`runs/`、`staging/`、`build/` 下的副本被忽略；小的 `*.md` / `*.json` 仍可跟踪。
- 测试基线：`python -m pytest -q` → **433 passed, 22 skipped, 0 failed**（62.87s）。失败项无，跳过的 22 个留到后续按需看。
- 9 月以来的改动已按模块提交（模型网关、工具与执行、会话恢复、上下文、agent loop、评测、A5 脚本、文档）。提交前抽查：配置里的 api key 是环境变量占位，没有大于 5MB 的暂存文件。误进索引的整仓副本和 `private*` 已用 `git rm --cached` 移出跟踪。
- `AGENTS.md` / `CLAUDE.md` 的参考路径改为 `D:\crq\src\learn-claude-code-main`。
- tag：`pre-capability-sprint`（打在本步收尾提交上）。

下一步：第 1 步，通用单题运行器和 dev 集。

## 第 1 步：通用单题运行器和 dev 集

日期：2026-09-24。花费：0 CNY（mock，没有真实模型调用）。

- 新增 `scripts/run_swe_task.py`。一条命令可以在 dev 清单里的任意题上跑 B0：`python scripts/run_swe_task.py --task <id> --profile configs/sprint/b0.yaml`。预算只走 CNY ledger，单次上限 1 CNY；没有再设 `max_cost_usd`。
- dev 集 9 题写在 `configs/sprint/dev-tasks.yaml`：pytest 5103/5221/5227，sympy 11400/11870/12171，scikit-learn 10297/10949/11281。20 个 pilot 目标已排除。Django 三道记忆源树超过 grader 的 2048 文件上限，没有放进 dev 集。
- `RepositoryGrader.execute` 增加 `selectors`，按 FAIL_TO_PASS + PASS_TO_PASS 的 nodeid 跑测试，测试补丁仍只在 grader 侧 overlay。
- mock 端到端（`pytest-dev__pytest-5103`，Docker grader）：未改代码，`solved=false`，grader `partial`，F2P 0/1，P2P 20/64，模型调用 1，费用 0。产物在 `runs/step1-mock3/`（已忽略）。
- 11 条记忆源历史 delta 的打分在 `docs/sprint/memory-source-verification.json`。只有 `pytest-dev__pytest-5103` 得到 `partial`（F2P 0/1，P2P 20/64）。Django 3 条因文件数上限、sympy/sklearn 6 条因 8MB 传输上限，记为 `grader_unavailable`。`pytest-dev__pytest-5221` 的 grader 没有给出 pass/partial/fail。

下一步：第 2 步，改 read_file、搜索和 masking，再在 dev 集上跑 B0。

## 第 2 步：B0 能力改造

日期：2026-09-24。本步花费：1.798 CNY。累计：1.798 CNY。

每项都有零模型测试，并单独提交：

- `read_file`（宿主机和容器）支持 1 起始的 `offset` 和 `limit`，输出带行号；截断时提示 `[showing lines A-B of N; call read_file with offset=B+1 to continue]`。
- 新增只读 `search_code`，输出 `path:line: text`。`docker_linux` 允许列表已加入。容器内优先 `rg`，否则 `grep -R`。
- masking 不再写成 `[Previous: used 工具名]`。旧结果保留路径、offset 或命令和退出码。`keep_recent` 仍由 profile 的 `keep_recent_tool_results` 控制，dev profile 为 4。
- `prompts/swe_b0.md` 经 `system_prompt_path` 加载。每轮上下文末尾注入 `remaining model calls: N/M`。`run_command` 超时在 dev profile 里已是 120 秒。
- 嵌套配置 `configs/sprint/b0.yaml` 原先找不到仓库 `.env`，真实调用时 Bearer 为空。已改为从配置文件向上查找 `.env`。

对照跑的是 pytest dev 题，不是 20 个 pilot。密钥修好之前有一次空 Bearer 的 pytest-5103（`runs/step2-b0/`）：没有改文件，模型调用 3，费用 0.207，停止原因 `model_parse_error`，grader `partial`。有效对照在 `runs/step2-b0b/` 和 `runs/step2-b0c/`。

| 题 | solved | 改动文件 | 模型调用 | 费用 | 停止原因 | grader |
| --- | --- | --- | --- | --- | --- | --- |
| pytest-5103 | 否 | `src/_pytest/assertion/rewrite.py` | 40 | 0.715 | budget_exhausted | invalid_env，改坏了 import，没有 receipt |
| pytest-5221 | 否 | 无 | 40 | 0.551 | unknown | invalid_env，nodeid 对不上 |
| pytest-5227 | 否 | 无 | 27 | 0.325 | unknown | invalid_env，测试文件路径找不到 |

和改之前相比：pytest-7220 那种全程 0 次改文件，在 5103 上已经出现一次代码改动。另外两题的 delta 仍是空的。三题都没有解出。`summary.json` 里的 `tool_calls` 记成了 0，和会话里大量工具产物不符，这个计数不能当结论。

没有再跑 sympy / sklearn，也没有做 thinking 对照。继续跑会再花钱，而 grader 现在给不出 pass/partial/fail，解出数不会增加。

下一步：停在审计节点。见 `docs/sprint/CHECKPOINT-1.md`。

## 第二轮 第 0 步：堵住统计和忽略漏洞

日期：2026-09-25。花费：0 CNY。tag：`sprint2-start`（打在本轮改动之前）。

审计结论已核对：5221、5227 改过代码，但 `export_delta` 用 gold 文件白名单，changelog 一碰就把整份 delta 丢掉了。本步还没改那条导出路径。

- `.gitignore` 在放行 `*.json` 之后增加 `docs/upgrade/evidence/**/private*`。`git check-ignore -v` 确认 `H3/final/private-spec.json` 被忽略，`git status` 不再列出这批 private-spec。
- summary 按 `tool.intent` 计工具调用；`first_edit_step` 是第一次编辑前的 `model.started` 次数；`stop_reason` 取 `run.finished`，取不到就写 `unknown` 并附上原始字段。
- summary 增加 `snapshot_error`。事件里有编辑、收集到的改动为空时，status 设为 `delta_lost` 并在 stdout 打印 `DELTA_LOST`。
- `tests/test_run_swe_task.py` 3 项通过。

下一步：第 1 步，agent 改跑 baseline 镜像，delta 收集全部改动。

## 第二轮 第 1 步：baseline 镜像和完整 delta

日期：2026-09-25。花费：0 CNY。

- 新增 `BaselineImageBackend`。`start()` 把 `/opt/repo` 复制到 `/workspace`，并把生成的 `.so` 链回镜像。`export_delta()` 对比这两棵树，收集全部改动，不用 gold 白名单。超过 200 个文件或 4MB 报 `delta_too_large`。`close(snapshot=True)` 失败时写入 `snapshot_error`。
- `run_swe_task.py` 改用这个 backend 和 receipt 的 `baseline_image_digest`。prompt 说明依赖已预装、没有网络、不要 pip install，并给出 pytest 或 django 的测试命令。
- 零模型验证：pytest-5103 的 `import pytest` 指向 `/workspace/src/pytest.py`；django-10914 的 `import django` 指向 `/workspace/django/__init__.py`。两题都做了 `search_replace` 再写 `changelog/sprint2-check.rst`，两处都出现在 delta 里。

下一步：第 2 步，镜像内 grader。

## 第二轮 第 2 步：镜像内 grader

日期：2026-09-25。花费：0 CNY。

- 新增 `src/eval/image_grader.py`。在 baseline 镜像里从 `/opt/repo` 复制仓库，写入模型 delta，再用 test patch 覆盖测试文件。只跑 F2P 和 P2P 的 nodeid。判定看收据里每条 nodeid，不看退出码。`solved` 是 F2P 全过且 P2P 没有失败。summary 会记下模型动过的测试文件和配置文件。
- `run_swe_task.py` 的打分改走这条路径，不再把整棵树上传进容器。
- 单元测试 `tests/test_image_grader.py` 和 `tests/test_run_swe_task.py` 共 6 项通过。

下一步：第 3 步，校准并扩大 dev 集。

## 第二轮 第 3 步：校准并扩大 dev 集

日期：2026-09-25。花费：0 CNY。

20 道非 pilot 候选都做了空改动和 gold 两次打分。入选 12 道，写进 `configs/sprint/dev-tasks.yaml`。sympy 的裸测试名补上了测试文件前缀。`PASS_TO_PASS` 里像 `[100%]` 这种碎片被丢掉。gold 下仍失败的 P2P 记在 `p2p_excluded`。

入选：django 10914、10924、11039；pytest 5103、5227；sympy 11400、11870、11897、12171；scikit-learn 10297、10949、11281。空改动时 F2P 都是 0，gold 时 F2P 和保留的 P2P 都通过。

未入选：django 11001、11019 的空改动已经通过了部分 F2P。pytest 5221 的 gold 没有通过 F2P。pytest 5413、5495 没有写出收据。sympy 12236 的 gold 没有通过。

重放第一轮编辑：5227 改了 `src/_pytest/logging.py` 和 changelog，新 grader 判定 **solved**，F2P 3/3，P2P 31/31。5221 改了 `src/_pytest/python.py`、changelog 和测试文件，F2P 0/2，P2P 0/170，没有解出。

下一步：第 4 步，用新 grader 重打 11 条记忆源。

## 第二轮 第 4 步：重打 11 条记忆源

日期：2026-09-25。花费：0 CNY。

`docs/sprint/memory-source-verification.json` 已用镜像 grader 重写。5 条 pass：django 10914、10924、11039，sklearn 10297、11281。5 条 fail：sympy 11400、12171，pytest 5103，sklearn 10949、11040。pytest 5221 因 gold 校准没通过，记为 `grader_unavailable`。请把这个文件转给 agent 侧。

下一步：第 5 步，在 12 道 dev 题上重跑 B0。前 3 题先看 delta_lost 和装依赖。

## 第二轮 第 5 步：dev 集重跑 B0

日期：2026-09-25。本步花费：4.390 CNY。本轮累计：4.390 CNY。

前 3 题是 django 10914、10924、11039，都解出了，没有 `delta_lost`，也没有 `pip install` 或 `find /`。所以继续跑完 12 题。12 题里环境类命令都是 0。

| 题 | 解出 | F2P | P2P | 首次改动 | 调用 | 工具 | 费用 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| django-10914 | 是 | 1/1 | 96/96 | 14 | 32 | 49 | 0.427 |
| django-10924 | 是 | 1/1 | 1/1 | 11 | 19 | 22 | 0.203 |
| django-11039 | 是 | 1/1 | 84/84 | 10 | 14 | 14 | 0.108 |
| pytest-5103 | 否 | 0/1 | 64/64 | 40 | 40 | 56 | 0.780 |
| pytest-5227 | 是 | 3/3 | 31/31 | 14 | 20 | 20 | 0.201 |
| sympy-11400 | 是 | 2/2 | 29/29 | 8 | 40 | 54 | 0.558 |
| sympy-11870 | 否 | 0/1 | 58/58 | 19 | 39 | 42 | 0.571 |
| sympy-11897 | 是 | 1/1 | 95/95 | 15 | 23 | 26 | 0.263 |
| sympy-12171 | 否 | 0/1 | 8/8 | 5 | 24 | 26 | 0.255 |
| sklearn-10297 | 否 | 0/1 | 0/28 | 8 | 13 | 16 | 0.143 |
| sklearn-10949 | 否 | 0/1 | 0/42 | 7 | 40 | 43 | 0.607 |
| sklearn-11281 | 否 | 0/2 | 0/43 | 15 | 23 | 30 | 0.274 |

6 道解出。sympy-11870 是 `delta_lost`：事件里有编辑，导出的 delta 是空的，`snapshot_error` 也是空。三道 sklearn 的 delta 带上了一大批 `.so`，P2P 变成 0。产物在 `runs/sprint2-b0/`。

## 第二轮 第 6 步：thinking 对照没有跑

日期：2026-09-25。花费：0 CNY。

`src/llm/client.py` 只接受 `thinking: disabled`。打开 thinking 会直接报错，因为没有把 reasoning 内容带回下一轮。没有为了对照去改这条链路，也没有花这 4–6 元。默认值保持关闭。

下一步：审计节点，见 `docs/sprint/CHECKPOINT-2.md`。

## 第三轮 第 1 步：sklearn 重打分

日期：2026-09-25。花费：0 CNY。

更正 CHECKPOINT-2 里「`.so` 进了 delta」的说法，也不采用计划书第 0 节「delta 里没有 `.so`」的判断。三份 `candidate-delta.json` 的 `changed` 确实各只有一个 `.py`（`ridge.py`、`validation.py`、`mixture/base.py`），但 `deleted` 里各有约 40 个 `.so`。原因是运行前把镜像里的扩展模块换成了指向 `/opt/repo` 的符号链接，导出时符号链接被跳过，原文件就被记成删除。评分器应用这份删除列表后，`sklearn.__check_build._check_build` 导入失败，收据 `collected_count=0`、`exit_code=4`，用例全部 missing。空 delta 对照可以收集测试并跑过 P2P，所以不是镜像本身坏了。只应用那个 `.py`、不删 `.so` 时，10297 的失败用例能通过。

修复：导出和评分应用都跳过 `*.so`、`*.pyd`、`*.o`、`*.dylib` 和 `build/`，源码文件不跳过。summary 增加 `export_skipped_files`。`ImageGrader` 把 `collection_errors`、`runner_error`、`exit_code` 和 stderr 末尾 4KB 写入宿主机的 grader 结果。

按修好后的规则重打分（不覆盖原来的 `grader-result.json`）：

| 题 | 结果 | F2P | P2P |
| --- | --- | --- | --- |
| sklearn-10297 | 解出 | 1/1 | 28/28 |
| sklearn-10949 | 模型失败 | 0/1 | 42/42 |
| sklearn-11281 | 解出 | 2/2 | 43/43 |

10949 的失败用例是 `test_check_dataframe_warns_on_dtype`，收集阶段没有报错。这三题的 gold 校准重做后都仍然通过（空 delta 的 F2P 为 0，gold 的 F2P 和保留的 P2P 全部通过）。

下一步：第 2 步，查 sympy-11870 为什么在 `step_deadline` 时没有导出。

## 第三轮 第 2 步：终止时也要导出

日期：2026-09-25。花费：0 CNY。

11870 的 `termination_kind` 是 `step_deadline`，`snapshot_error` 为空，磁盘上没有 `candidate-delta.json`。当时 profile 里命令超时和 step 超时都是 120 秒。慢命令触发 step deadline 后，`await_with_control` 取消正在执行的 `docker exec`。`DockerExecutionBackend.execute` 只要 `kind` 非空就调用 `close()`，容器被删掉，`active` 变成 false。外层循环随后只在 `backend.active` 时导出，所以导出没有发生，`snapshot_error` 也留空。容器是这次 `execute` 自己删的。

修复：命令超时不再拆掉容器，也不再结束整次运行；工具结果里写明「命令在 N 秒后超时，输出已截断」，然后继续。运行结束时，容器还在就先导出再清理；容器已经不在，就把 `snapshot_error` 写成 `container_gone_before_snapshot`。新 profile 是 `configs/sprint/b0-v1.yaml`（命令超时仍是 120，step 超时 300，总超时 2400）。`b0.yaml` 没有改。

mock 检查：`sleep 200` 在约 120 秒后返回超时文本，模型调用了 2 次，运行没有以 `step_deadline` 结束。

11870 事件重放改了 `sympy/simplify/fu.py` 和 `sympy/simplify/trigsimp.py`。镜像评分 F2P 0/1，P2P 58/58，没有解出。缺的是导出，不是没改代码。

下一步：第 3 步，修正 `stop_reason`，并让 `verify_memory` 走 `ImageGrader`。

## 第三轮 第 3 步：stop_reason 和记忆源验证

日期：2026-09-25。花费：0 CNY。

`_stop_reason` 先读内存里的 `termination_kind` 和 `failure_reason`。`run.finished` 如果只剩 `artifact_ref`，就到 `session/artifacts/` 把正文读出来。成功结束且没有失败原因时记为 `completed`，不再把 `unknown` 当成真实停止原因。`apply_delta` 同时接受 `{content: ...}` 和裸 base64 字符串。

`verify_memory` 改为 `ImageGrader`，只给 gold 校准通过的记忆源打分。pytest-5221 的 gold F2P 是 0/2，记为 `grader_unavailable`，原因 `gold_fails_calibration`。`docs/sprint/memory-source-verification.json` 已按这次结果更新：5 条 pass（django 10914、10924、11039，sklearn 10297、11281），5 条 fail（sympy 11400、12171，pytest 5103，sklearn 10949、11040）。

下一步：第 4 步，把 sklearn 10508 和 11040 加入 dev 集，mock 跑完 14 题后打 tag `b0-v1`。

## 第三轮 第 4 步：14 题 dev 集和 b0-v1

日期：2026-09-25。花费：0 CNY。

dev 集加入 sklearn-10508 和 sklearn-11040，共 14 题。两题的 gold 校准都已通过。profile 是 `configs/sprint/b0-v1.yaml`，prompt 仍是 `prompts/swe_b0.md`。

14 题 mock（不调用模型，只链接仓库并打分）都正常结束：`stop_reason=completed`，费用 0，没有改动，所以都未解出。sklearn 导出时跳过了 237–238 个编译产物，源码文件还在。

本步提交后打 tag `b0-v1`。此后本轮不再改 B0 的 prompt、工具集、profile 和 grader 判定逻辑。

下一步：第 5 步，14 题各重复 3 次，预计花费写在开跑之前。

## 第三轮 第 5 步：B0 v1 重复运行

日期：2026-09-25。

预计花费：16 CNY。依据是第二轮 12 题单次合计 4.390 CNY，平均约 0.37 CNY，42 次约 15.5 CNY，取 16。单次账本上限 1 CNY。

实际花费：16.173 CNY。42 次都低于 1 CNY。本轮累计 16.173 CNY。

解出 32/42。10 道题 3/3，2 道题 0/3（sympy-11870、sklearn-10949），2 道题混合（pytest-5103 1/3，sympy-12171 1/3）。表在 `docs/sprint/B0-V1-RESULTS.md`。抽查 django-10914 r1 和 sklearn-10297 r1，改的是源码和文档，不是测试。42 次的 `test_files_touched` 都是空的。交接文件是 `docs/sprint/memory-source-runs.json`。

下一步：第 6 步，20 道 pilot 题零模型校准。

## 第三轮 第 6 步：pilot 零模型校准

日期：2026-09-25。花费：0 CNY。没有在 pilot 题上调用模型。`HOLDOUT` 没有改。

`scripts/calibrate_pilot_image_grader.py` 对 20 道 pilot 做了空改动和 gold 打分。镜像来自 `A5-pilot-grader-readiness-20260923-07`，源码包来自 `A5-harness-preflight-12-host-sources`。没有重建镜像。私有 patch 只通过 source-row 路径读取，没有写进 yaml。`runs/` 下的临时树被 gitignore。coding-agent 的 private 文件在本仓库之外。

没有一道被接受为「空改动失败、gold 通过」：

| 结果 | 题 |
| --- | --- |
| 镜像里没有 `/opt/repo`，无法用当前 grader | pytest 9359、8365、7220 |
| 已知合同阻塞，没有打分 | django-13265 |
| 空改动已经通过 F2P | sklearn 25747、25500；sphinx 8595、8721；sympy 20442、20154、24152；django 13448、13590 |
| gold 没有通过 | pytest 7432；sklearn 25570、25638；sphinx 8713、10451；sympy 18532；django 15781 |

清单在 `configs/sprint/pilot-tasks.yaml`。

下一步：第 7 步，接入记忆卡片，并用 mock 跑通一条链路。

## 第三轮 第 7 步：记忆卡片接入

日期：2026-09-25。花费：0 CNY。

`register_memory_cards` 按 coding-agent 当前构造函数加载 `MemoryCardPlugin`。`run_swe_task.py` 接受 `--variant B0|B1|B2|B3` 和 `--cards`。传给插件之前会去掉 `source_id` 等于当前题的卡片。summary 的 `memory` 字段记下 variant、卡片 sha256、被过滤的 id、注入的 id 和字节数、B3 拒绝项。

卡片文件用的是 `benchmarks/a5/memory-cards-v3.jsonl`。v4 manifest 的 `status` 仍是 `interim`，`build_inputs.memory_source_runs_sha256` 是空的，所以没有换成 v4。

零模型测试：B0 不产生候选；B2 在 django-10914 上过滤掉它自己的卡，注入的是 10924（877 字节）和 11039（1362 字节），都低于 4096。mock 全链路一次，费用 0，`context.prepared` 里能看到这两张卡，看不到 10914。

下一步：第 8 步要等 v4 manifest 变成 final。先写第 9 步的扩充说明，再复查一次。

## 第三轮 第 8 步：跳过

日期：2026-09-25。花费：0 CNY。

`memory-cards-v4.manifest.json` 的 `status` 是 `interim`，`build_inputs.memory_source_runs_sha256` 是 `null`。写完第 9 步的说明后再看了一次，仍是这样。没有跑 B2/B3，也没有自造卡片。

## 第三轮 第 9 步：sphinx 扩充规则

日期：2026-09-25。花费：0 CNY。

规则写在 `docs/sprint/MEMORY-SOURCE-EXPANSION.md`。本地没有 sphinx baseline 镜像，本轮没有做那一道试跑。

## 第三轮 第 10 步：审计节点

`docs/sprint/CHECKPOINT-3.md` 已写。本轮模型花费 16.173 CNY。停在这里等审计。

CHECKPOINT-3 把 gold 没有通过的 pilot 题写成 6 道。PROGRESS 第 6 步的表是 7 道，以表为准。

## 第四轮 R4-1：干净镜像

日期：2026-09-25。花费：0 CNY。tag：`sprint4-start`。

只读核对：`django-11039` 的 `staging/baseline.tar.gz` 含 `test_sqlmigrate_for_non_transactional_databases`，同路径的 original 不含。旧 Dockerfile 把这份归档解到 `/opt/repo`。

clean image 从 original `source.tar.gz` 构建，不放入 test patch 或 gold patch。最终文件系统里没有这份构建用的归档。`/opt/native-artifacts.json` 列出构建生成的 `.so`；没有这份清单、也没有旧归档时，链接会报错。14 道 dev 题的 source-only hash 都和 original 一致。全文件系统扫描用的是 original 归档里不存在的新增行，14 道都没有命中。sklearn 五题各有 40 个 native artifact。

## 第四轮 R4-2：答案隔离

日期：2026-09-25。花费：0 CNY。

`b0-v2` 只接受 `answer_isolation_pass` 为真的 clean image。开跑前再对 `/opt/repo` 做 source-only 比对，不一致就停，不调用模型。django-11039、sympy-11400、sklearn-10297 的空 delta 导出都是空的。

## 第四轮 R4-3：零模型校准

日期：2026-09-25。花费：0 CNY。

14 道 dev 题都接受：空改动 F2P 没有通过，gold F2P 全部通过，两边的 nodeid 结果不同。sklearn 在复制 `/opt/repo` 之后可以 `import sklearn`。结果在 `docs/sprint/clean-calibration/`。

## 第四轮 R4-4：B0 v2 重复

日期：2026-09-25。

预计花费：16 CNY。依据是第三轮 42 次实际 16.173 CNY。单次上限 1 CNY。本轮累计上限 20 CNY，开跑前若已用到 19 CNY 就停。

实际花费：14.712 CNY。42 次都低于 1 CNY。隔离检查 42 次都通过。解出 17/42。表在 `docs/sprint/B0-V2-RESULTS.md`。sklearn-11281 r2 的 `stop_reason` 是 `StoreError`，记录到的模型调用是 0，但账本记了 0.668 CNY。没有因为隔离失败停波。

## 第四轮 R4-5：交接

日期：2026-09-25。花费：0 CNY。

新交接文件 `docs/sprint/memory-source-runs.json`，`profile_tag` 是 `b0-v2`。sha256 `89c33557b611fdb0578c050b54952a7c8a5b062e115db097f619b456ae84d073`。20 道 pilot 没有重建 clean image。审计节点是 `docs/sprint/CHECKPOINT-4.md`。

## 第五轮 第 0 步：强制干净镜像，并查清 StoreError

日期：2026-09-26。tag：`sprint5-start`。

真实运行不再看 profile 名。没有 clean image 就拒绝。`--legacy-image` 只能和 `--mock` 一起用。

sklearn-11281 r2 的 `events.sqlite3` 还在，最后一条是第 40 次调用之后的 `state.saved`。工件目录 155 个文件、14857689 字节，16MB 配额还剩大约 1.9MB，下一次保存触发了 `artifact disk quota exceeded`。不是 ACL，也不是宿主机磁盘满。旧目录保留为 `r2-storeerror`。会话工件上限改为 64MB。`StoreError` 的 summary 现在记 `infra_error`，模型调用数和花费从账本读取，汇总时不进分母。

未跟踪的 `pelican-bicycle.html` 已删除。交接 sha256 的算法写在 `docs/sprint/HANDOFF-CONVENTIONS.md`。

重跑已经完成。新的 r2 解出，33 次调用，`stop_reason` 是 `completed`，隔离通过，花费 0.478 CNY。11281 从 1/3 变成 2/3。42 次合计 18/42，14.522 CNY。旧证据留在 `runs/sprint4-b0-v2/scikit-learn__scikit-learn-11281/r2-storeerror`。这 0.478 CNY 算进第五轮，不另加在 14.522 上。

## 第五轮 第 1 步：Docker 磁盘在 C 盘

日期：2026-09-26。花费：0 CNY。

Docker 数据盘是 `C:\Users\Administrator\AppData\Local\Docker\wsl\disk\docker_data.vhdx`。C 盘空闲约 68GB，不到 150GB。没有迁移，也没有删除镜像。请把 Docker Desktop 的 Disk image location 手动迁到 E 盘（E 盘空闲约 815GB）。等待期间继续第 2 步和第 4 步。第 5 步的 60 个镜像在磁盘迁走之前不开工。

## 第五轮 第 2 步：官方镜像试用

日期：2026-09-26。花费：0 CNY。

试用题是 django-10914、sympy-11400、scikit-learn-10297。镜像名是 `swebench/sweb.eval.x86_64.<id 里的 __ 换成 _1776_>:latest`。`docker manifest inspect` 超时，`docker pull` 可以完成。django 大约 385 秒，sklearn 大约 260 秒。Hub 慢，但没有被完全挡住。

仓库在 `/testbed`，Python 在 `/opt/miniconda3/envs/testbed/bin/python`。三道题的全文件系统扫描都是 0 命中：django 2 条特征行，sympy 9 条，sklearn 12 条。

零模型校准：django 空改动 F2P 0/1，gold 1/1，通过。sympy 空改动 0/2，gold 仍是 0/2，收据文件没有生成。sklearn 在链接 `.so` 时因没有 native artifact 依据报错，按规则没有跳过。三道没有全部通过，所以题目池不用官方镜像。

决定：用 `build_clean_baseline.py` 自建。版本安装改为读取 SWE-bench v4.0.4 的 `MAP_REPO_VERSION_TO_SPECS_PY`（当前安装的 swebench 5.0.2 已经去掉这个文件，缓存放在 `runs/sprint5-specs/python.py`）。`main-targets.yaml` 的 `image_source` 是 `swebench-specs-v4.0.4`。没有拉取其余 57 个官方镜像，也没有删除已经拉下来的 3 个。

## 第五轮 第 3 步：题目池

日期：2026-09-26。花费：0 CNY。

按设计文档第 3 节，从 SWE-bench Verified test split 的 5 个仓库里排除 14 道 dev 题，按 `created_at` 等间隔各取最多 12 道，共 60 道。题目 id 列表 sha256：`d4caaa48c5735b2bf1a302855bbf94a2cdb5ab0397dff152d5d839440a4b22dd`。私有字段在 `runs/sprint5-main-private/`，不提交。选定之后没有因为环境以外的原因换题。`sphinx-doc__sphinx-8721` 被抽进题目池，已从 `HOLDOUT` 里拿掉，其余 pilot 仍然拒绝。

## 第五轮 第 4 步：记忆源 created_at

日期：2026-09-26。花费：0 CNY。

Verified 里对不上 36 条运行。改用 `princeton-nlp/SWE-bench` 的 test split 之后，42 条都有 `repo` 和 `created_at`。交接文件升级为 `sprint5.memory-source-runs.v2`。换行符归一后的 sha256：`984826707e8f69ad9b900134bd244c6056f2d8860f3036a3606bfc60b4bcb450`。11281 重跑刚写完时、还没加这两个字段之前的 sha256 是 `31de0c2a727519786703d454825cbcd95440adc846d22cf868f0c3702a41f9a4`。第四轮检查点里的 `89c33557b611fdb0578c050b54952a7c8a5b062e115db097f619b456ae84d073` 是重跑之前的文件。

## 第五轮 第 5 步：题目池环境

日期：2026-09-26。花费：0 CNY。

2026-09-27 用户把 Docker 数据盘迁到 E 盘之后，60 道都做了镜像和零模型校准。合格 56 道，明细在 `docs/sprint/MAIN-CALIBRATION.md`。环境剔除 4 道，没有换题：django-7530 的 F2P 在空改动下已经通过；sklearn-25232 和 sklearn-25973 的官方 pin `numpy==1.19.2` 没有 Python 3.9 的 wheel，源码也无法用 Cython 3.0.10 编译；sphinx-8721 的 F2P 在空改动下已经通过。

2026-09-28 恢复全文件系统扫描。误报只排除两类：和基础镜像同一路径且 sha256 相同的文件，以及和 pip `RECORD` 中 sha256 相同的文件。有镜像的 58 道全部重扫通过，合格数仍是 56。sklearn-25232 和 25973 没有镜像。每道校准 JSON 的 `nodeids` 记录原始条数、实际条数和丢弃原因。django-7530 重跑后仍是 `empty_f2p_did_not_fail`（空改动和 gold 都是 F2P 1/1、P2P 59/59），没有换题。

## 第五轮 第 6 步：dev 题 B2 冒烟

日期：2026-09-26。开工前估计 14 次大约 4.9 CNY，加上已经花掉的 0.478，合计大约 5.4 CNY。上限 10 CNY，累计到 9 CNY 就停。

v5 的 manifest 是 interim，没有用。用的是 v4 final（`cards_sha256` 前缀 `d31af37b612ae38f`）。v4 没有 `created_at`，由交接文件在 harness 里补上之后再交给插件。14 道题都跑了一次 B2。过滤前都是 14 张。注入字节都低于 4096。当前题和更晚的卡片没有注入。这一步不和 B0 比较解出率。

| 题 | 过滤后 | 实际注入 |
| --- | --- | --- |
| django-10914 | 0 | 无 |
| django-10924 | 1 | django-10914 |
| django-11039 | 2 | django-10924、django-10914 |
| pytest-5103 | 0 | 无 |
| pytest-5227 | 1 | 无（留下的不是 validated_fix） |
| sympy-11400 | 0 | 无 |
| sympy-11870 | 1 | 无 |
| sympy-11897 | 2 | 无 |
| sympy-12171 | 3 | 无 |
| sklearn-10297 | 0 | 无 |
| sklearn-10508 | 1 | sklearn-10297 |
| sklearn-10949 | 2 | sklearn-10297 |
| sklearn-11040 | 3 | sklearn-10297 |
| sklearn-11281 | 4 | sklearn-11040 |

sklearn-11281 的 `context.prepared` 里能看到 `scikit-learn__scikit-learn-11040`。10297 留在时间过滤之后，检索分数低于 1.0，没有注入。sklearn-10508 的 delta 没有收上来，状态是 `delta_lost`。冒烟花费 5.871 CNY。本轮合计 6.349 CNY。

## 第五轮 第 7 步：主实验运行器

日期：2026-09-26。花费：0 CNY。

`scripts/run_a5_main.py` 先跑合格题的 B0 三次，写出交接文件后停下，再跑 B2。并行 3，总上限 150 CNY，单次仍是 1 CNY。题目池 yaml 没有 `receipt`、`public_task` 和 `family`，走查前在 `runs/` 里补上，再调用原来的 `run_task`。

2026-09-28 用 mock 走完 django-16527、sympy-11618、sklearn-14053 的 B0 → 交接 → B2，各 1 次重复，费用 0。交接文件 `docs/sprint/main-b0-runs.json` 的 `scope` 是 `step7-mock`，不是 R6 交接。sklearn-14053 注入了 10297（771 字节）和 11040（871 字节）。django-16527 过滤后剩 3 张卡，插件给出 `no_relevant_memory`。sympy-11618 过滤后剩的 1 张不是 validated_fix。没有调用真实模型。

## 第五轮 第 8 步：停下等审计

日期：2026-09-26。审计节点是 `docs/sprint/CHECKPOINT-5.md`。没有打 `a5-main-freeze`。

第五轮第 5 步已处理 10 道。明细在 `docs/sprint/MAIN-CALIBRATION.md`。

第五轮第 5 步已处理 20 道。明细在 `docs/sprint/MAIN-CALIBRATION.md`。

第五轮第 5 步已处理 30 道。明细在 `docs/sprint/MAIN-CALIBRATION.md`。

第五轮第 5 步已处理 40 道。明细在 `docs/sprint/MAIN-CALIBRATION.md`。

第五轮第 5 步已处理 50 道。明细在 `docs/sprint/MAIN-CALIBRATION.md`。

第五轮第 5 步已处理 60 道。明细在 `docs/sprint/MAIN-CALIBRATION.md`。

## 第五轮补丁：P1–P5

日期：2026-09-28。花费：0 CNY，只用 mock。依据 `docs/sprint/HARNESS-SPRINT-5-PATCH.zh-CN.md`。

P1：step 7 的 mock 输出移到 `runs/a5-main-mock-step7/`，交接文件改名为 `main-b0-runs.step7-mock.json`。`run_a5_main.py` 的 mock 和正式运行分开目录和交接文件，续跑时 summary 必须和当前模式、`b0-v2`、phase 一致，否则退出、不覆盖。

P2：时间过滤读卡片自己的 repo 和 `created_at`，按带时区的时刻比较，和 dev 交接文件交叉核对。B2 拿不到目标日期、卡片缺日期都报错。

P3：django docstring 测试 id 用 `ast` 映射回测试方法，12 道 django 重新校准。F2P 16 → 18 条，P2P 695 → 898 条，13 条有歧义的 P2P 丢弃。没有题被排除，合格仍是 56。R6 运行时改为使用校准的同一份 id，56 道核对一致。

P4：`/opt/repo` 和目标项目包目录下的命中不再适用两条扫描排除。56 份 receipt 离线重判，6 个排除文件都不受影响，结论不变。

P5：删除 `pelican-bicycle.html`。用 v5 final 卡片在 3 道题上跑 mock B2，过滤和注入记录正常。

补记在 `docs/sprint/CHECKPOINT-5.md`。没有打 `a5-main-freeze`。

## 第六轮：冻结与 B0 canary

日期：2026-09-28。花费：0.687 CNY。依据 `docs/sprint/HARNESS-SPRINT-6.zh-CN.md`。

第 0 步：infra_error 槽位移到 `r<k>.infra<n>` 后重跑，每个槽位最多 2 次；`PARALLEL` 为 4；summary 记录模型名和 base_url host。冻结记录在 `docs/sprint/A5-MAIN-FREEZE.md`，harness tag `a5-main-freeze` → `02c8671`。

第 1 步：canary 用 django-13964、sklearn-13142、sphinx-8593。前两道检查全部通过（sklearn 解出）。sphinx-8593 在调用模型之前 answer isolation 就失败了：构建镜像时排除了 `pre_install` 用 `sed` 改写的 `setup.py`、`tox.ini`，运行时的比对没有排除。同样的问题会影响 11 道 sphinx 和 pytest-8399。第 2 步没有开始。

记录在 `docs/sprint/CHECKPOINT-6.md` 的 6a 部分，停下等审计。

## 第六轮修订 1：F1

日期：2026-09-28。花费：0 CNY。依据 `docs/sprint/HARNESS-SPRINT-6A-FIX.zh-CN.md`。

被 `pre_install` sed 改写的文件改为按重放后的期望 sha 比对，构建和运行使用同一份 override（提交 `a3b4450`）。12 道受影响的题里 11 道离线核对通过。sphinx-9258 的 `setup.py` 不一致：它的规格里有两条以 `grep -q` 开头的守卫 sed 命令，现有解析规则识别不到。把这两条也重放后，结果和镜像一致。按 F1 第 5 项停下，F2–F6 没有做。记录在 `docs/sprint/CHECKPOINT-6.md`。

审计批准 guarded_sed 规则后：F1 12/12 通过（`53c072a`），只有 sphinx-9258 的记录改变。F2 预检（`43ee604`）按原口径是 53/56：sphinx 8120、9673、10323 在校准时排除过 1–2 条 P2P，运行时条数少了这几条。扣除排除条数后是 56/56。按规定停下等审计确认口径，F3–F6 没有做。花费 0 CNY。

审计确认口径后：F3 56 道 mock 核对一致（`a3cdc3a`）；F4 移动 sphinx-8593 的失败槽位；F5 调整 infra_error 停止线（`653ebbb`）；F6 冻结修订 1，tag `a5-main-freeze-r1` → `fb26dbd`。sphinx-8593 canary 通过（0.467 CNY）。

全量 B0 新跑 22 次后，django-14434 r2 的 grader 超时，触发停止。排查发现，Python 低于 3.9 的镜像里 agent 的结构化工具全部报错（`Path.is_relative_to`），影响 17 道题、已完成 25 次中的 22 次。另有 2 次快照、1 次 grader 因 Docker 控制通道出错。累计花费 13.682 CNY。记录在 `docs/sprint/CHECKPOINT-6.md`，停下等审计。

6B-FIX：G1–G7 完成（`ef32056`…`2f28232`，tag `a5-main-freeze-r2`）。预检 56/56，工具冒烟 56/56。修订 2 之前的 25 次运行移到 `runs/a5-main-void/r1-tool-py36/`。4 道 canary 通过（2.585 CNY）。全量 B0 在 django-16527 r2 触发 grader missing 停止：候选改动有 IndentationError，测试导入失败；grader 和工具正常。36 次有效运行、0 解出、2 次 infra 已重跑、4 次 Docker 重试、harness_tool_errors 0、花费 24.055 CNY。记录在 `docs/sprint/CHECKPOINT-6.md`，停下等审计。

6C-FIX：审计发现 0/36 的根因是 pool 题的 prompt 里没有 issue 文本，只有 `Public issue for <id>` 占位。H1–H9 完成（`6a21da4`…`1707d23`，tag `a5-main-freeze-r3`）：从 SWE-bench Verified（revision `c104f840…`）补齐 issue，静默回退改为报错，预检检查 prompt 内容。预检 56/56，dev prompt 14/14 逐字节一致。修订 3 之前的 38 个运行目录移到 `runs/a5-main-void/r2-no-issue/`（作废成本 24.055 CNY）。每个 repo 一道 canary，5/5 通过且全部解出。全量 B0 跑完，没有触发停止：115/168 = 68.5% 解出（django 24/33，pytest 29/36，sklearn 26/30，sphinx 20/33，sympy 16/36），2 次 infra 已重跑，72 次 Docker 重试全部成功，harness_tool_errors 0，花费 55.774 CNY。`main-b0-runs.json` 已生成。记录在 `docs/sprint/CHECKPOINT-6.md`，没有开始 B2，停下等审计。

6D 第 A 段：D1–D4 完成，花费 0 CNY，没有调用模型。D1 交接文件 v2（`614ebce`），sha `fe0f47b8…`，旧文件保留为 `main-b0-runs.v1.json`。D2 描述 4 次 delta_lost（`1c6498b`）：3 次是 agent 自己撤回改动，1 次是 `search == replace` 的空编辑。D3 漂移对照臂 `--phase b2 --with-b0-drift`，种子 20260929（`9d1a438`）。D4 冻结修订 4，tag `a5-main-freeze-r4` → `074219c`。全套测试 420 passed。交接文件 v2 已就绪；没有开始 B2，也没有做第 C 段。

6D 第 C 段：v6 卡片审计通过后执行 D5–D8。开跑前补上 B2 故障警报（`068380e`），D5 manifest 核对（`f97284c`），D6 预测注入表（`89ef367`，sha `5d858eb4…`，51/56 道题注入），D7 注入一致性停止条件（`8008223`），冻结修订 4 补记（`5c0c6b5`）。D7 核对代码修正两次：事件类型字段（`399132a`，mock 中发现），以及存成附件的大负载（`a75303a`，导致一次误停，运行结果不变）。B2 加漂移对照臂跑到 B2 115/168、r4 38/56 时，django-13964 B2 r3 触发 grader missing 停止：候选删掉了外键赋值分支，`setUpClass` 报错，37 个 id 都没跑；H6 规则不覆盖执行阶段的错误。实际注入与预测 115/115 一致，全量检查没有晚于目标、目标自身或跨 repo 的卡。本段花费 54.208 CNY（B2 41.947，r4 12.261），`runs/a5-main/` 总额 109.982 CNY。全套测试 435 passed。记录在 `docs/sprint/CHECKPOINT-6.md`，没有计算 B2 与 B0 的差异，停下等审计。

审计新规则 missing_regrade（`d99e1f6`，冻结修订 4 补记 2 `2be58e7`）：grader 报 missing 且 H6 不适用时，同一镜像以空改动重评，无 missing 且与校准一致就记为普通失败。B0 的 168 次没有 missing，不受影响。django-13964 B2 r3 重评一致，记为普通失败，没有重跑。续跑新启动 32 次后，sphinx-7590 B2 r3 触发"grader crashed"停止：候选的 `_parse_udl_suffix` 遇到 `current_char == 'EOF'` 时死循环，测试超时，grader 读不到结果文件，报成 `DockerUnavailable`。零花费诊断显示空改动 10 秒正常、候选重评再次超时。截至停止 B2 139/168、r4 46/56，注入 139/139 一致；本段花费 64.935 CNY，总额 120.709 CNY。全套测试 441 passed。停下等审计。

审计批准 execution_timeout 扩展（`5a7ac96`、`6dadad2`，冻结修订 4 补记 3 `7a9986f`，不打新 tag）：grader 报 reason 且测试执行超时时，同一镜像以空改动重评，一致就记为普通失败，F2P/P2P 全部算失败。已完成运行里只有 sphinx-7590 B2 r3 适用，重评 F2P 0/1、P2P 24/24 与校准一致，记为普通失败，没有重跑；B0 的 168 次没有 grader reason，不受影响。续跑剩下的 39 个槽位全部完成，没有触发停止：B2 168/168、`b0/r4` 56/56，注入 168/168 一致，全量检查三项为 0，新增 1 次 infra（sphinx-9461 B2 r2，已重跑）。第 C 段花费 76.030 CNY（B2 57.790，r4 18.240），总额 131.804 CNY。全套测试 444 passed。记录在 `docs/sprint/CHECKPOINT-6.md`，没有计算 B2 与 B0 的差异，已通知 coding-agent 可以开始分析。

## 第七轮 第 1 步：运行清单

日期：2026-09-29。花费：0 CNY，没有调用模型。依据 `docs/sprint/HARNESS-SPRINT-7-CLOSEOUT.zh-CN.md`。

新增只读脚本 `scripts/sprint7_inventory.py`，从磁盘复算后写 `docs/sprint/A5-MAIN-INVENTORY.md`。6 个输入文件的 sha 和 v6 `cards_sha256` 都与冻结记录一致。有效槽位 B0 r1–r3 168、B2 r1–r3 168、B0 r4 56；infra 退役 2/3/2。作废目录 25 个（13.682 CNY）和 38 个（24.055 CNY）。`runs/a5-main/` 有效实验 131.804 CNY，第 6 轮合计 169.541 CNY；加上 PROGRESS 记录的第 1–5 轮 43.422 CNY，项目模型花费 212.963 CNY。隔离失败 0，harness_tool_errors 0，注入 168/168，全量检查三项 0。

## 第七轮 第 2 步：核对案例数据

日期：2026-09-29。花费：0 CNY。用本仓库 `.venv` 复跑 `.tmp/case_mem.py table` 和 `follow`（gold 只在内存里取 `+++ b/` 路径，输出只有计数和路径）。结果与 `docs/sprint/A5-CASE-DATA.md` 第 1、2 节一致：注入卡片的题 51 道，其中卡片文件与 gold 文件有重合 9 道、没有重合 42 道；平均 d_t 为 −0.074、+0.016，未注入 5 道 −0.200；9 道重合表逐行相同；153 次注入运行里 5 次打开卡片独有文件，0 次最终改在这类文件上。第 3 节 17 道 d_t ≠ 0 的题也一致。文首加了核对行，没有改数据。

## 第七轮 第 3 步：冻结收口

日期：2026-09-29。花费：0 CNY。在 `docs/sprint/A5-MAIN-FREEZE.md` 末尾追加「收口」一节：实验运行结束，不再接受 runner / grader / 镜像 / 校准改动；分析以 coding-agent 的 `A5-MAIN-RESULTS.zh-CN.md` 为准，最终叙述以 `A5-FINAL-REPORT.zh-CN.md` 为准，案例数据以 `A5-CASE-DATA.md` 为准，清单以 `A5-MAIN-INVENTORY.md` 为准。前面的修订正文没有改。没有打新 tag。

## 第七轮 第 4 步：文档入口

日期：2026-09-29。花费：0 CNY。`README.zh-CN.md` 和 `README.md` 在简介句后面加「A5-main」一段（B0 68.5%，没有检出大于 13.1 个百分点的效应），链接项目历程、A5-main 设计、运行清单，以及 agent 仓库的结果报告和最终报告（最终报告由 agent 侧收尾后生成）。旧的 H3/H4/H5/R1/R2 段落没有改。审计提供的 `docs/PROJECT-HISTORY.zh-CN.md` 和收尾计划原样入库。

## 第七轮 第 5 步：测试与停下

日期：2026-09-29。花费：0 CNY。`.venv` 全量测试 620 passed，1 failed，22 skipped。失败的是 `tests/test_summary_wrapper.py::test_one_call_no_summary_private_grading_and_durable_replay`：`src/runtime/loop.py` 自 `dd77ba3`（2026-09-24）起会追加 `remaining model calls` 提示，但测试期望没有更新；在 `03fe586` 和 `a5-main-freeze-r4` 上同样失败，与本轮无关。系统 Python 下仍是 444 passed，199 skipped。没有修，写进 `docs/sprint/CHECKPOINT-7.md` 等审计。已通知 coding-agent：清单和案例数据已就绪，可以写最终报告。

## 第七轮 审计后续

日期：2026-09-30。花费：0 CNY，没有调用模型。

`.venv` 全量测试 621 passed，22 skipped。`test_one_call_no_summary_private_grading_and_durable_replay` 接受 loop 追加的 `remaining model calls: 1/1`。`scripts/audit_summary_pilot.py` 比对导出视图时去掉这条发送时附注。`src/runtime/loop.py` 没有改。`A5-CASE-DATA.md` 改为引用第 1–4 节。最终报告第 7 节就是案例分析，`PROJECT-HISTORY.zh-CN.md` 的指向没有改。两个 README 和冻结记录去掉「最终报告尚未生成」。tag `a5-main-closeout`。

## A6-R 第 1 轮（A6-1）：记录构建与泄漏检查

日期：2026-10-13。花费：0 CNY，没有调用模型，没有启动 provider。依据 `docs/sprint/A6-R-PLAN.zh-CN.md` 第 5 节。

第 1 步（`b9826c9`）：`run_task` 加 `prompt_suffix` 和 `retry`，新增 `build_prompt`。默认参数下 14 道 dev 题的 prompt sha 与改动前相同，56 道主池题与 A5 B0 r1 的 `prompt_sha256` 相同。审计的计划和启动 prompt 原样入库（`40b2be3`）。

第 2 步（`ce0b0ff`）：`scripts/build_a6_attempts.py`。第一次尝试复算 53 次、22 道题，与计划一致。53 份记录 688–8192 字节，中位 2664；diff 截断 1 份，命令块截断 15 份共 18 块，最后消息截断 3 份；11 份没有改非测试源码。真实数据跑两次，55 个输出文件逐字节相同。泄漏检查：第 1 项 34 次（11 份），第 2 项 58 次（10 份），第 3 项 0，第 4 项（只报告）113 次（18 份）。第 1、2 项合计 16 份记录、7 道题。第 1 项命中的测试名在原始测试文件里都已存在；第 2 项有 20 次落在 diff 的上下文或删除行上，17 次是 agent 新增行与隐藏测试行相同。按计划阻断，模板和规则没有改。记录和清单（`handoff_sha256` `a324ab61…`）写在磁盘上，没有提交。

第 3–5 步（runner、preflight、mock）没有开始。全量测试 633 passed，22 skipped。记录在 `docs/sprint/CHECKPOINT-A6-1.md`，停下等审计。

## A6-R 第 1b 轮（A6-1 审计后）：runner、preflight、mock

日期：2026-10-13。花费：0 CNY，没有调用真实模型。依据 `docs/sprint/AUDIT-A6-1.zh-CN.md` 第 4 节。

审计结论是泄漏检查第 1、2 项不阻断，判定口径改为"记录内容只能来自第一次运行的产物和原始源码"。为此新增测试：私有材料不可读或换成垃圾内容时，渲染出的记录逐字节不变；合成数据和真实 53 份都测了（`4bfd6f3`）。只改了测试文件的 2 份记录（django-15973 b0r3、sphinx-9258 b0r2），Files changed 改写为 `none (only test files were changed; see the diff)`，其余 51 份不变，泄漏计数仍是 34/58/0/113，只作描述。记录和清单已提交（`27a7a0a`）：模板 sha `7bed7ba8…`，清单 `handoff_sha256` `bd932529…`。

`scripts/run_a6_retry.py`（`69178cc`）：318 个槽位用种子 20261013 打乱；R1 每次运行前按 sha 读回记录，运行后核对第一条 user 消息；停止条件按计划第 1 节；runs 文件字段按 agent 预注册；canary 规则已预先实现。preflight 22/22 题通过，R0 53/53 与 A5 sha 相同，R1 53/53 精确拼接，53 份记录重渲染逐字节相同。mock 4 个槽位（R0、R1 各 2，4 个 repo）跑通，注入核对 4/4；agent `a6-retry-freeze-r1`（`01db102`）的分析脚本读 mock runs 文件，输出 `STOP mock_input`。全量测试 `.venv` 两次都是 661 passed，22 skipped；系统 Python 两次都是 484 passed，199 skipped。记录在 `docs/sprint/CHECKPOINT-A6-1b.md`，没有打 tag，停下等审计。

## A6-R 第 2 轮（A6-2）：冻结和 canary

日期：2026-10-13。花费：2.450 CNY。依据 `A6-R-PLAN.zh-CN.md` 第 5 节 A6-2 和 `AUDIT-A6-1b.zh-CN.md` 第 3 节。

20:54 第一次开工时，agent 仓库还没有 `a6-retry-freeze-r2`，也没有 `CHECKPOINT-A6-1c.md`，按第 0 步停下，什么都没做。重新开工时核对到 r2 → `6c67739`，与 agent CHECKPOINT 一致。审计文件原样入库（`4b10d63`）。全量测试 661 passed、22 skipped 之后，写冻结记录 `A6-R-FREEZE.md`，并打 harness tag `a6-retry-freeze`（`0cbc63d`）。canary 前重跑 preflight，22/22 通过。

canary 4 个槽位（R0 2、R1 2）写入 `runs/a6-retry/`：没有触发停止条件，注入核对 4/4，隔离 4/4，模型 `deepseek-flash` @ `api.deepseek.com`，单次最高 0.834 元，累计 2.450 元。冻结后没有改代码。记录在 `docs/sprint/CHECKPOINT-A6-2.md`（`ce41746`），停下等审计，没有进入 A6-3。

## A6-R 第 3 轮（A6-3）：正式运行

日期：2026-10-13 22:04 至 10-14 03:51。花费：累计 164.577 CNY（`TOTAL_CAP` 210）。依据 `A6-R-PLAN.zh-CN.md` 第 5 节 A6-3 和 `AUDIT-A6-2.zh-CN.md` 第 3 节。审计文件原样入库（`50f54a7`）。

开跑前关闭系统睡眠（跑完后恢复），确认 Docker 在线。runner 跳过 4 个 canary 槽位，跑完其余 314 个：318/318 都有 summary，没有中断目录，没有触发停止条件。7 次 infra_error（都是快照前容器消失），各重跑一次完成。注入核对 318/318，runner 和独立复核结果一致。模型全程是 `deepseek-flash` @ `api.deepseek.com`。单次最高 0.940 元。`context_overflow`：R0 1 次，R1 2 次。

问题：最后约 4 分钟 DeepSeek 账户余额耗尽，22 次运行（R0 8 次、R1 14 次）收到 HTTP 402，被记成了 `model_parse_error` 失败，不是 infra_error，停止条件没有覆盖这种情况。runner 自动写出的 `a6-retry-runs.json`（`handoff_sha256` `05bea3fb…`，`a15696f`）包含这 22 行，暂不交接。没有改代码，没有移动目录，没有计算 R1−R0。记录在 `docs/sprint/CHECKPOINT-A6-3.md`，停下等审计决定这 22 次怎么处理。
