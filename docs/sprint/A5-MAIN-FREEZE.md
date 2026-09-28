# A5-main 冻结记录

harness tag `a5-main-freeze` 指向加入本文件的提交。它的父提交 `2b1d2442c88d869534c8c54a3a667310477808c4` 是第 0 步的代码改动（infra_error 重跑、停止条件、模型记录）。

coding-agent tag `a5-main-freeze` 指向 `a22e4ca0a3994012c167a3e02e06498731c24a18`（见 coding-agent 提交 `1053203` 的 CHECKPOINT-6）。

从这里到 R6 结束，不改 runner、grader、镜像和校准。只有停止条件要求时才改，改动单独提交并在 CHECKPOINT 里写明影响了哪些已完成的运行。

## 输入文件

sha 用 `scripts/handoff_sha.py` 的 `handoff_sha256` 算：先把换行统一成 LF，再取 sha256。

| 文件 | sha256 |
|------|--------|
| `configs/sprint/main-targets.yaml` | `3556a5fdfac8b7d4ac2b631a31e2a7951312523aff605014f3b32eaf184738a4` |
| `docs/sprint/main-accepted-ids.txt`（56 道合格题） | `d71cb17adb44fd06f71bf8b0f8babcac12ea839354f1dcec30aae2ffa719b730` |
| `configs/sprint/b0-v2.yaml` | `ddf53b2db293bf03c7a099a43a34ea96aee5ecca365d9b8b4f11d66afb344e60` |
| `docs/sprint/memory-source-runs.json`（dev 交接） | `984826707e8f69ad9b900134bd244c6056f2d8860f3036a3606bfc60b4bcb450` |

`main-accepted-ids.txt` 是 `docs/sprint/main-calibration/*.json` 里 `accepted: true` 的 id，按字母排序，每行一个，末尾有换行。各仓库题数：pytest 12，sympy 12，django 11，sphinx 11，scikit-learn 10。

## 运行参数

| 参数 | 值 |
|------|----|
| `PARALLEL` | 4（B0 与 B2 相同） |
| `TOTAL_CAP` | 150 元 |
| B0 软上限 | 80 元 |
| `MAX_INFRA_RERUNS` | 2 |
| infra_error 停止线 | 超过已完成运行的 10% |

Docker Desktop：8 核，7.7 GiB 内存。

## 修订 1

tag `a5-main-freeze-r1` 指向加入本节的提交。原 tag `a5-main-freeze` 保留不动。依据是 `docs/sprint/HARNESS-SPRINT-6A-FIX.zh-CN.md` 和 CHECKPOINT-6 的两次审计结论。

### 原因

canary 里 sphinx-8593 在运行前比对失败。构建镜像时，`pre_install` 用 sed 改写的文件不参与 source-only 比对；运行时却参与了，而且没有排除。12 道题会因此在运行前失败（11 道 sphinx 和 pytest-8399）。镜像本身没有问题，也不是泄漏。

### 改动与提交

| 项 | 内容 | 提交 |
| --- | --- | --- |
| F1 | 被改写的文件按"在 clean image 的 /tmp tmpfs 里断网重放 sed 后的期望 sha"比对，不再有跳过不比的文件；构建和运行都通过 `overrides_for` 读同一份 `docs/sprint/rewritten-expected/<task>.json` | `a3b4450`、`53c072a` |
| F2 | `run_a5_main.py --preflight`：56 道题执行全部运行前检查，不调用模型 | `43ee604` |
| F3 | `--out-root`（只能和 `--mock` 一起用）和全池 mock 核对脚本 `scripts/sprint6_mock_e2e_check.py` | `43ee604`、`a3cdc3a` |
| F4 | 移动 sphinx-8593 的失败槽位，见下文 | 只移动文件，没有提交 |
| F5 | infra_error 次数 ≥ 3 **并且**超过已完成运行的 10% 时才停止 | `653ebbb` |

