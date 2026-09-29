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

### 修订 1 执行记录（F1 第 5 项停止）

依据 `docs/sprint/HARNESS-SPRINT-6A-FIX.zh-CN.md`。**结论：F1 第 5 项的离线核对在 sphinx-9258 上失败，按规定停下，没有回退到做法 1。** F2–F6 都没有做，sphinx-8593 的补跑和全量 B0 也没有开始。本轮真实花费 0，累计仍是 0.687 元。

#### F1 已完成的部分（提交 `a3b4450`）

- `scripts/rewritten_sources.py`：
  - `sed_rewrites` 返回"文件 → 按顺序作用于它的 sed 命令"，解析规则和原来一致：命令以 `sed` 开头，最后一个词是不带 `/` 的文件名。
  - `replay` 在 clean image 里用 `--network none --read-only --tmpfs /tmp` 起临时容器，把压缩包里的原文件写进 `/tmp/rewrite`，再用 `/bin/sh -c` 按顺序执行这些命令（构建时也是用 sh 执行的），然后取 sha256。
  - `load_overrides` 读 `docs/sprint/rewritten-expected/<task>.json`。如果记录里的文件集合、命令原文或原文件 sha 和当前规格、压缩包不一致，就拒绝。
- `source_only_check` 的 `ignore` 参数换成 `overrides`，不再有跳过不比的文件。override 里出现压缩包中不存在的文件时报错。
- 构建路径（`sprint5_prepare_main.py`）和运行路径都通过 `overrides_for` 取同一份 override。运行路径的检查抽成了 `prerun_check`，`run_task` 调用它，F2 预检也准备调用它。
- 测试在 `tests/test_rewritten_sources.py`，共 11 个，覆盖三种情况：override 文件内容正确时通过；被改动时失败；不在 override 里的文件被改动时失败。另外测了记录不一致时拒绝。全量测试 325 passed、199 skipped。

#### F1 第 5 项：12 道受影响题的离线核对

脚本是 `scripts/sprint6_rewritten_expected.py`，记录写在 `docs/sprint/rewritten-expected/`。

| 题 | override 文件 | 被 sed 改变的文件 | 核对 |
| --- | --- | --- | --- |
| sphinx 7440、7590、7910、8120、8459、8593、9461、9673 | `setup.py`、`tox.ini` | 2 | 通过 |
| sphinx-9258 | `setup.py`、`tox.ini` | 2 | **`setup.py` 不一致** |
| sphinx 10323、10614 | `tox.ini` | 1 | 通过 |
| pytest-8399 | `setup.cfg` | 0（这个版本的文件里没有 `>=>=`，sed 没有改动） | 通过 |

11/12 通过，其中 sphinx-8593 的比对结果是原 tree hash `35681e93…`。

#### sphinx-9258 为什么不一致

镜像是正确的，问题出在解析规则上。sphinx 4.1 的规格里有两条命令带 `grep` 守卫：

```text
grep -q 'sphinxcontrib-htmlhelp>=2.0.0' setup.py && sed -i 's/sphinxcontrib-htmlhelp>=2.0.0/sphinxcontrib-htmlhelp>=2.0.0,<=2.0.4/' setup.py || sed -i 's/sphinxcontrib-htmlhelp/sphinxcontrib-htmlhelp<=2.0.4/' setup.py
grep -q 'sphinxcontrib-serializinghtml>=1.1.5' setup.py && sed -i 's/sphinxcontrib-serializinghtml>=1.1.5/sphinxcontrib-serializinghtml>=1.1.5,<=1.1.9/' setup.py || sed -i 's/sphinxcontrib-serializinghtml/sphinxcontrib-serializinghtml<=1.1.9/' setup.py
```

它们的第一个词是 `grep`，所以现有规则不把它们算作改写命令，重放时就少了这两处锁定。构建时的 Dockerfile（`runs/sprint5-main-images/sphinx-doc__sphinx-9258/context/Dockerfile`）执行过这两条命令，镜像里的 `setup.py` 多出 `sphinxcontrib-htmlhelp<=2.0.4` 和 `sphinxcontrib-serializinghtml<=1.1.9`，和规格一致。

验证：把 `setup.py` 相关的 8 条命令（6 条普通 sed 加这 2 条）按原顺序重放，得到 `27bcaf655c0321c29b0c30ce9c740c8551c63a67cefd9a89436c05361cf5255a`，和镜像里的文件完全一致。`tox.ini` 的期望 sha 本来就对得上。

旧的构建检查没有发现这个问题，是因为 `setup.py` 整个被跳过了。

在 56 道题的规格里，现有规则没有覆盖到的 `pre_install` 命令只有三条：上面两条（只出现在 sphinx-9258），以及 sphinx-10614 的 `apt-get update && apt-get install -y graphviz`（不碰仓库文件）。

提交的 `sphinx-doc__sphinx-9258.json` 是按现有规则生成的，只有 6 条 `setup.py` 命令，期望 sha 是 `4533f9b2…`。按这份记录，运行时会对 9258 报 `opt/repo source-only hash mismatch` 并停下，不会跳过比对；`prerun_check` 实测也是这样。

#### 需要审计决定

F1 第 1 项要求解析规则和现在一致，而修好 9258 必须改这条规则，所以需要审计批准。建议：一条命令按 `&&`、`||` 拆开后，如果每一段都是 `sed -i … <文件>` 或 `grep -q … <文件>`，并且都指向同一个不带 `/` 的文件，就把整条命令原文算作这个文件的改写命令，重放时整条交给 sh 执行。按这条规则，9258 的 `setup.py` 会有 8 条命令，期望 sha 就是上面验证过的 `27bcaf65…`；其他 11 道题的记录不变。

#### 对已完成运行的影响

两次有效 canary（django-13964 r1、sklearn-13142 r1）跑在 `02c8671` 上。它们的 `pre_install` 不改写源码文件，override 为空，新旧比对规则的结果相同，不受影响。

sphinx-8593 的失败槽位还在 `runs/a5-main/` 里，F4 的移动没有执行。

停在这里等审计。没有开始 B0，没有看 B2，也没有开始 B2。coding-agent 侧继续等 `main-b0-runs.json`。

### 修订 1 执行记录（续）：F1 完成，F2 预检停止

审计批准了 guarded_sed 规则。**结论：F1 12/12 通过。F2 预检按原口径是 53/56，按规定停下；三道不一致的题都是校准时就排除过 P2P 的题，修正口径后是 56/56。** F3–F6、sphinx-8593 补跑和全量 B0 都没有做。本轮真实花费 0，累计 0.687 元。

#### F1（提交 `53c072a`）

- `rewrite_target` 按审计给的规则判断：
  - `plain_sed`：单独一条 `sed … <文件>`。
  - `guarded_sed`：按 `&&`、`||` 拆开后，每段都是 `sed -i … <文件>` 或 `grep -q … <文件>`，至少有一段是 sed，并且都指向同一个不含 `/` 的文件。
  - 其他命令都不算改写。
