# 第五轮审计节点

日期：2026-09-26 写初稿，2026-09-27 补上第 5 步结果，2026-09-28 补上全量重扫、django-7530 重跑和第 7 步 mock。本轮模型花费仍是 6.349 CNY，上限 10 CNY。没有打 `a5-main-freeze`，也没有进入 R6。

## 第 0 步

真实运行强制使用 clean image，不再看 profile 名。`--legacy-image` 只能和 `--mock` 一起用。

sklearn-11281 原来的 r2 是工件配额超出（16MB），不是 ACL，也不是宿主机磁盘满。旧目录留在 `runs/sprint4-b0-v2/scikit-learn__scikit-learn-11281/r2-storeerror`。会话工件上限改为 64MB。`StoreError` 记为 `infra_error`，不进解出率分母。

重跑的 r2 解出，33 次调用，`completed`，隔离通过，花费 0.478 CNY。11281 变为 2/3。42 次合计 18/42，14.522 CNY。这 0.478 算在第五轮里。

## 镜像方案

三道试用题的官方镜像扫描都是 0 命中。校准只有 django-10914 通过（空改动 F2P 0/1，gold 1/1）。sympy-11400 的 gold 没有写出收据。sklearn-10297 有 `.so`，镜像里没有 native artifact 依据，按规则报错。三道没有全部通过，题目池不用官方镜像。

决定用 `build_clean_baseline.py` 自建，安装命令读取 SWE-bench v4.0.4 的版本 specs。`main-targets.yaml` 的 `image_source` 是 `swebench-specs-v4.0.4`。已经拉下的 3 个官方镜像没有删除。

## 磁盘

2026-09-26 检查时数据盘还在 C 盘，空闲约 68GB，第 5 步因此停过。2026-09-27 迁移已经生效：C 盘的 `docker_data.vhdx` 不在了，引擎锁着 `E:\Docker\wsl\DockerDesktopWSL\disk\docker_data.vhdx`。当时 C 盘空闲约 120GB，E 盘约 688GB。没有删除 b0 镜像。

## 第 5 步

60 道都做了自建镜像、文件系统扫描和零模型校准。合格 56 道。没有因为难度或环境以外的原因换题。

2026-09-28 按全文件系统重新扫描了有镜像的 58 道。扫描不再跳过 `site-packages`，也不再只看 `/opt/repo`。和基础镜像同一路径、同一 sha256 的文件，以及和 pip `RECORD` 里记录的 sha256 相同的文件，记为误报并排除。58 道 `answer_isolation_pass` 仍是 true，合格数没有变。sklearn-25232 和 25973 没有镜像，没有可扫的对象。

每道校准 JSON 的 `nodeids` 记下了 F2P/P2P 的原始条数、实际送进 grader 的条数，以及丢弃原因。SymPy 一个名字对上多个测试文件时，实际条数会多于原始条数。两道没有建成镜像的 sklearn 题也记了过滤后的条数，并注明没有送进 grader。

django-7530 在这次扫描和条数记录之后重跑了空改动和 gold。结果仍是 `empty_f2p_did_not_fail`：空改动 F2P 1/1、P2P 59/59，gold 同样 1/1、59/59。没有换题。

| 仓库 | 合格 | 剔除 |
| --- | --- | --- |
| django/django | 11/12 | django-7530：空改动时 F2P 已经通过 |
| sympy/sympy | 12/12 | 无 |
| scikit-learn/scikit-learn | 10/12 | 25232、25973：官方 pin `numpy==1.19.2` 没有 Python 3.9 wheel，源码也不能用 Cython 3.0.10 编译 |
| sphinx-doc/sphinx | 11/12 | sphinx-8721：空改动时 F2P 已经通过 |
| pytest-dev/pytest | 12/12 | 无 |

明细在 `docs/sprint/MAIN-CALIBRATION.md` 和 `docs/sprint/main-calibration/`。

## 题目池

60 道。id 列表 sha256：`d4caaa48c5735b2bf1a302855bbf94a2cdb5ab0397dff152d5d839440a4b22dd`。选定之后没有换题。`sphinx-doc__sphinx-8721` 被抽中，已从 `HOLDOUT` 移除。其余 pilot 仍然拒绝。