`docs/sprint/rewritten-expected/` 在本修订中的 git tree 是 `dab524dfff1c46344e1a3ec524b66048739c140e`。

### 改写命令的解析规则

- **guarded_sed**（审计批准新增）：一条命令按 `&&`、`||` 拆开后，每一段都是 `sed -i … <文件>` 或 `grep -q … <文件>`，至少有一段是 sed，并且都指向同一个不含 `/` 的文件。这时整条命令原文算作这个文件的改写命令，重放时整条交给 `/bin/sh` 执行，顺序和规格一致。
- **plain_sed 的收紧**：原来的"以 sed 开头、最后一个词不含 `/`"规则保留，但现在要求整条命令只有一段。否则 `sed … && pip install -e .` 会被误算成对 `.` 的改写。
- 其他命令都不算改写，比对时也不为它们放宽。
- 记录里每条命令都标明匹配的规则（`plain_sed` 或 `guarded_sed`）。
- 这次规则修改只影响 sphinx-9258：它的 `setup.py` 多了 2 条 guarded_sed 命令，期望 sha 是 `27bcaf655c0321c29b0c30ce9c740c8551c63a67cefd9a89436c05361cf5255a`。另外 11 份记录只新增了 `rules` 字段，其他内容不变。plain_sed 的收紧不影响 56 道题中的任何一道。

### 核对口径修正

1. **F2（审计批准）**：运行时 P2P 条数等于校准 `nodeids.p2p.used` 减去 `p2p_excluded` 条数，并且每个被排除的 id 都必须在选中的 P2P 列表里。涉及 sphinx-8120、9673、10323。
2. **F3（审计批准）**：有 `p2p_excluded` 的三道题，P2P 通过数等于 `empty_p2p` 的通过数，总数等于 `empty_p2p` 的总数减去排除条数；同时确认被排除的 id 没有出现在 grader 的用例里。
3. **F3（按第二次审计的授权自行修正）**：原口径要求"F2P 全部失败，并且等于 empty_f2p"。django-13512（1/3）和 sympy-14248（1/12）在空改动下各有 1 条 F2P 通过，运行时的结果和 `empty_f2p` 完全相同。校准的合格规则（`sprint5_prepare_main.py` 的 `acceptance`）只要求空改动下 F2P 不全部通过。新口径：F2P 的通过数和总数等于 `empty_f2p`，通过数小于总数，summary 的 `solved` 为 false。依据的记录字段是校准 JSON 的 `empty_f2p` 和 `accepted`。

三处都只改核对口径，不改任何运行时行为。

### F4 规则

模型调用为 0、花费为 0、因为 harness 运行前检查的 bug 而失败的运行，不算实验数据，可以移出后重跑这个槽位。**有模型调用的运行一律不适用这条规则。**

按这条规则，`runs/a5-main/sphinx-doc__sphinx-8593/b0/r1/` 已整个移到 `runs/a5-main-halted/sphinx-doc__sphinx-8593/b0/r1/`，`runs/a5-main/b0-report.json` 移到 `runs/a5-main-halted/b0-report.json`。

### 已完成的 canary

django-13964 r1 和 sklearn-13142 r1 继续有效。它们跑在 `02c8671` 上，`pre_install` 不改写源码文件，override 为空，新旧比对规则的结果相同。它们也没有 `p2p_excluded`，两种 id 口径的结果一致。

### F2、F3 结果

- F2 预检：56/56 通过。所有题 `answer_isolation_pass` 为 true，带 override 的 source-only 比对全部通过，grader id 按修正后的口径和校准一致，public task 全部生成。
- F3 mock 端到端：56 道 mock B0 r1 写在 `runs/a5-main-mock-e2e/`，花费 0，没有停止。
  - 没有 answer isolation 失败，没有 infra_error，grader 没有崩溃，没有 `missing`。
  - 按修正后的口径 56/56 一致：F2P 等于 `empty_f2p`（54 道 0 通过，2 道部分通过）。
  - P2P 全部通过，并且等于 `empty_p2p`（三道有排除的题是 43/43、23/23、38/38）。
  - 被排除的 id 都没有进入 grader。