- 有一处比原规则收紧了：`plain_sed` 现在要求整条命令只有一段。原规则只看第一个词和最后一个词，会把 `sed … && pip install -e .` 误算成对 `.` 的改写，这正是审计要求不识别的形式。56 道题的规格里没有这种命令，所以这处收紧不影响任何题。
- 记录里每个文件新增 `rules`，与 `commands` 一一对应；读取记录时也会核对。
- 新增测试：guarded 命令能被识别；以下 8 种形式都不被识别：
  - 混入 `pip install` 或 `python -m pip`；
  - 两段指向不同文件；
  - 只有 grep；
  - 路径带 `/`；
  - `grep` 不带 `-q`；
  - `apt-get`。

离线核对 12/12 通过。sphinx-9258 的 `setup.py` 现在有 8 条命令（6 条 plain_sed、2 条 guarded_sed），期望 sha 是 `27bcaf655c0321c29b0c30ce9c740c8551c63a67cefd9a89436c05361cf5255a`，和镜像一致。另外 11 份记录去掉新增的 `rules` 字段后，和旧版逐字段相同。56 道题的规格里，没有被识别为改写的命令只剩 sphinx-10614 的 `apt-get update && apt-get install -y graphviz`。

#### F2（提交 `43ee604`）

`--preflight` 对每道题依次执行：`materialize_runner_task`（grader id 与校准核对、生成 public task），`prerun_check`（解析镜像、`answer_isolation_pass`、带 override 的 source-only 比对），比较 grader id 条数和校准 JSON，最后执行 `public_issue`。结果写到 `runs/a5-main-logs/preflight.json`。另外按 F3 的要求加了 `--out-root`，只能和 `--mock` 同时使用，使用时不写交接文件。

第一次预检拿运行时条数直接和校准 JSON 的 `nodeids.*.used` 比，结果 53/56（保存在 `runs/a5-main-logs/preflight.used-count.json`）：

| 题 | 运行时 F2P/P2P | 校准 used | `p2p_excluded` | 校准 empty_p2p |
| --- | --- | --- | --- | --- |
| sphinx-8120 | 1/43 | 1/44 | `test_intl.py::test_text_docfields` | 43/44 |
| sphinx-9673 | 1/23 | 1/24 | `test_ext_autodoc_configs.py::test_autodoc_typehints_description` | 23/24 |
| sphinx-10323 | 1/38 | 1/40 | `test_directive_code.py::test_literal_include_linenos`、`test_linenothreshold` | 38/40 |

这不是运行时的错误。56 道题里只有这三道带 `p2p_excluded`，被排除的 P2P 在空改动和 gold 下都失败，校准时就决定排除。`materialize_runner_task` 把它们交给 runner，`grader_spec` 在运行时去掉，所以运行时条数正好等于 `used` 减去排除条数。是我写的预检口径没有考虑排除。

修正后的口径：运行时 P2P 条数等于 `used` 减去 `p2p_excluded` 条数，并且每个被排除的 id 都必须在选中的 P2P 列表里。按这个口径重跑是 56/56，所有题的 `answer_isolation_pass` 都为 true，source-only 比对全部通过。

#### 需要审计决定

1. **预检口径。** 请确认 F2 的"核对 grader id 和校准 JSON"采用扣除 `p2p_excluded` 后的条数。确认后，56/56 这个结果可以直接用，不需要重跑。
2. **F3 的核对口径也会碰到同一件事。** F3 要求"P2P 的通过数和总数等于校准里的 empty_p2p"。这三道题运行时的总数比 `empty_p2p` 少掉排除的条数，而被排除的 P2P 正好是空改动下失败的那几条。建议 F3 对这三道题按"通过数 = empty_p2p 通过数，总数 = empty_p2p 总数减排除条数"核对，其他 53 道照原口径。

前两次 canary 运行（django-13964、sklearn-13142）没有 `p2p_excluded`，两种口径的结果相同。

停在这里等审计。没有做 F3–F6，没有补跑 sphinx-8593，没有开始 B0，也没有看或开始 B2。coding-agent 侧继续等 `main-b0-runs.json`。

### 修订 1 执行记录（续二）：F3–F6

审计批准了两个口径修正，并授权我在核对差异能被已提交的校准记录完全解释、且不涉及运行时行为时，自己修正口径后继续。

- **F3**：56 道 mock B0 r1，花费 0，没有停止，报告在 `runs/a5-main-logs/mock-e2e-check.json`。按原口径是 54/56，差异属于授权范围，修正口径后是 56/56。
  - 原口径：F2P 全部失败，并且等于 `empty_f2p`。
  - 差异：django-13512 是 1/3，sympy-14248 是 1/12。运行时结果和 `empty_f2p` 完全相同，只是不满足"全部失败"。
  - 新口径：F2P 的通过数和总数等于 `empty_f2p`，通过数小于总数，并且 `solved` 为 false。
  - 依据的记录字段：校准 JSON 的 `empty_f2p` 和 `accepted`。合格规则 `acceptance` 只要求空改动下 F2P 不全部通过。
  - 三道有 `p2p_excluded` 的题按审计批准的口径核对通过：43/43、23/23、38/38，被排除的 id 都没有进入 grader 用例。全池没有 `missing`。
- **F4**：sphinx-8593 的失败槽位和旧的 `b0-report.json` 已移到 `runs/a5-main-halted/`。
- **F5**：infra_error 次数 ≥ 3 并且超过已完成运行的 10% 才停止（`653ebbb`）。F3 的 mock 跑在这次改动之前，没有出现 infra_error，所以不受影响。
- **F6**：冻结修订写在 `A5-MAIN-FREEZE.md` 的"修订 1"一节，tag `a5-main-freeze-r1`。

### 修订 1 之后：sphinx-8593 canary 与全量 B0（停止）

**结论：全量 B0 在第 22 次新运行后触发"grader 崩溃"停止条件（django-14434 r2）。排查时发现了一个更严重的运行时 bug：在 Python 低于 3.9 的镜像里，agent 的结构化工具全部报错。这影响 56 道题中的 17 道，也影响已完成的 25 次运行中的 22 次。** 累计花费 13.682 元。没有生成 `main-b0-runs.json`，没有开始 B2，coding-agent 暂时不要构建 v6 卡片。

#### sphinx-8593 canary

跑在 `fb26dbd`（`a5-main-freeze-r1`）上：
- `mock: false`，`profile: b0-v2`，模型是 `deepseek-flash` @ `api.deepseek.com`；
- `answer_isolation_pass: true`，grader id 为 F2P 2、P2P 1，和校准一致（没有排除项），没有 `missing`；
- 花费 0.467 元，记入了账本，没有 infra_error；
- 结果是未解出，模型调用 35 次。

第 1 步列出的检查项全部通过，于是进入第 2 步。

#### 全量 B0 停在哪里

`run_a5_main.py --phase b0` 从 20:53 开始，新完成 22 次运行后，django-14434 r2 的 grader 返回 `invalid_env`，reason 是 `TimeoutError: `。runner 停止开新运行，等在跑的运行结束后退出，报告显示 `started: 22`，`not_started: 143`。已跑的题是 django 的 11211、11749、12276、13109、13512、13964、14434 各 3 次，以及 15022 的 2 次。

#### 运行时问题 1：Python 低于 3.9 的镜像里工具全部失败（主要问题）

容器内的工具脚本用了 `Path.is_relative_to`，这个方法是 Python 3.9 才加入的。涉及的文件是 `src/tools/container_files.py` 第 17 行和 `src/tools/search.py` 第 23、54 行。在 3.8 和 3.6 的镜像里，以下工具每次调用都报 `AttributeError: 'PosixPath' object has no attribute 'is_relative_to'`：`read_file`、`list_dir`、`search_code`、`search_replace`、`edit_file`。agent 只能改用 `run_command`，用 sed 或 python 来查看和修改文件。

