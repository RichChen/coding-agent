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