交接文件是 `sprint5.memory-source-runs.v2`，sha256 `984826707e8f69ad9b900134bd244c6056f2d8860f3036a3606bfc60b4bcb450`。

## 第 6 步冒烟

v5 manifest 不是 final，用的是 v4 final，`created_at` 由交接文件补上。14 道 dev 题各一次 B2，花费 5.871 CNY。过滤前都是 14 张。注入字节最大 1500，低于 4096。当前题和更晚的卡片没有注入。sklearn-11281 的上下文里出现了 `scikit-learn__scikit-learn-11040`。sympy 四道和 pytest-5227 过滤后还有卡片，但都不是 `validated_fix`，实际注入是 0。这一步不和 B0 比较解出率。

## R6 估计

按设计仍是约 360 次、约 125 CNY、上限 150 CNY、串行 24–36 小时。合格题现在是 56 道，若只跑合格题则是 56×2×3 = 336 次。运行器是 `scripts/run_a5_main.py`。题目池 yaml 没有 dev 题的 `receipt`、`public_task` 和 `family`。走查时在 `runs/sprint5-main-runner/` 里生成这些文件，再走原来的 `run_task`。没有改 b0-v2 的 prompt、工具、预算和 grader 判定。

第 7 步第 3 项已做完：django-16527、sympy-11618、sklearn-14053，各 1 次重复，先 B0 再 B2，费用 0。mock 客户端回了一次停止响应，没有改代码，三道都未解出。交接文件是 `docs/sprint/main-b0-runs.json`，`scope` 为 `step7-mock`，只含这 3 道的 r1，不是 R6 交接。B2 用 v4 final 卡片。django-16527 过滤后剩 3 张更早的 validated_fix 卡，插件结论是 `no_relevant_memory`，注入 0。sympy-11618 过滤后剩 1 张更早的卡，不是 validated_fix，注入 0。sklearn-14053 过滤后剩 5 张，注入 10297（771 字节）和 11040（871 字节）。没有进入 R6。

本轮花费：重跑 0.478 CNY，冒烟 5.871 CNY，合计 6.349 CNY。

## R5 补丁补记

日期：2026-09-28。依据 `HARNESS-SPRINT-5-PATCH.zh-CN.md`。只用了 mock，真实模型花费 0，本轮合计仍是 6.349 CNY。没有打 `a5-main-freeze`。

P3 的 django 重新校准跑了约 38 分钟，这段时间里先提交了 P4 的代码。两者互不依赖，提交顺序是 P1、P2、P4、P3。

### P1 mock 输出和正式输出分开

`runs/a5-main/` 整个移到了 `runs/a5-main-mock-step7/`，6 个 summary 都在，没有删除。`docs/sprint/main-b0-runs.json` 用 `git mv` 改名为 `main-b0-runs.step7-mock.json`，内容没动，所以里面的 `summary` 路径还写着 `runs/a5-main/...`，实际位置在 `runs/a5-main-mock-step7/...`。现在 `runs/a5-main/` 不存在，`docs/sprint/main-b0-runs.json` 也不存在。

`run_a5_main.py`：`--mock` 写 `runs/a5-main-mock/` 和 `main-b0-runs.mock.json`，正式运行写 `runs/a5-main/` 和 `main-b0-runs.json`。只有 summary 里 `mock` 和当前模式一致、`profile` 是 `b0-v2`、`variant` 和当前 phase 一致时才算续跑完成。任何一条不满足，或者 summary 缺 `mock`/`profile` 字段，就列出这些文件并退出，不覆盖，也不启动任何一次运行。`run_task` 的 summary（包括隔离失败的提前返回）现在带 `mock` 和 `profile`。`write_b0_handoff` 用同一条检查，正式交接遇到 mock summary 直接报错。step 7 的旧 summary 没有这两个字段，放回正式目录也会被拒绝。测试在 `tests/test_run_a5_main.py`。

### P2 时间过滤

`temporal_filter` 改用卡片自己的 `repo` 和 `created_at`。dev 交接文件里有同一张卡时做交叉核对，repo 或时间不一致就报错。时间用 `datetime.fromisoformat`（先把 `Z` 换成 `+00:00`）解析，解析失败或没有时区都报错。B2 的目标日期：题目池的题读 `main-targets.yaml`，dev 题读 dev 交接文件，都找不到就退出。原来"拿不到日期就退回留一法"的分支删了。`dated_cards` 遇到补不上日期的行直接报错，不再丢弃。