| 镜像 | 合格题数 | 题 |
| --- | --- | --- |
| `python:3.8-slim-bookworm` | 2 | django 13964、14434 |
| `python:3.6.15-slim-buster` | 15 | django 11211、11749、12276、13109、13512，sklearn 全部 10 道 |
| `python:3.9` / `3.11` | 39 | 其余（这些镜像里工具正常） |

已完成的 25 次运行中，跑在低于 3.9 镜像上的 22 次，每一次都有这类失败：
- 共 109 次工具调用失败：`search_code` 46、`read_file` 24、`list_dir` 22、`search_replace` 12、`edit_file` 5；
- 两次 canary 也在其中：django-13964 r1 失败 5 次，sklearn-13142 r1 失败 4 次；
- 跑在 3.9 镜像上的 django-15022 两次和 sphinx-8593 一次，没有出现这类失败。

这个问题之前没有被发现，有两个原因：mock 运行不调用工具，所以 F3 测不到；第 1 步的 canary 检查项里没有"工具是否报错"这一项。

django-14434 r3 的 `delta_lost` 也是这个 bug 造成的。它唯一一次 `search_replace` 调用失败了，改动从来没有写进去；并不是改动写进去之后丢失了。

#### 运行时问题 2：并发 4 时 Docker 控制通道出错

22 次新运行中有 3 次，出错点在 Docker 控制调用上，不是模型或测试本身的问题：

| 时间 | 运行 | 现象 | 当前归类 |
| --- | --- | --- | --- |
| 21:04:57 | django-12276 r1 | 候选改动快照失败：`DockerUnavailable … ConnectionResetError` | `delta_lost`（改动丢失，按空改动评测） |
| 21:10:20 | django-13109 r1 | 同上 | `delta_lost` |
| 21:20:44 | django-14434 r2 | grader 启动后 12 秒报 `TimeoutError`，发生在测试执行之前（`execution_status` 为空） | `invalid_env`，触发停止 |

同一道题的另外两次运行 grader 都正常（14434 r3 的测试只用了 1.5 秒），说明问题不在题目本身。按现在的规则，只有 `StoreError` 才算 infra_error，这 3 次都不会被重跑。前两次还会作为"未解出"进入实验数据。

#### 花费

新运行平均每次 0.569 元，25 次平均 0.547 元，平均模型调用 37.6 次，其中 17 次用满了 40 次调用。按这个速度，168 次 B0 大约需要 92–96 元，会在第 140 次左右碰到 80 元的 B0 软上限。工具失败可能推高了调用次数，但 3.9 镜像上的三次也花了 0.47–0.81 元。

#### 6a 要求的统计（截至停止）

| 项 | 值 |
| --- | --- |
| 有效 B0 运行 | 25（canary 3 次 + 全量 22 次），其中 22 次受工具 bug 影响 |
| 解出 | 2/25：django 1/23（13964 r2），sklearn 1/1（13142 r1），sphinx 0/1 |
| 每题 k/3（跑满 3 次的 7 道题） | 0/3：6 道；1/3：1 道（django-13964）；2/3、3/3：0 道 |
| infra_error | 0，没有重跑（上面 3 次 Docker 控制错误没有被归为 infra_error） |
| 花费 | 13.682 元 |
| 平均模型调用 | 37.6 |
| 停止原因 | `max_model_calls` 17，`completed` 6，`candidate_snapshot_failed` 2；总时限超时 0；grader 超时 1 |
| `main-b0-runs.json` sha | 没有生成 |

报告在 `runs/a5-main/b0-report.json`，日志在 `runs/a5-main-logs/b0-full.log`。

#### 需要审计决定

1. **工具 bug 怎么修。** 把容器内脚本里的 `is_relative_to` 换成 3.6 也能用的写法，比如 `os.path.commonpath`，或者 `relative_to` 加 `try`。修完之后，在 3.6 和 3.8 的镜像里各跑一次零花费的工具冒烟测试。这是运行时改动，需要单独提交并再做一次冻结修订。
2. **受影响的 22 次运行怎么处理。** 其中包括 django-13964 r1 和 sklearn-13142 r1 两次 canary。它们都有模型调用，按 F4 规则不能移出；但这 22 次都是在工具残缺的状态下测出来的，和修复后的运行不可比。需要审计决定是作废后重跑（约 12.5 元），还是用别的办法处理。
3. **Docker 控制错误的归类。** 建议把 `snapshot_error` 以 `DockerUnavailable` 开头的运行，以及 grader 在测试执行之前就报的超时，归为 infra_error，走现有的重跑规则。另外可以考虑为 Docker 控制调用加重试。是否需要降低 `PARALLEL` 也请一并决定；按冻结规则，B0 和 B2 的 `PARALLEL` 必须相同。
4. **预算。** 按目前的速度，B0 会超过 80 元的软上限。重跑那 22 次还会再增加大约 12.5 元。

停在这里等审计。没有修改任何运行时代码，没有看 B2，也没有开始 B2。coding-agent 侧继续等 `main-b0-runs.json`。

### 修订 2 执行记录：G1–G7、canary 与全量 B0（停止）

**结论：G1–G7 全部完成。预检 56/56，工具冒烟 56/56。4 道 canary 全部通过。全量 B0 在 django-16527 r2 触发"grader 报 missing"停止条件。** 这次 missing 是候选改动自己造成的：agent 编辑后的 `django/contrib/admin/views/main.py` 有 `IndentationError`，测试模块导入失败，7 个 id 一个都没收集到。grader 和编辑工具都工作正常。

停止时的状态：

- 共 38 份 summary，其中 36 个正式槽位、2 个已退役的 infra 槽位；
- `harness_tool_errors` 合计 0；Docker 重试 4 次，全部在第一次重试后成功；
- 花费 24.055 元；
- 没有生成 `main-b0-runs.json`，没有看 B2，也没有开始 B2。

#### G1–G7 提交与对已完成运行的影响

| 项 | 提交 |
| --- | --- |
| 6B-FIX 文档入库 | `37c5bde` |
| G1 容器代码兼容 3.6，加 py_compile 测试 | `ef32056` |
| G2 预检加工具冒烟 | `074a076` |
| G3 Docker 控制重试与 infra_error 归类 | `e4b919a` |
| G4 `harness_tool_errors`、停止条件与 canary 检查 | `040a7a8` |
| G5 `PARALLEL=3`，110 / 220 元 | `d002f27` |
| G6 作废 25 次运行（脚本） | `53600b9` |
| G7 冻结修订 2，tag `a5-main-freeze-r2` | `2f28232` |

以上改动都在修订 2 的第一次运行之前提交。修订 2 之前的 25 次运行按 G6 全部作废，移到了 `runs/a5-main-void/r1-tool-py36/`。所以这些提交不影响任何有效运行。全量测试 377 passed、199 skipped；G1 的 3.6 编译测试和 3.6 工具执行测试这一轮都实际跑过，没有被跳过。

本轮没有用到"核对口径可以自行修正"的授权，没有任何核对口径改动。

#### 需要审计确认的实现选择

以下几处是我对 6B-FIX 文字的理解，已经写进冻结修订 2：