冻结输入的 sha 没有变化，本修订没有改 clean image、校准记录、profile 和 `src/eval`。全量测试 343 passed、199 skipped。

## 修订 2

tag `a5-main-freeze-r2` 指向加入本节的提交。`a5-main-freeze` 和 `a5-main-freeze-r1` 保留不动。依据是 `docs/sprint/HARNESS-SPRINT-6B-FIX.zh-CN.md`（CHECKPOINT-6a 的审计结论）。

### 原因

第一次全量 B0 停止后发现了三类问题：

- 容器里的文件工具和 search_code 用了 `Path.is_relative_to`（3.9 才有）和 `subprocess.run(capture_output=, text=)`（3.7 才有）。在 3.6 和 3.8 的镜像里（17 道题），这些工具每次调用都失败。
- 并发下的 Docker 控制错误没有重试：两次候选快照因为 `ConnectionResetError` 失败，被当成空补丁评分（`delta_lost`）。
- 一次 grader 在测试开始之前超时，被记为 `invalid_env`。

### 改动与提交

| 项 | 内容 | 提交 |
| --- | --- | --- |
| G1 | 容器内代码兼容 Python 3.6：`is_relative_to` 改成 `relative_to` 加 `try/except ValueError`（越界照样拒绝），`capture_output/text` 改成 `stdout/stderr=PIPE, universal_newlines=True`。改了 `FILE_CODE`、`SEARCH_CODE` 和 B2 dispatcher 的 `RPC`。新测试会自动收集 A5-main 路径上所有送进容器执行的 Python 代码（22 段，包括工具、后端、grader、runner、source-only 比对和重放），做两件事：一是静态扫描 3.7+ 的 API 和语法，二是在 `python:3.6.15-slim-buster` 里对每段跑 `py_compile`，同时在 3.6 里实际执行文件工具和 search_code，确认符号链接逃逸仍然被拒绝。本轮已实跑通过。 | `ef32056` |
| G2 | `--preflight` 加工具冒烟，零模型调用。每道题先按真实运行的方式启动 clean image（`clean_backend`，和 `run_task` 共用），然后用固定参数依次调用 `list_dir`、`read_file`（仓库根目录的 `setup.py`，没有就取第一个文件）、`search_code`、`run_command`（在 /workspace 建临时文件并打印 Python 版本）、`search_replace`、`edit_file`，最后用 `read_file` 确认两处编辑生效。容器关闭时不导出，也不评分。判失败的情况有两种：`success=False`，或输出里有 Python traceback。 | `074a076` |
| G3 | Docker 控制调用遇到 `DockerUnavailable`、`ConnectionResetError` 或 `TimeoutError` 时，间隔 2、5、10 秒重试 3 次，每次重试都记进 summary 的 `docker_retries`（阶段、操作、第几次、等待、错误、时间）。重试后仍失败的运行记 `infra_error`，走原来的重跑规则，细则见下文。 | `e4b919a` |
| G4 | summary 加 `harness_tool_errors`，任何运行大于 0 就停止启动新运行。`scripts/sprint6_canary.py` 负责 canary 的选题和检查。 | `040a7a8` |
| G5 | `PARALLEL=3`（B0 与 B2 相同），B0 软上限 110 元，`TOTAL_CAP` 220 元 | `d002f27` |
| G6 | 作废 25 次运行，见下文 | `53600b9`（脚本；文件只移动） |

### G3 细则

- **重试的调用**：凡是经过 `DockerExecutionBackend._ok` 的调用，包括：
  - `info`、`image inspect`、`create`、`start`、`inspect`；
  - 启动时的 exec（导入文件、复制仓库、链接 native 产物）；
  - 候选快照（`export_delta`）；
  - grader 的启动、APPLY、上传 runner、读取 receipt；
  - 容器销毁（`rm -f` 和 `ps` 确认）。
