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