1. **G3 里的"exec 启动"**：我理解为经过 `_ok` 的 exec，包括启动时的导入/复制/链接、快照，以及 grader 的 APPLY、上传 runner、读 receipt。agent 工具命令本身的 `docker exec` 不重试，因为命令可能已经执行了一部分，不能安全重放。这类失败如果把容器关掉了，就没有候选快照，记 `infra_error`，不会按空补丁评分。本轮两次 infra_error 都属于这种情况，见下文。
2. **"候选快照失败一律 infra_error"**：`snapshot_error` 非空一律按这一条处理，包括 `container_gone_before_snapshot`、`delta_too_large`，以及因为 OOM（exit 137）容器被关闭的情况。其中 `delta_too_large` 和 OOM 可能是 agent 自己造成的，本轮都没有出现。
3. **不重试的失败**：容器里 harness 脚本自己报 traceback，以及 `delta_too_large`。这两种是程序结果，不是 Docker 控制错误。
4. **`harness_tool_errors` 的口径**：只统计 harness 提供程序的工具；最后一个异常是实现类异常；参数符合 schema。详见冻结修订 2。这个口径在作废的 25 次运行上算出 109 次，和人工统计一致。

#### 预检（G2）

56/56 通过，工具冒烟 56/56。按镜像 Python 分：3.6 15/15，3.8 2/2，3.9 38/38，3.11 1/1。容器里实际的版本分别是 3.6.15、3.8.20、3.9.25、3.11.16。报告在 `runs/a5-main-logs/preflight.json`，日志在 `preflight-r2.log`。

#### canary

每个镜像 Python 版本各一道，按 `created_at` 取下中位，跑在 `2f28232` 上，并发 3。检查脚本是 `scripts/sprint6_canary.py check`，结果在 `runs/a5-main-logs/canary-check.json`。

| Python | 题 | 结果 | 模型调用 | 花费 | harness_tool_errors | Docker 重试 |
| --- | --- | --- | --- | --- | --- | --- |
| 3.6 | sklearn-14053 | 未解出 | 40 | 0.875 | 0 | 0 |
| 3.8 | django-13964 | 未解出 | 32 | 0.494 | 0 | 0 |
| 3.9 | pytest-7490 | 未解出 | 40 | 0.627 | 0 | 0 |
| 3.11 | django-16527 | 未解出 | 40 | 0.589 | 0 | 0 |

4/4 通过全部检查项：

- `mock: false`、`profile: b0-v2`、`answer_isolation_pass: true`；
- grader id 和校准一致，没有 `missing`，没有 grader reason；
- 花费等于 CNY 账本；
- 没有 infra_error；
- `harness_tool_errors == 0`。

`read_file`、`list_dir`、`search_code` 的调用全部成功。另外记一个观察：4 道 canary 都没有调用编辑工具。按规则，没有据此做任何调整。

#### 全量 B0 停在哪里

`run_a5_main.py --phase b0` 从 22:29 开始，到 23:16 退出，续用了 4 个 canary r1。新启动 32 次运行后，django-16527 r2 的 grader 报告 7 个 id 全部 `missing`。runner 停止开新运行，等在跑的运行结束后退出，报告显示 `started: 32`、`not_started: 132`，日志在 `runs/a5-main-logs/b0-r2.log`。

django-16527 r2 的排查结果：

- 候选改动只改了 `django/contrib/admin/views/main.py`，第 267–277 行把一段 `if v is None: … else: p[k] = v` 在 `return` 之后又插了一遍，第 273 行报 `IndentationError: unexpected indent`。
- grader 的 runner 导入 `tests/admin_views/test_templatetags.py` 时失败，所以一个测试都没收集到，receipt 里的 `runner_error` 记下了完整 traceback，`receipt_complete` 为 false。
- 编辑工具没有问题：用原始文件按顺序重放这次运行的 4 次 `search_replace`，得到的文件和导出的候选文件逐字节相同。错误完全来自模型写的替换文本。
- 同一道题的 r1（canary）和 r3 都正常收集到了 7 个 id。

按冻结规则，"grader 报 missing"是停止条件，不区分原因，所以停在这里。

#### infra_error、Docker 重试、delta_lost

| 运行 | 情况 | 处理 |
| --- | --- | --- |
| django-12276 r1（第一次） | 一次 `read_file` 的 `docker exec` 回收超时（`cleanup_failed`），容器被关闭，没有候选快照 | `infra_error`，退役为 `r1.infra1`，重跑 |
| django-15973 r2（第一次） | 一次 `search_code` 出现同样的情况 | `infra_error`，退役为 `r2.infra1`，重跑 |

infra_error 共 2 次，没有达到 ≥3 的停止线。两次都没有送 grader，没有按空补丁评分。

Docker 控制重试共 4 次，每次都在第一次重试（等 2 秒）后成功：

| 时间 | 运行 | 阶段 | 操作 | 错误 |
| --- | --- | --- | --- | --- |
| 22:33:51 | django-11211 r2 | grader | rm | `TimeoutError` |
| 22:45:21 | django-13109 r1 | run | snapshot | `ConnectionResetError` |
| 22:50:12 | django-13512 r1 | run | snapshot | `ConnectionResetError` |
| 23:07:28 | django-15499 r3 | run | rm | `TimeoutError` |

13109 r1 和 13512 r1 这两次快照错误，在修订 2 之前会被当成空补丁评分；现在重试后拿到了正常的候选改动。

`delta_lost` 共 3 次（django-12276 r1、13109 r3、14434 r1），都是模型调用 `search_replace` 时 `search` 和 `replace` 完全相同，文件内容没有变化，差异为空是正确的。这是原有的分类规则，不是停止条件。

#### 6a 要求的统计（截至停止）

| 项 | 值 |
| --- | --- |
| 有效 B0 运行 | 36（canary 4 次 + 全量 32 次）；另有 2 个 infra 槽位已退役 |
| 解出 | 0/36：django 0/33，pytest 0/1，sklearn 0/1，sympy 0/1 |
| 每题 k/3（跑满 3 次的 11 道 django 题） | 0/3：11 道 |
| 有改动的运行 | 16/36；F2P 通过数都没有超过空补丁基线；P2P 全部保持通过，只有 16527 r2 是 0/6 |
| infra_error | 2 次，都已重跑 |
| Docker 控制重试 | 4 次，时间见上表 |
| `harness_tool_errors` 合计 | 0 |
| 花费 | 24.055 元，平均每次 0.633 元 |
| 平均模型调用 | 38.0 |
| 停止原因 | `max_model_calls` 25，`completed` 11，`candidate_snapshot_failed` 2；总时限超时 0；grader 超时 0 |
| `main-b0-runs.json` sha | 没有生成 |

#### 需要审计决定

1. **候选改动自己破坏了测试收集时，missing 是否还算停止条件。** 这次 grader 和工具都没有问题，是模型写出了不能导入的代码。建议的规则是：如果 receipt 的 `runner_error` 或收集错误的 traceback 指向本次候选改动里的文件，就把这次运行记为普通失败（solved=false），不停止；其他 missing 照常停止。这是运行时规则的改动，我没有实施。django-16527 r2 的去留也请一并决定：是按普通失败保留，还是另作处理。
2. **预算。** 目前平均每次 0.633 元，168 次加上重跑大约 107 元，很接近 110 元的软上限，可能在 B0 的最后几次运行时触发停止。
3. **0 解出。** 36 次都没有解出，其中 33 次是 django。本轮检查过的几处都没有发现 harness 的问题：
   - 工具冒烟 56/56 通过，`harness_tool_errors` 为 0；
   - grader 确实加载了候选改动（16527 r2 的导入失败就是证据）；
   - 有改动的运行里，P2P 都保持通过。

   按规则，我没有因为这个结果调整题目、profile 或卡片。