- `create` 重试之前，先 `rm -f` 同名容器，避免第一次其实已经建成导致名字冲突。
- **不重试的失败**：
  - 容器里 harness 脚本自己报 traceback，以及 `delta_too_large`。这两种是程序结果，不是 Docker 控制错误，重试也不会变。
  - agent 工具命令本身的 `docker exec`（`execute()`）。命令可能已经执行了一部分，不能安全地重放。如果这类失败把容器关掉了，候选快照就不存在，按下一条记 `infra_error`，不会按空补丁评分。
- **agent 阶段记 `infra_error`、不送 grader 的情况**：
  - StoreError；
  - 容器启动失败；
  - 候选快照失败（`snapshot_error` 非空，包括 `container_gone_before_snapshot`）；
  - 没有候选快照；
  - 容器销毁失败。
- **grader 阶段**：
  - `execution_status` 为 None，也就是在测试执行之前就失败或超时，记 `infra_error`；
  - 测试开始以后超时，仍是普通失败；
  - 测试结束以后读 receipt 失败，仍按 grader 崩溃停止。
- summary 新增 `run_error`、`infra_reason`、`docker_retries`。

### harness_tool_errors 的口径

只统计程序由 harness 提供的工具：`read_file`、`list_dir`、`write_file`、`edit_file`、`search_replace`、`search_code`。计数条件：

- 输出里的 Python traceback 最后一个异常是实现类异常，即 `AttributeError`、`ImportError`、`ModuleNotFoundError`、`SyntaxError`、`IndentationError`、`TabError`、`NameError`、`UnboundLocalError`、`TypeError` 之一；
- 并且该次调用的参数符合工具 schema（按 `tool.intent` 配对）。

以下情况不计入：`run_command` 的输出（那是 agent 自己的命令）、"file not found"/"path denied"/"search string not found" 这类 `ValueError`/`OSError`，以及参数不合 schema 时的异常。用作废的 25 次运行校验：这个口径算出 109 次，和人工统计的 `is_relative_to` 失败次数一次不差；agent 命令里的 12 个 traceback 都没有计入。

### 作废规则与 25 次运行

**修订 2 之前的全部 B0 运行，不论结果。** `runs/a5-main/` 下的 25 次运行和 `b0-report.json` 已整个移到 `runs/a5-main-void/r1-tool-py36/`，只移动、不删除，那里的 `README.md` 和 `void-runs.json` 列出每次运行的镜像 Python、`harness_tool_errors`、solved、status 和花费。

- 这 25 次运行是：
  - django 11211、11749、12276、13109、13512、13964、14434 各 r1–r3；
  - django-15022 r1–r2；
  - sklearn-13142 r1；
  - sphinx-8593 r1。
- 合计 `harness_tool_errors` 109，解出 2 次（django-13964 r2、sklearn-13142 r1），花费 13.682 元。这部分花费不计入 `TOTAL_CAP`。
- 修订 1 里"继续有效"的 canary（django-13964 r1、sklearn-13142 r1）也在其中，同样作废。
- 修订 1 的 F4 移到 `runs/a5-main-halted/` 的零花费槽位不受影响。

B0 从空的 `runs/a5-main/` 重新开始。这一轮没有生成过 `docs/sprint/main-b0-runs.json`。

### 运行参数（修订 2）

| 参数 | 值 |
|------|----|
| `PARALLEL` | 3（B0 与 B2 相同） |
| `TOTAL_CAP` | 220 元，只统计 `runs/a5-main/` 下的花费，作废运行不计 |
| B0 软上限 | 110 元 |
| `MAX_INFRA_RERUNS` | 2 |
| infra_error 停止线 | ≥ 3 并且超过已完成运行的 10% |
| 新停止条件 | 任何运行 `harness_tool_errors > 0` |
| Docker 控制重试 | 3 次，间隔 2、5、10 秒 |

### 预检结果

`run_a5_main.py --preflight`（`runs/a5-main-logs/preflight.json`）：56/56 通过，其中工具冒烟 56/56。

