# 第五轮审计节点

日期：2026-09-26。本轮模型花费 6.349 CNY，上限 10 CNY。到这里停下，等审计。没有打 `a5-main-freeze`，也没有进入 R6。

## 第 0 步

真实运行强制使用 clean image，不再看 profile 名。`--legacy-image` 只能和 `--mock` 一起用。

sklearn-11281 原来的 r2 是工件配额超出（16MB），不是 ACL，也不是宿主机磁盘满。旧目录留在 `runs/sprint4-b0-v2/scikit-learn__scikit-learn-11281/r2-storeerror`。会话工件上限改为 64MB。`StoreError` 记为 `infra_error`，不进解出率分母。

重跑的 r2 解出，33 次调用，`completed`，隔离通过，花费 0.478 CNY。11281 变为 2/3。42 次合计 18/42，14.522 CNY。这 0.478 算在第五轮里。

## 镜像方案

三道试用题的官方镜像扫描都是 0 命中。校准只有 django-10914 通过（空改动 F2P 0/1，gold 1/1）。sympy-11400 的 gold 没有写出收据。sklearn-10297 有 `.so`，镜像里没有 native artifact 依据，按规则报错。三道没有全部通过，题目池不用官方镜像。

决定用 `build_clean_baseline.py` 自建，安装命令读取 SWE-bench v4.0.4 的版本 specs。`main-targets.yaml` 的 `image_source` 是 `swebench-specs-v4.0.4`。已经拉下的 3 个官方镜像没有删除。

## 磁盘

Docker 数据盘仍在 `C:\Users\Administrator\AppData\Local\Docker\wsl\disk\docker_data.vhdx`。检查时 C 盘空闲约 68GB，不到 150GB。没有迁移，也没有删除镜像。请手动把 Docker Desktop 的 Disk image location 迁到 E 盘（当时 E 盘空闲约 815GB）。第 5 步因此没有开始：题目池 60 道都还没有镜像，合格 0 道，没有按环境剔除的题。

## 题目池

60 道。id 列表 sha256：`d4caaa48c5735b2bf1a302855bbf94a2cdb5ab0397dff152d5d839440a4b22dd`。选定之后没有换题。`sphinx-doc__sphinx-8721` 被抽中，已从 `HOLDOUT` 移除。其余 pilot 仍然拒绝。

交接文件是 `sprint5.memory-source-runs.v2`，sha256 `984826707e8f69ad9b900134bd244c6056f2d8860f3036a3606bfc60b4bcb450`。

## 第 6 步冒烟

v5 manifest 不是 final，用的是 v4 final，`created_at` 由交接文件补上。14 道 dev 题各一次 B2，花费 5.871 CNY。过滤前都是 14 张。注入字节最大 1500，低于 4096。当前题和更晚的卡片没有注入。sklearn-11281 的上下文里出现了 `scikit-learn__scikit-learn-11040`。sympy 四道和 pytest-5227 过滤后还有卡片，但都不是 `validated_fix`，实际注入是 0。这一步不和 B0 比较解出率。

## R6 估计

60 题 × B0/B2 × 3 次 = 360 次。按 b0-v2 平均约 0.35 CNY，大约 125 CNY，上限 150 CNY。每次 4–6 分钟的话，串行 24–36 小时，可以 2–3 个并行。运行器是 `scripts/run_a5_main.py`。合格清单还不存在，B0 → 交接 → B2 的零模型走查没有执行。

本轮花费：重跑 0.478 CNY，冒烟 5.871 CNY，合计 6.349 CNY。