停在这里等审计。没有看 B2，也没有开始 B2。coding-agent 侧继续等 `main-b0-runs.json`。

### 修订 3 执行记录：H1–H9、canary 与全量 B0（完成）

**结论：H1–H9 全部完成。预检 56/56，其中 prompt 内容检查 56/56，dev prompt 14/14 逐字节一致。5 道 canary 全部通过。全量 B0 跑完，没有触发任何停止条件，故障警报也没有触发。总解出率 115/168 = 68.5%，高于 10% 的 B2 启动阈值。** 已生成 `docs/sprint/main-b0-runs.json`。按指示停在这里：没有看 B2，也没有开始 B2。

#### 每个 repo 的解出率

| repo | 解出 / 运行 | 解出率 |
| --- | --- | --- |
| django | 24 / 33 | 72.7% |
| pytest | 29 / 36 | 80.6% |
| scikit-learn | 26 / 30 | 86.7% |
| sphinx | 20 / 33 | 60.6% |
| sympy | 16 / 36 | 44.4% |
| **合计** | **115 / 168** | **68.5%** |

预注册的"低于 B2 启动阈值"条件（总解出率低于 10%）不成立。不含 5 次 canary 时是 110/163。

#### H1–H9 提交与对已完成运行的影响

| 项 | 提交 |
| --- | --- |
| 6C-FIX 文档入库 | `047df42` |
| H1 补齐 issue 文本，materialize 改读 public 文件 | `6a21da4` |
| H2 静默回退改为报错，加测试 | `2dddb2b` |
| H3 预检检查 prompt 内容和 dev prompt 一致性 | `b0d25be` |
| H4 summary 加 `issue_sha256`/`prompt_sha256`，canary 按 repo 选并检查 issue sha | `f1b1f8c` |
| H5 故障警报 | `dc61377` |
| H6 候选改动导致的 missing 记普通失败 | `1133112` |
| H7 作废 38 个运行目录（脚本） | `7d768b9` |
| H8 120 / 230 元 | `60fd926` |
| H9 冻结修订 3，tag `a5-main-freeze-r3` | `1707d23` |

以上改动都在修订 3 的第一次运行之前提交。修订 3 之前的 38 个运行目录按 H7 全部作废，所以这些提交不影响任何有效运行。H7 的移动结果：

- 36 个正式槽位、2 个 infra 槽位和 `b0-report.json` 移到了 `runs/a5-main-void/r2-no-issue/`，那里有 README 和 `void-runs.json`；
- 38 个目录记录的 user prompt 全部是 `Public issue for <id>` 占位；
- 作废成本 24.055 元，不计入实验。

全量测试 412 passed、199 skipped。

**H2 改为报错的位置**（冻结修订 3 里有同样的表）：

- `run_a5_main.materialize_runner_task`：
  - 原来的 issue 占位回退，改为读 public 文件；文件缺失、`issue_text` 为空、sha 与 `main-issues.json` 不一致、`repo_ref` 与目标不一致都报错；
  - 私有文件的 `test_patch`、`patch` 为空时报错。
- `run_swe_task.public_issue`：
  - `issue_text` 为空、只有空白或以 `Public issue for ` 开头时报错；
  - `repo_ref` 缺 `repo_id` 或 `revision` 时报错；
  - 测试命令按 family 查表，查不到就报错。原来是"不是 django 就用 pytest 命令"。
- `run_swe_task.run_task` 卡片插件里的两处 issue 回退，改用同一个严格的 `issue_text()`。
- `run_swe_task.grader_spec`：`test_patch_paths`、`gold_patch_paths` 为空时报错；`grader_timeout_seconds` 不再默认 300，必须给出。

检查过但保留的 `or` 默认值都不在 prompt、任务或 grader 输入上，清单见冻结修订 3。

#### 预检（H3）

`runs/a5-main-logs/preflight.json` 的结果：

- 56/56 通过；
- 工具冒烟 56/56；
- prompt 检查 56/56，每道题都原样包含 issue，issue sha 与 `main-issues.json` 一致，不含私有字段；
- dev prompt 14/14 与 `runs/sprint4-b0-v2/<id>/r1/events.jsonl` 记录的 user prompt 逐字节一致。

56 道合格题的 issue 字符数：最小 190，中位 1498.5，最大 22778。

#### canary

每个 repo 各一道，按 `created_at` 取下中位，跑在 `1707d23` 上，并发 3，共花费 1.733 元。结果在 `runs/a5-main-logs/canary-check.json`。

| repo | 题 | 结果 | 模型调用 | 花费 | harness_tool_errors | Docker 重试 |
| --- | --- | --- | --- | --- | --- | --- |
| django | django-13964 | 解出 | 37 | 0.483 | 0 | 1 |
| pytest | pytest-7205 | 解出 | 37 | 0.529 | 0 | 2 |
| scikit-learn | sklearn-13142 | 解出 | 7 | 0.066 | 0 | 1 |
| sphinx | sphinx-8593 | 解出 | 35 | 0.457 | 0 | 1 |
| sympy | sympy-16766 | 解出 | 21 | 0.198 | 0 | 0 |

5/5 通过全部检查项：

- 原有各项；
- `harness_tool_errors == 0`；
- 没有 infra_error；
- `issue_sha256` 等于 `main-issues.json`，并且有 `prompt_sha256`。

Docker 重试都在第一次重试后成功。

每道 canary issue 的前 200 个字符（原样，`\r\n` 是数据集原文里的换行）：

- django-13964（`d0a164326a7b…`）：`Saving parent object after setting on child leads to data loss for parents with non-numeric primary key.\nDescription\n\t \n\t\t(last modified by Charlie DeTar)\n\t \nGiven a model with a foreign key relation `
- pytest-7205（`088371cacf19…`）：`BytesWarning when using --setup-show with bytes parameter\nWith Python 3.8.2, pytest 5.4.1 (or latest master; stacktraces are from there) and this file:\r\n\r\n```python\r\nimport pytest\r\n\r\n@pytest.mark.para`
- sklearn-13142（`09d29f40006e…`）：`GaussianMixture predict and fit_predict disagree when n_init>1\n#### Description\r\nWhen `n_init` is specified in GaussianMixture, the results of fit_predict(X) and predict(X) are often different.  The ``
- sphinx-8593（`d7a0b222ecda…`）：`autodoc: `:meta public:` does not effect to variables\n**Describe the bug**\r\nautodoc: `:meta public:` does not effect to variables.\r\n\r\n**To Reproduce**\r\n\r\n```\r\n# example.py\r\n_foo = None  #: :meta publi`
- sympy-16766（`c71bac3070c6…`）：`PythonCodePrinter doesn't support Indexed \nI use `lambdify()` to generate some functions and save the code for further use. But the generated code for `Indexed` operation has some warnings which can b`

#### 全量 B0