| 镜像 Python | 通过 / 总数 | 工具冒烟 | 容器里实际的版本 |
| --- | --- | --- | --- |
| 3.6 | 15 / 15 | 15 / 15 | 3.6.15 |
| 3.8 | 2 / 2 | 2 / 2 | 3.8.20 |
| 3.9 | 38 / 38 | 38 / 38 | 3.9.25 |
| 3.11 | 1 / 1 | 1 / 1 | 3.11.16 |

所有冒烟容器都确认已清理。冻结输入的 sha、clean image、校准记录、`rewritten-expected`（tree 仍是 `dab524dfff1c46344e1a3ec524b66048739c140e`）和 profile 都没有变化。

### canary 选题

每个镜像 Python 版本各一道，按 `created_at` 排序取下中位：3.6 取 sklearn-14053，3.8 取 django-13964，3.9 取 pytest-7490，3.11 取 django-16527。检查项包括：

- 第 1 步原有各项；
- `harness_tool_errors == 0`；
- 没有 infra_error（因此也没有 Docker 控制类 infra_error）。

## 修订 3

tag `a5-main-freeze-r3` 指向加入本节的提交。`a5-main-freeze`、`a5-main-freeze-r1`、`a5-main-freeze-r2` 保留不动。依据是 `docs/sprint/HARNESS-SPRINT-6C-FIX.zh-CN.md`（CHECKPOINT-6a 的审计结论）。

### 原因

修订 2 下的 36 次正式运行 0 解出。根因是 pool 题的 user prompt 里没有 issue 文本，只有 `Public issue for <id>` 占位（38 个字符）：

- `select_main_targets.py` 只把 `instance_id`、`FAIL_TO_PASS`、`PASS_TO_PASS`、`patch`、`test_patch` 存进私有文件，没有保存 `problem_statement`；
- `materialize_runner_task` 用 `private.get("problem_statement") or ("Public issue for " + id)` 静默回退。

作废的 38 个运行目录里，记录下来的 user prompt 全部是占位文本（infra 槽位也是）。dev 14 题的 public task 由另一条路径生成，带有完整 issue，不受影响。

### 改动与提交

| 项 | 内容 | 提交 |
| --- | --- | --- |
| H1 | 从 `princeton-nlp/SWE-bench_Verified` test（Hub revision `c104f840cc67f8b6eec6f759ebc8b2693d585d4a`，文件 `data/test-00000-of-00001.parquet`）读取 60 道题的 `problem_statement`，原样保存（不 strip，不拼 `hints_text`，与 dev 相同）到 `runs/sprint5-main-public/<id>.json`（`issue_text`、`issue_sha256`、`repo_ref`），并写 `docs/sprint/main-issues.json`。脚本 `scripts/sprint6_restore_issues.py` 先按原规则重新选题，60 个 id 与顺序和 `main-targets.yaml` 一致、id 列表 sha 仍是 `d4caaa48…`、repo 与 base_commit 一致，才写文件。`select_main_targets.py` 以后选题时同时写 public 文件；本轮没有重选。`materialize_runner_task` 改为直接用 public 文件，不再从私有文件拼 issue | `6a21da4` |
| H2 | 去掉静默回退，改为报错，改动位置见下表；新增 `tests/test_no_silent_fallback.py` | `2dddb2b` |
| H3 | 预检对每道合格题渲染完整 user prompt，检查：原样包含 `issue_text`、issue sha 与 `main-issues.json` 一致、长度大于 0、不含私有字段内容。另外渲染 dev 14 题的 prompt，要求与 `runs/sprint4-b0-v2/<id>/r1/events.jsonl` 里记录的 user prompt 逐字节一致；不一致时 `--preflight` 失败 | `b0d25be` |
| H4 | summary 增加 `issue_sha256`、`prompt_sha256`。canary 改为每个 repo 一道，检查项增加"`issue_sha256` 等于 `main-issues.json`"和"有 `prompt_sha256`" | `f1b1f8c` |
| H5 | 故障警报（规则见下） | `dc61377` |
| H6 | 候选改动导致的 missing 记普通失败（规则见下） | `1133112` |
| H7 | 作废修订 3 之前的 38 个运行目录（规则见下），脚本 `scripts/sprint6_void_r2.py` | `7d768b9` |
| H8 | B0 软上限 120 元，`TOTAL_CAP` 230 元，`PARALLEL` 仍为 3 | `60fd926` |