v5 final 的 14 张卡和 dev 交接文件逐张核对过，repo 和时间都一致。测试覆盖了：不在 dev 交接文件里的 pool 卡按自己的日期参与过滤；`+09:30`、`Z`、`+08:00` 混用时按时刻比较（测试里两张卡如果按字符串比较都会判错）；卡片缺日期、日期无法解析、没有时区、和交接文件不一致、目标没有日期、卡片行补不上日期，都会报错。

### P3 Django docstring 测试 id

在应用了测试补丁的源码树上用 `ast` 扫描测试方法，按 unittest `shortDescription()` 的取法得到 docstring 第一行，和 id 完全相等且只匹配一个方法时，映射为 `module.Class.method`。扫描范围是测试补丁涉及的 `tests/` 文件，加上同一道题里其他可定位 id 所在的模块。零个匹配记 `docstring_unmatched`，多个匹配记 `docstring_ambiguous`，都算定位失败。映射之后仍有 F2P 定位失败的题判为 `f2p_unaddressable` 并排除（`calibrate` 和 `grade_verdict` 都加了这条）。校准 JSON 的 `nodeids` 里新增 `mapped` 计数和 `mapping` 明细。

12 道 django 题都用 empty 和 gold 重新校准，其他仓库没动。映射出来的 id 在空改动和 gold 下都被收集并执行了，没有 `missing`。gold 下的 P2P 全部通过，`p2p_excluded` 全部变成 0；之前 7 道题共排除了 73 条，其实都是没法定位、在 gold 下显示为 missing 的 id。django-14434 那 54 条现在走同一条规则：49 条映射成功，5 条有歧义被丢弃。

下表中"前"是这次补丁之前实际能送进 grader 的条数，"后"是这次校准实际送进 grader 的条数：

| 题 | F2P 原始 | F2P 前 → 后 | P2P 原始 | P2P 前 → 后 | 映射 F2P/P2P | 歧义丢弃 P2P |
| --- | --- | --- | --- | --- | --- | --- |
| django-11211 | 1 | 1 → 1 | 76 | 75 → 76 | 0/1 | 0 |
| django-11749 | 1 | 1 → 1 | 34 | 31 → 34 | 0/3 | 0 |
| django-12276 | 2 | 2 → 2 | 117 | 114 → 117 | 0/3 | 0 |
| django-13109 | 2 | 2 → 2 | 170 | 160 → 169 | 0/9 | 1 |
| django-13512 | 3 | 3 → 3 | 32 | 31 → 32 | 0/1 | 0 |
| django-13964 | 1 | 1 → 1 | 36 | 35 → 36 | 0/1 | 0 |
| django-14434 | 1 | 1 → 1 | 133 | 79 → 128 | 0/49 | 5 |
| django-15022 | 3 | 1 → 3 | 56 | 30 → 54 | 2/24 | 2 |
| django-15499 | 1 | 1 → 1 | 35 | 15 → 35 | 0/20 | 0 |
| django-15973 | 1 | 1 → 1 | 157 | 63 → 152 | 0/89 | 5 |
| django-16527 | 1 | 1 → 1 | 6 | 3 → 6 | 0/3 | 0 |
| django-7530 | 1 | 1 → 1 | 59 | 59 → 59 | 0/0 | 0 |
| 合计 | 18 | 16 → 18 | 911 | 695 → 898 | 2/203 | 13 |

django-15022 的两条 F2P 映射到了 `admin_changelist.tests.ChangeListTests` 下的测试方法：空改动 0/3，gold 3/3，这道题恢复了原来的判定标准。13 条歧义 P2P 的 docstring 第一行都对应同一个类里的两到四个方法（例如 `Tests simple altering of fields` 同时对应 `test_alter` 和 `test_rename`），按规则丢弃，候选方法记在 `dropped[].candidates` 里。没有题因为 `f2p_unaddressable` 被排除。django 仍是 11/12 合格，django-7530 仍是 `empty_f2p_did_not_fail`。