`run_a5_main.py --phase b0` 从 01:35 跑到 04:41，续用了 5 个 canary r1。报告如下：

- `started: 163`、`not_started: 0`、`halt_reason: null`；
- 花费 55.774 元，低于 120 元的 B0 软上限；
- `main-b0-runs.json` sha（`handoff_sha256`）为 `5c42a406c35a94c80dc7163a061e7383a66609b6c28ebaf7bd0c2fa19f92eb9e`。

统计脚本是 `scripts/sprint6_b0_stats.py`，输出在 `runs/a5-main-logs/b0-stats.json`。

| 项 | 值 |
| --- | --- |
| 有效 B0 运行 | 168（56 题 × 3，全部跑满）；另有 2 个 infra 槽位已退役 |
| 解出 | 115/168 = 68.5%（各 repo 见上表） |
| 每题 k/3 | 3/3：34 道；2/3：4 道；1/3：5 道；0/3：13 道 |
| status | pass 115，fail 35，partial 14，delta_lost 4 |
| 停止原因 | `completed` 121，`max_model_calls` 46，`model_parse_error` 1 |
| infra_error | 2 次，都已重跑 |
| Docker 控制重试 | 72 次，全部在第一次重试后成功：rm 31，snapshot 30，start 5，create 3，exec 2，ps 1；run 阶段 53 次，grader 阶段 19 次 |
| `harness_tool_errors` 合计 | 0 |
| grader 报 missing | 0 次；`grader_candidate_error` 0 次；grader reason 0 次 |
| issue sha 与 `main-issues.json` 不一致 | 0 次 |
| 模型 | 全部是 `deepseek-flash` @ `api.deepseek.com`，没有变化 |
| 花费 | 55.774 元，平均每次 0.328 元 |
| 平均模型调用 | 23.6 |
| 有改动的运行 | 159/168 |

各档题目：

- 0/3 的 13 道：
  - django-13512、15973；
  - pytest-5840、7324；
  - sklearn-12973；
  - sphinx-10614、7590、9461；
  - sympy-13091、14248、15599、20428、21596。
- 1/3 的 5 道：django-15022，sphinx-8120、9258，sympy-19040、23950。
- 2/3 的 4 道：django-13964，pytest-7490，sklearn-10908，sympy-11618。

**infra_error：**

| 运行 | 情况 |
| --- | --- |
| sklearn-14710 r1（第一次） | `container cleanup failed`，退役为 `r1.infra1`，重跑 |
| sympy-14248 r2（第一次） | `candidate snapshot failed: container_gone_before_snapshot`，退役为 `r2.infra1`，重跑 |

共 2 次，没有达到"满 3 次且超过 10%"的停止线。

**delta_lost 4 次：** django-13964 r2、django-15022 r2、sphinx-8120 r2、pytest-5840 r3。这 4 次都用满了 40 次模型调用，`snapshot_error` 为空。这是原有的分类规则，不是停止条件。我没有逐次核对它们是不是像修订 2 那样属于 `search == replace` 的空编辑。

**单次运行的 CNY 硬上限：** 日志里有一行 `LLM call failed: CNY hard cap would be exceeded`。它来自 sympy-15599 r3：

- 这次运行累计花了 0.937 元，下一次调用的预留会超过账本里每次运行 1.000 元的硬上限，于是调用被拒绝，运行结束；
- 随后按正常流程送 grader，结果是 fail；
- summary 的 `stop_reason` 记成了 `model_parse_error`。这个标签不准确，但它属于运行时的分类，我没有改，只在这里记录。

这个每次运行的上限是冻结前就有的设置，不是本轮新加的，也不是停止条件。

#### 核对口径

本轮没有用到"核对口径可以自行修正"的授权，没有任何核对口径改动。

#### 需要审计确认的实现选择

以下几处是我对 6C-FIX 文字的理解，已经写进冻结修订 3：

1. **H3 的"不含私有字段内容"：**
   - gold patch、test patch、F2P/P2P 原始列表都不能出现在整个 prompt 里；
   - 单个 F2P/P2P id 不能出现在 prompt 的模板部分（去掉末尾原样 issue 后的部分）；
   - 有 3 道题的单个 id 本来就出现在数据集的公开 issue 里：sympy-15599 的 `test_Mod`，pytest-5262 和 pytest-7521 的 `[100%]`。这 3 处只记录，不算泄露。
2. **H6 需要新增一个 grader 诊断字段：**
   - 原来的 `collection_errors` 是 JSON 字符串，而且只保留前 2048 个字符，最内层的栈帧可能被截掉；
   - 所以新增了只在宿主机上保存的 `collection_error_tails`（每条 traceback 保留最后 2048 个字符），原有字段不变，也不影响评分；
   - canary 检查里的"grader reported missing ids"也按 H6 同样放行；
   - 本轮没有出现任何 missing，所以这条规则没有实际用上。
3. **H5 的"正式运行"：** 不含 `r<k>.infra<n>` 退役槽位和 `infra_error`，包括 delta_lost。全量 B0 的前几批运行里就已经有解出，警报没有触发。
4. **H1 的数据集版本：**
   - 当前环境里没有安装 HF `datasets`，所以用 `huggingface_hub` 下载了固定 revision `c104f840…` 的 parquet，读取后按原规则重新选题；
   - 60 个 id、顺序、repo 和 base_commit 全部一致，才写文件；
   - dev 14 题里只有 2 道在 Verified 中，它们的 dev issue 与数据集逐字节相同；另外 12 道不在 Verified 里，但 H3 的 dev prompt 检查 14/14 一致。

B0 已经完成，结果文件已经交接给 coding-agent 侧（`main-b0-runs.json`）。按指示没有看 B2，也没有开始 B2，停在这里等审计。

### 6D 第 A 段执行记录：D1–D4（完成）

**交接文件 v2 已就绪。** 新交接文件是 `docs/sprint/main-b0-runs.json`（schema `sprint6.main-b0-runs.v2`），sha（`handoff_sha256`，LF）为：

`fe0f47b8df67730a0335d7109631dc09bc4d6b5d19a601acfec0963f5dcb1f8c`

旧文件保留为 `docs/sprint/main-b0-runs.v1.json`（sha `5c42a406c35a94c80dc7163a061e7383a66609b6c28ebaf7bd0c2fa19f92eb9e`）。冻结修订 4 已写入 `A5-MAIN-FREEZE.md`，tag `a5-main-freeze-r4` → `074219c`。

本段没有调用真实模型，花费 0 元；没有看 B2，也没有开始 B2。

#### 提交与对已完成运行的影响

| 项 | 提交 | 对已完成运行的影响 |
| --- | --- | --- |
| D1 交接文件 v2（`run_a5_main.py --handoff`） | `614ebce` | 无。只读取已有的 r1..r3 summary 和 grader 结果，重新写交接文件；168 次运行的 v1 字段与 v1 文件逐项相同 |
| D2 delta_lost 归类脚本 `scripts/sprint6_delta_lost.py` | `1c6498b` | 无。只读事件日志，分类规则不变 |
| D3 漂移对照臂 `--with-b0-drift` | `9d1a438` | 无。只影响以后的 `--phase b2`；`halt_reason` 拆出 `run_checks`，`--phase b0` 的检查项和顺序不变 |
| D4 冻结修订 4 | `074219c` | 无 |

