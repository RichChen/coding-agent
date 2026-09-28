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