**另外修了一处：R6 运行时用的测试 id 和校准不一致。** 改之前，`grader_spec` 从私有字段重新推导 id，用的规则和校准不一样：django 不丢弃无法定位的 id，sympy 在没有源码树的情况下直接拼第一个测试文件名，也不处理 pytest 那几条丢弃规则。在 56 道合格题上对比，django 15022/15499/15973/16527、sympy 13091/13757/14248、sklearn 14710/15100 这 9 道的 id 集合和校准不同；sphinx 的 11 道会在 `PYTHON_PATHS` 上 `KeyError` 崩掉。step 7 mock 里 django-16527 的 3 条 P2P 就是以 `missing` 送进 grader 的，按这个状态跑 R6，这几道题永远不可能判为解出。现在 `materialize_runner_task` 调用校准用的同一个 `nodeid_selection`，得到的条数和校准 JSON 里记录的不一致就退出；`grader_spec` 直接用这份 id。56 道全部核对一致。解出的判定规则没有改。

### P4 扫描排除护栏

`/opt/repo` 下的命中，以及路径经过目标项目顶层包目录的命中（包括压缩包内部路径），不再适用"和基础镜像同 sha"或"和 pip RECORD 同 sha"这两条排除。顶层包从源码压缩包的清单里取，包括根目录和 `src/` 下带 `__init__.py` 的目录（pytest 是 `src/` 布局）。测试在 `tests/test_base_image_scan.py`。

没有重建镜像。56 份合格题的 receipt 里，两类排除清单都没有超过 20 条的记录上限，是完整的，所以直接用新规则离线重判（`scripts/sprint5_rejudge_scan.py`，结果在 `docs/sprint/scan-rejudge.json`）：一共排除了 6 个文件，没有一个落在护栏范围内，56 道的结论都没变。审计点名了 5 个文件，第 6 个是 pytest-5631 的 `runpy.py`：

| 题 | 文件 | 规则 |
| --- | --- | --- |
| pytest-5631 | `/usr/local/lib/python3.9/pickle.py` | 和基础镜像同 sha |
| pytest-5631 | `/usr/local/lib/python3.9/pickletools.py` | 和基础镜像同 sha |
| pytest-5631 | `/usr/local/lib/python3.9/runpy.py` | 和基础镜像同 sha |
| pytest-5631 | `/usr/local/lib/python3.9/site-packages/attr/_cmp.py` | 和 pip RECORD 同 sha |
| sphinx-8120 | `/usr/local/lib/python3.9/site-packages/babel/messages/mofile.py` | 和 pip RECORD 同 sha |
| sphinx-8120 | `/usr/local/lib/python3.9/site-packages/babel/messages/pofile.py` | 和 pip RECORD 同 sha |

`MAIN-CALIBRATION.md` 现在由 `write_summary` 生成这张排除表，以及 django id 映射表。

### P5 杂项

`pelican-bicycle.html` 从来没有被 git 跟踪过，已删除。

coding-agent 的 v5 final 已经提交：manifest `status: final`，14 张卡都有 `repo` 和 `created_at`，`cards_sha256` 是 `40d22ef838af7172ba8e72b09954107ea055d65501e11219c71ae2e0a88c015c`。用这份卡片对 django-16527、sympy-11618、sklearn-14053 各跑了一次 mock B2，写在 `runs/a5-main-mock/`，费用 0，三道都没解出（mock 直接停止）。summary 里 `mock: true`，`profile: b0-v2`。

| 题 | 过滤前 | 过滤后 | 注入 | grader |
| --- | --- | --- | --- | --- |
| django-16527 | 14 | 3（10914、10924、11039） | 0 | F2P 0/1，P2P 6/6，无 missing |
| sympy-11618 | 14 | 1（11400，failed_attempt） | 0 | F2P 0/1，P2P 4/4 |
| sklearn-14053 | 14 | 5 | 10297（771 字节）、11040（871 字节） | F2P 0/1，P2P 5/5 |

过滤后的卡片数和 step 7 用 v4 时一样。只有 sklearn-14053 的事件里出现了被注入的两个 source id，其他仓库和更晚的卡片都没有出现。

### 结论

全量测试 304 passed、199 skipped（补丁前是 285 passed、199 skipped）。最终合格题数仍是 56（django 11、sympy 12、sklearn 10、sphinx 11、pytest 12），R6 仍按 56×2×3 = 336 次估计。真实模型花费 0。停在这里等审计，没有打 tag。