#### D1 交接文件 v2

- 每次运行新增 `answer_isolation_pass`、`base_commit`、`grader_status`、`run_dir`、`public_task`、`issue_sha256`。
- 168 次运行：`answer_isolation_pass` 全部为 true；`grader_status` pass 115、fail 39、partial 14；`issue_sha256` 全部等于 `main-issues.json`。
- 只读 `b0/r1..r3`，不读 `r4` 和 `.infra<n>`；有测试确认 r4 和 infra 槽位不会进入交接文件。

#### D2 4 次 delta_lost 的归类（只做描述）

做法：用 `runs/sprint5-main-images/<id>/staging/original` 里的原始文件，按顺序重放每次运行的编辑调用，得到被编辑文件的状态序列（O 表示与原始文件相同，A、B 表示不同的改动版本）；再检查 `run_command` 里有没有写入 workspace 的命令。

| 运行 | 分类 | 编辑次数 | 文件状态序列 |
| --- | --- | --- | --- |
| django-13964 r2 | agent 自己撤回了改动 | 16 | O→A→O，重复 8 次 |
| django-15022 r2 | agent 自己撤回了改动 | 16 | O→A→O，之后 O→B→O 重复 7 次 |
| sphinx-8120 r2 | agent 自己撤回了改动 | 10 | O→A→O，重复 5 次 |
| pytest-5840 r3 | `search == replace` 的空编辑 | 3 | 3 次编辑的 search 与 replace 都相同，文件一直是 O |

合计：撤回 3 次，空编辑 1 次，其他 0 次。4 次运行的共同点：

- 每次编辑工具都返回"文件已更新"；
- 最终文件与原始文件逐字节相同，所以 delta 为空；
- 没有通过 `run_command` 写入 workspace 的命令；
- 都用满了 40 次模型调用（`stop_reason` 为 `max_model_calls`）。

三次撤回的运行都是 agent 改完文件、跑测试或检查后，再用编辑工具把改动改回原样，然后又改一遍，如此循环，直到用完调用次数，停下时恰好处在撤回之后的状态。这只是描述，delta_lost 的分类规则没有改。

#### D3 漂移对照臂

- `--phase b2 --with-b0-drift`：168 个 B2 槽位加 56 个 `b0/r4` 槽位，先按规范顺序排序，再用种子 20260929 打乱，`PARALLEL` 仍为 3。
- 56 道合格题的完整队列共 224 个槽位，队列指纹 `db6809a1…`（完整值和计算方法见冻结修订 4）。
- r4 用同一个 profile 和 B0 变体，不带卡片；不进入交接文件，不参与卡片构建和主要分析。
- 续跑、infra 重跑和停止条件对 r4 同样适用；花费按 `TOTAL_CAP` 230 元停止。
- 新增 5 个测试，并沿用 D1 的"交接文件不含 r4"测试。

#### 测试

全套测试 420 passed，199 skipped（修订 3 时是 412 passed；新增 D1 的 3 个测试和 D3 的 5 个测试）。

#### 需要审计确认的实现选择

1. **r4 的停止条件：** infra_error 停止线（满 3 次且超过 10%）对 b2 和 b0 分别计算，不合并；其余逐次运行的检查（harness 工具错误、隔离、missing、grader 崩溃）对两个阶段的全部运行都做。故障警报只针对 `--phase b0`，B2 阶段不检查。
2. **花费上限：** 混合队列里 r4 的花费和 B2 一起计入 `runs/a5-main/` 总额，按 `TOTAL_CAP` 230 元停止，不再单独套用 B0 的 120 元软上限。

按第 A 段的要求，停在这里，通知 coding-agent：交接文件 v2 已就绪，可以构建 v6 卡片。没有开始 B2，也没有做第 C 段。

### 6D 第 C 段执行记录：D5–D8（B2 停止）

**结论：B2 在 django-13964 的 B2 r3 触发了原有停止条件"grader reported missing ids"，停在这里等审计。** 已完成 B2 115/168 次、`b0/r4` 38/56 次，未启动的有 71 个槽位（B2 53 个，r4 18 个）。实际注入与预测注入 115/115 一致。本段累计花费 54.208 元（B2 41.947 元，r4 12.261 元），`runs/a5-main/` 总额 109.982 元，低于 `TOTAL_CAP` 230 元。

按 D8 要求：没有计算 B2 相对 B0 的差异，没有下结论，本节也不报告 B2 或 r4 的解出率。

#### 提交与对已完成运行的影响

| 提交 | 内容 | 对已完成运行的影响 |
| --- | --- | --- |
| `068380e` | B2 故障警报（审计纠正第 2 条，新增停止条件） | 无。第一次 B2 运行之前提交 |
| `f97284c` | D5 v6 manifest 核对 | 无 |
| `89ef367` | D6 预测注入表和脚本 | 无 |
| `8008223` | D7 注入一致性停止条件，要求预测表已提交 | 无 |
| `399132a` | D7 核对修正：事件类型字段是 `event_type`，不是 `type`（mock 检查中发现） | 无。真实 B2 开跑之前 |
| `5c0c6b5` | 冻结修订 4 补记 | 无 |
| `505d730` | D8 统计脚本 `scripts/sprint6_b2_stats.py`（只读） | 无 |
| `a75303a` | D7 核对修正：读取存成 session 附件的 `context.prepared` 负载（见下） | 不改变任何运行结果。它导致了 B2 的第一次停止（误停），修正后重新核对已完成的 25 次 B2，全部一致，然后续跑 |

两处 D7 修正都只改核对代码，属于"纯核对口径差异可以自行修正"的授权范围，没有改动运行时行为。

#### D5 v6 核对

`memory-cards-v6.manifest.json` 的三项都一致，B2 每次启动时都会重新检查：

- `status: final`；
- `build_inputs.handoffs` 包含 dev 交接文件（`98482670…`）和 `main-b0-runs.json` v2（`fe0f47b8…`），与当前文件一致；
- `cards_sha256` 复算为 `3416eb9d8f6119081330fb3b0a2d612b8fde4678d6ec1c73a7fc681cedfcfc70`，70 张卡（`validated_fix` 50 张，`failed_attempt` 20 张）。

#### D6 预测注入表

`docs/sprint/b2-predicted-injection.json`，sha（LF）为 `5d858eb4f3ab368fc655b310168e2c77de311ddfee4f77c0928e4d08ba79e3e5`，在第一次 B2 运行之前以 `89ef367` 提交。

- 51/56 道题会注入至少 1 张卡，高于 10 道的停止线；共 148 张次，注入的题平均 3236.2 字节。
- 不注入的 5 道：sympy-11618、sympy-13757、sympy-14248、sklearn-9288、sphinx-7440，插件结论都是 `no_relevant_memory`。

**gold 行重叠（描述统计）：**

- 做法：对每道注入卡片的题，统计目标题 gold patch 的新增行（去掉首尾空白、跳过空行）里，有多少行与注入卡片文本中的某一行完全相同。另外单列长度不少于 10 个字符的行。
- 结果：51 道注入卡片的题都是 0 行，不论是全部行还是长度不少于 10 个字符的行。
- 抽查卡片文本：卡片写的是修法说明、文件和行号范围、测试命令和 issue 摘要，不含代码行，所以和 gold 新增行没有逐行重叠。
- 这个统计只按行做完全匹配，没有检查卡片的说明文字在语义上是否透露了修法。