### H2 改为报错的位置

| 文件 | 原来的回退 | 现在 |
| --- | --- | --- |
| `scripts/run_a5_main.py` `materialize_runner_task` | `private.get("problem_statement") or ("Public issue for " + id)` | 读 `runs/sprint5-main-public/<id>.json`；文件缺失、`issue_text` 为空、sha 与 `main-issues.json` 不一致、`repo_ref` 与目标不一致都报错（`checked_public`） |
| 同上 | `private.get("test_patch") or ""`、`private.get("patch") or ""`（grader id 选择与 receipt 的 patch 路径） | 为空就报错 |
| `scripts/run_swe_task.py` `public_issue` | `public.get("issue_text") or ""` | `issue_text()`：为空、只有空白或以 `Public issue for ` 开头都报错 |
| 同上 | `repo_ref.get("repo_id", task.get("repo", ""))`、`repo_ref.get("revision", "")` | `repo_ref` 缺 `repo_id` 或 `revision` 就报错 |
| 同上 | family 不是 django 就用 pytest 命令 | 按 family 查表（django、pytest-dev、scikit-learn、sphinx-doc、sympy），查不到就报错 |
| `scripts/run_swe_task.py` `run_task`（卡片插件） | 两处 `public.get("issue_text") or ""` | `issue_text(public)` |
| `scripts/run_swe_task.py` `grader_spec` | `binding.get("test_patch_paths") or []`、`binding.get("gold_patch_paths") or []` | 为空就报错 |
| `scripts/run_swe_task.py` `grader_spec`、`run_task` | `task.get("grader_timeout_seconds", 300)` | 必须给出（pool 与 dev 都是 600） |

检查过、没有改的 `or` 默认值：`api_key or "mock"/"smoke"`（只在 mock 和工具冒烟里用，不调模型）、`result.output or ""`（工具冒烟的输出）、`_named_reason(...) or "unknown"`（停止原因的显示）、`base_url or ""`（模型身份记录）、`_memory_task` 里的 `.get(..., "")`（dev 记忆源核验，不在 A5-main 路径上）、`p2p_excluded or []`（合法地可以为空）。

### main-issues.json

`docs/sprint/main-issues.json` 的 sha256（`handoff_sha256`，LF）是 `114f6367a0f14e274a2f4af5368661a21533b436ae9e50ee073e6a530310c0ba`。它记录数据集名称、split、Hub revision、parquet 文件 sha256、60 个 id 的列表 sha，以及每道题的 `issue_sha256` 和字符数。

- 60 道题 issue 字符数：最小 190，中位 1448，最大 22778。
- 56 道合格题：最小 190，中位 1498.5，最大 22778。
- dev 14 题里有 2 道也在 Verified 中（django-10914、sklearn-10297），它们的 dev `issue_text` 与数据集 `problem_statement` 逐字节相同，说明"原样保存"与 dev 的做法一致。

### 作废规则

**修订 3 之前的全部 B0 运行，不论结果。** `runs/a5-main/` 下的 38 个运行目录（36 个正式槽位、2 个 infra 槽位 `django-12276/b0/r1.infra1`、`django-15973/b0/r2.infra1`）和 `b0-report.json` 已移到 `runs/a5-main-void/r2-no-issue/`，只移动，不删除；那里的 `README.md` 和 `void-runs.json` 逐个列出。已经花掉的 24.055 元记为作废成本，不计入实验，也不计入 `TOTAL_CAP`（只统计 `runs/a5-main/`）。B0 从空的 `runs/a5-main/` 重新开始。