#### D7 运行情况

命令：`run_a5_main.py --phase b2 --with-b0-drift --cards <coding-agent>/benchmarks/a5/memory-cards-v6.jsonl`。队列、种子、并发与冻结修订 4 一致。

**第一次停止（误停，已修正）：** 第一次运行在 13:25 前后停在 sklearn-14710 的 B2 r2，理由是实际注入为空、预测是 4 张卡。

- 这次运行注入了 4 张卡，第 0 步的 `context.prepared` 负载有 17390 字节，事件库把它存成了 `session/artifacts/<sha>`，`events.jsonl` 里只留下 `artifact_ref`。
- D7 检查只读了内联的负载，所以误判为空。
- 附件的 sha 与引用一致，内容显示第 0 步实际注入了 sklearn 9288、14053、14496、12585 共 4 张卡，id 和字节数与预测相同，没有被拒绝，也没有插件错误。
- `a75303a` 改为读取附件并校验 sha，附件缺失或 sha 不符时仍然停止。修正后重新核对已完成的 25 次 B2，全部一致，然后续跑。日志在 `runs/a5-main-logs/b2-full-stop1.log`。

**第二次停止（本次）：** 续跑新启动 118 次运行（B2 90 次、r4 28 次）后，django-13964 的 B2 r3 报告 37 个 id 全部 `missing`。runner 停止开新运行，等在跑的运行结束后退出。日志在 `runs/a5-main-logs/b2-full.log`。

- 这是 r3 槽位的第二次尝试：第一次是 `container cleanup failed`，已退役为 `r3.infra1`。
- 候选改了 `django/db/models/fields/related_descriptors.py`，以及 `tests/many_to_one/models.py`、`tests/many_to_one/tests.py`（两个测试文件都会被测试补丁覆盖）。
- 候选删掉了 `ForwardManyToOneDescriptor.__set__` 里给外键字段赋值的 `else` 分支，还给 `ForeignKeyDeferredAttribute` 加了一个 `__get__`（旁边留着两行 `# TEMP_REVERT` 注释）。
- grader 正常执行测试。`ManyToOneTests.setUpClass` 在 `setUpTestData` 的第一个 `save()` 就报 `ValueError: Cannot force an update in save() with no primary key.`，整个测试类 0 个测试运行，所以 1 个 F2P 和 36 个 P2P 都是 missing。
- H6 规则只读 grader 的 `runner_error` 和 `collection_error_tails`。这次两者都为空：37 个 id 都收集到了，错误发生在执行阶段的 `setUpClass`，只出现在 `execution_stderr_tail` 里。所以 `grader_candidate_error` 为空，按原规则停止。
- 即使对 `execution_stderr_tail` 也按 H6 取最内层的项目栈帧，结果是 `/workspace/django/db/models/base.py`，候选没有改这个文件，同样不会放行。
- 我的判断：这是候选改动引起的失败，不是 harness 或 grader 的故障。但现行规则不覆盖这种情况：错误发生在执行阶段，出现在未修改的文件里，根因在候选改过的文件里。怎么处理需要审计决定。

**完成情况：**

| 项 | B2 | `b0/r4` |
| --- | --- | --- |
| 应跑槽位 | 168 | 56 |
| 已完成（不含 infra） | 115 | 38 |
| 未启动 | 53 | 18 |
| 3 次都跑完的题 | 16 | — |
| infra_error（都已退役重跑） | 2：django-13964 r3（容器清理失败）、pytest-5631 r1（快照前容器消失） | 2：sklearn-12585 r4（Docker 控制输出超限）、sphinx-7910 r4（快照前容器消失） |
| Docker 控制重试 | 21 次 | 9 次 |
| `harness_tool_errors` | 0 | 0 |
| grader 报 missing | 1 次（django-13964 r3，本次停止） | 0 |
| `grader_candidate_error` | 0 | 0 |
| 隔离失败 | 0 | 0 |
| 停止原因 | `completed` 79，`max_model_calls` 35，`model_parse_error` 1 | `completed` 27，`max_model_calls` 11 |
| 花费 | 41.947 元，平均每次 0.359 元 | 12.261 元，平均每次 0.307 元 |
| 平均模型调用 | 24.8 | 23.5 |

- infra_error 共 4 次，B2 和 r4 分开计算，都没有达到"满 3 次且超过 10%"的停止线。
- 模型全部是 `deepseek-flash` @ `api.deepseek.com`，profile 全部是 `b0-v2`；B2 的变体全部是 B2，r4 全部是 B0。
- 故障警报：B2 正式运行已超过 30 次，其中有解出，没有触发。
- B2 的 1 次 `model_parse_error` 是 sklearn-9288 r2：累计花了 0.923 元，下一次调用会超过单次 1 元的硬上限，被拒绝后记成了这个标签。情况和 B0 的 sympy-15599 r3 相同，不是停止条件。

#### 预测注入与实际注入的一致性

- 已完成的 115 次 B2 全部核对，115 次一致，0 次不一致。核对的是事件日志里实际注入的卡片 id 集合，包括存成附件的负载。
- 每张实际注入卡片的字节数和 sha256 都与预测表一致。
- summary 里记录的预览注入（id 和字节数）也都与预测表一致。
- 每张卡在每次运行中只注入一次，没有日志不可读的运行。

#### 注入统计（已完成的 115 次 B2）

- 注入至少 1 张卡的题：51 道，就是预测会注入的全部 51 道，每道至少跑了 1 次。
- 注入至少 1 张卡的运行：105 次；其余 10 次属于预测不注入的 5 道题。
- 注入的运行平均 2.93 张卡、3308.7 字节。

#### 全量检查

对 115 次 B2 实际注入的每张卡，按卡片自己的 `repo`、`created_at` 与 `main-targets.yaml` 里目标题的 repo、`created_at` 核对：

- 没有晚于或等于目标题日期的卡；
- 没有目标题自己的卡；
- 没有跨 repo 的卡。

预测表对 56 道题做同样的检查，结果也是 0。

#### 测试

全套测试 435 passed，199 skipped。

#### 需要审计决定

1. **django-13964 B2 r3 如何处理。** 可选的做法：
   - 按现行规则把它记作 grader 停止，维持现状；
   - 扩展 H6：也读 `execution_stderr_tail`，并把判据放宽到"任意一个项目栈帧落在候选改过的文件里"。这一次栈帧里有 `tests/many_to_one/tests.py`，候选改过它，但 grader 用的是测试补丁覆盖后的版本，所以按这个判据放行也不严谨；
   - 或者另定口径。

   这属于规则改动，我没有做。
2. **B2 续跑。** 审计决定后，用同一条命令续跑。已完成的 115 次 B2 和 38 次 r4 会被跳过，并重新核对注入。

没有看 B2 相对 B0 的结果，也没有计算差异。停在这里等审计。

**通知 coding-agent：** B2 已停止，D8 报告就绪。现有数据是 B2 115/168、`b0/r4` 38/56，不完整；运行目录在 `runs/a5-main/`，统计在 `runs/a5-main-logs/b2-stats.json`，预测注入表是 `docs/sprint/b2-predicted-injection.json`（`5d858eb4…`）。可以开始分析的准备工作；是否等 B2 续跑完成再做完整分析，由审计决定。