### 故障警报（预注册）

全量 B0 中（不含 5 道 canary 的 r1），完成的正式运行（不含 `r<k>.infra<n>` 退役槽位和 `infra_error`）达到 30 次时，如果解出数为 0，就停止启动新运行，等待审计。实现在 `run_a5_main.fault_alarm`，每次运行结束后与其他停止条件一起检查。

这一条只用来发现 harness 故障，不改变实验设计。触发后只允许排查 harness，不允许因此调整题目、profile 或卡片。

### 候选改动导致的 missing

- grader receipt 的 `runner_error`，以及收集阶段每条 traceback 的末尾（新字段 `collection_error_tails`，每条保留最后 2048 个字符；原有 `collection_errors` 不变）：取其中最内层属于项目的栈帧（`/workspace/` 下或相对路径的文件；跳过标准库、site-packages、`/tmp/a5-runner.py` 和 frozen 模块）。
- 如果这个文件在本次候选改动修改过的文件里，就把这次运行记为普通失败（`solved=false`），summary 记录 `grader_candidate_error`（来源和文件），不停止。
- 其他 missing 照常停止。候选改动为空时，这条规则永远不适用。
- canary 检查里的"grader reported missing ids"按同一规则放行。
- 用修订 2 停止时的 django-16527 r2 核对：候选在 `django/contrib/admin/views/main.py` 里引入了 `IndentationError`，按这条规则判为候选错误；如果把候选改动当成空的，则仍然停止。

### 运行参数（修订 3）

| 参数 | 值 |
|------|----|
| `PARALLEL` | 3（B0 与 B2 相同） |
| `TOTAL_CAP` | 230 元，只统计 `runs/a5-main/` 下的花费 |
| B0 软上限 | 120 元 |
| `MAX_INFRA_RERUNS` | 2 |
| infra_error 停止线 | 满 3 次且超过已完成运行的 10% |
| 其他停止条件 | 任何运行 `harness_tool_errors > 0`；非候选错误的 missing；grader 崩溃；隔离失败；模型变化；故障警报 |
| Docker 控制重试 | 3 次，间隔 2、5、10 秒 |

冻结输入（`main-targets.yaml`、`main-accepted-ids.txt`、`b0-v2.yaml`、`memory-source-runs.json`）的 sha 与上表相同；clean image 记录和校准记录自 `a5-main-freeze-r2` 以来没有改动。

### 预检结果

`run_a5_main.py --preflight`（`runs/a5-main-logs/preflight.json`）：56/56 通过；工具冒烟 56/56；prompt 检查 56/56；dev prompt 14/14 逐字节一致。

| 镜像 Python | 通过 / 总数 | 工具冒烟 |
| --- | --- | --- |
| 3.6 | 15 / 15 | 15 / 15 |
| 3.8 | 2 / 2 | 2 / 2 |
| 3.9 | 38 / 38 | 38 / 38 |
| 3.11 | 1 / 1 | 1 / 1 |

私有内容检查的口径：gold patch、test patch、F2P/P2P 原始列表都不能出现在整个 prompt 里；单个 F2P/P2P id 不能出现在 prompt 的模板部分（去掉末尾原样 issue 后的部分）。有 3 道题的单个 id 出现在数据集自带的公开 issue 里，只记录，不算泄露：sympy-15599（`test_Mod`）、pytest-5262 和 pytest-7521（P2P id `[100%]`）。

### canary 选题

每个 repo 各一道，按 `created_at` 排序取下中位：django-13964、pytest-7205、scikit-learn-13142、sphinx-8593、sympy-16766。每道跑一次真实的 B0 r1。检查项包括：

- 第 1 步原有各项；
- `harness_tool_errors == 0`；
- 没有 infra_error；
- `issue_sha256` 等于 `main-issues.json`，并且有 `prompt_sha256`。

全套测试：412 passed，199 skipped。
