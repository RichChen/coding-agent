# coding-harness 第五轮计划书：为 A5-main 准备题目池和环境

日期：2026-09-26。执行者：挂在 `D:\crq\src\coding-harness` 的 Cursor agent。
前置：`HARNESS-SPRINT-4.zh-CN.md`、`CHECKPOINT-4.md`。实验设计见 `A5-MAIN-DESIGN.zh-CN.md`，**本轮的所有工作都服务于这份设计**。
配套：`D:\crq\src\coding-agent\docs\sprint\AGENT-MEMORY-5.zh-CN.md`。

## 0. 第四轮审计结论

第四轮有效，不需要回滚。答案隔离已经修好：干净镜像、全文件系统扫描、每次运行前的源码哈希检查都已到位。`b0-v2` 的 17/42 是可信的干净基线。抽查了失败的运行：测试都被正常收集并执行，是真实的失败，不是链路问题。

需要处理的问题：

1. **隔离检查的开关写法很危险。** `run_swe_task.py` 里是 `if profile.stem == "b0-v2":` 时才使用干净镜像，其他任何 profile 名都会静默退回到有泄漏的旧镜像。
2. **sklearn-11281 r2 出了 `StoreError`**：账本记了 0.668 CNY，summary 里的模型调用数却是 0，最后按空改动被判为失败。
3. 交接文件的 sha256 是按 LF 换行归一化后计算的，而磁盘上的文件是 CRLF。这个约定没有写进任何文档。
4. 根目录有一个未跟踪的 `pelican-bicycle.html`，不属于本项目。
5. 原来的 20 道 pilot 题没有干净镜像。本轮不再单独处理它们，改为按 A5-main 的题目池统一准备（见设计文档第 3 节）。

## 1. 本轮规则

- 第一轮的硬约束继续有效。本轮模型花费上限 **10 CNY**：只包括 11281 的重跑和第 6 步的冒烟。
- 开工前提交 `A5-MAIN-DESIGN.zh-CN.md` 和本计划书，打 tag `sprint5-start`。继续往 PROGRESS 追加记录，标题用"第五轮 第 N 步"。
- **题目池里的题在本轮一律不调用模型**，只做数据准备、构建镜像和零模型校准。
- 删除任何 Docker 镜像之前，先把 digest 列表写进 PROGRESS。不能删除 `b0-v1` 和 `b0-v2` 用过的镜像。

## 2. 分步计划

### 第 0 步：先修小问题（不花钱，第 3 项约 0.7 CNY）

1. **干净镜像改为强制使用。** 删掉 `profile.stem == "b0-v2"` 这个判断。所有模型运行默认都必须使用 clean image，并且必须通过隔离检查。只有显式传入 `--legacy-image` 时才允许用旧镜像，而且这种情况下只允许 `--mock`，不能调用真实模型。补测试：用任意 profile 名跑非 mock 的运行，如果没有 clean image，必须拒绝。
2. **查 `StoreError`。** 查清 11281 r2 是在哪一步、为什么失败（是不是 ACL、磁盘或事件存储的问题）。修复之后，summary 在这种情况下也要从账本里读出模型调用数和花费，并把 status 标记为 `infra_error`；汇总时 `infra_error` 不计入分母。
3. 重跑 11281 r2，结果写进 `B0-V2-RESULTS.md`，同时更新交接文件。
4. 在 `docs/sprint/HANDOFF-CONVENTIONS.md` 里写明：交接文件的 sha256 按"UTF-8 编码 + LF 换行"归一化后计算，并给出计算函数。两边都用这一个函数。
5. 删除 `pelican-bicycle.html`（先确认 git 没有跟踪它）。

### 第 1 步：磁盘空间（需要人工配合）

题目池最多 60 道题，每道一个镜像，预计需要 60–150GB。先查清 Docker Desktop 的数据盘在哪里、还剩多少空间：

- 如果在 C 盘，并且空闲不足 150GB：**停下来，在 PROGRESS 里写清楚，请用户手动把 Docker 的磁盘镜像位置迁到 E 盘**（Docker Desktop → Settings → Resources → Disk image location）。不要自己去迁移。等待期间可以先做第 2 步和第 4 步。
- 可以清理 build cache（`docker builder prune`）。不要清理镜像。

### 第 2 步：试用 SWE-bench 官方实例镜像（不花钱）

背景：`dependency_profile()` 是按仓库手写的版本固定配置。题目池里的版本跨度很大（django 2.x–4.x，sympy 1.1–1.12，sklearn 0.20–1.3，sphinx 3–7，pytest 5–8），手写配置很可能大面积失败。SWE-bench 官方为每道题都发布了预先构建好的评测环境镜像（Docker Hub 上的 `swebench/sweb.eval.x86_64.*` 系列）。先核实它的实际命名和可用性。

1. 在 django、sympy、scikit-learn 里各选 1 道 dev 题，拉取对应的官方实例镜像。
2. 核实：
   - 仓库在哪个目录（一般是 `/testbed`），它是不是 base commit 的原始代码；
   - **全文件系统扫描**：确认没有 test patch 和 gold 的特征行，沿用第四轮的扫描方法；
   - Python 解释器的路径（一般是 conda 环境）；
   - 能不能用我们的 observer 收集并运行测试。
3. 让 `BaselineImageBackend` 和 `ImageGrader` 支持"仓库目录和 Python 路径可配置"，官方镜像和我们自己的 clean image 共用同一套逻辑：
   - 起容器之后，把仓库复制到 `/workspace`；
   - grader 先应用 delta，再覆盖 test patch，然后跑 F2P 和 P2P；
   - `.so` 的处理方式照旧，找不到判别依据就报错。
4. 对这 3 道题做零模型校准：空改动时 F2P 失败，gold 时 F2P 全部通过，两者结果确实不同。再用 mock 跑通一次完整链路。
5. **决策规则：** 3 道全部通过，题目池就用官方镜像；否则用 `build_clean_baseline.py`，版本配置改为读取 SWE-bench 官方的 specs（参考 `scripts/build_swebench_lite_subset.py` 里的 `_load_swebench_py_constants`），不要继续手写。决策和理由写进 PROGRESS。
6. 如果镜像拉取很慢或者被墙，在 PROGRESS 里记下实际速度，按第 5 条的后一种方案继续。

### 第 3 步：选定题目池（不花钱）

1. 新写 `scripts/select_main_targets.py`：用 `datasets` 加载 `princeton-nlp/SWE-bench_Verified`（test split），按设计文档第 3 节的规则选题：5 个仓库，排除 14 道 dev 题，每个仓库按 `created_at` 排序后等间隔抽取最多 12 道。
2. 产出 `configs/sprint/main-targets.yaml`，每道题记录：`id`、`repo`、`created_at`、`base_commit`、`version`、镜像来源。私有字段（F2P / P2P、gold patch、test patch）写进 `runs/` 下被 git 忽略的 private 目录，yaml 里只放路径引用。
3. 把选题脚本的输出（题目 id 列表）的 sha256 记进 PROGRESS。选定之后，不能因为环境以外的任何原因替换题目。

### 第 4 步：记忆源元数据（不花钱）

14 道 dev 题的 `created_at` 也从 SWE-bench 数据集里取出来，写进交接文件，供按时间过滤卡片使用。交接文件升级为 `sprint5.memory-source-runs.v2`，每条运行增加 `repo` 和 `created_at`。

### 第 5 步：为题目池准备环境并校准（不花钱）

对 `main-targets.yaml` 里的每道题：

1. 准备镜像：用第 2 步定下的方案。
2. 答案隔离：全文件系统扫描，再加源码哈希核对（官方镜像要和 base commit 的源码对比）。
3. 零模型校准：空改动时 F2P 失败，gold 时 F2P 全部通过，两者结果不同；gold 下失败的 P2P 按固定规则排除。
4. 输出 `docs/sprint/main-calibration/<id>.json`（格式和第四轮的 `clean-calibration` 一致），以及汇总表 `docs/sprint/MAIN-CALIBRATION.md`：合格的题数，剔除的题和原因，按仓库分别列出。

镜像构建和拉取可以批量做，失败的题自动重试一次。整体耗时较长也可以接受，但每处理完 10 道题都往 PROGRESS 写一次进度。

### 第 6 步：按时间顺序过滤记忆，并用真实模型冒烟（约 5 CNY）

1. `run_swe_task.py` 在 B2 下，传给插件之前先过滤卡片：只保留同一仓库、`created_at` 早于当前题、并且不是当前题的卡片。summary 的 `memory` 字段记录过滤前的数量、过滤后的数量，以及实际注入的卡片。补零模型测试，包括"更晚的卡片一定会被过滤掉"。
2. 使用 coding-agent 的卡片文件：`benchmarks/a5/memory-cards-v5.jsonl`，条件是它的 manifest 为 `final`，并且含有 `created_at` 字段。如果 v5 还没好，就用 v4 final 加上交接文件里的 `created_at` 在 harness 这边补上，这是一个临时办法。
3. 在 14 道 dev 题上各跑一次 B2（1 次重复）。目的是用真实模型验证注入链路：注入的内容是否出现在 prompt 里，是否符合时间和留一法的约束，字节数是否在上限以内。**这一步不和 B0 比较解出率。**

### 第 7 步：准备 R6 的运行器（不花钱）

1. `scripts/run_a5_main.py`：读 `main-targets.yaml` 和合格清单，先跑 B0（每题 3 次），全部完成后写出题目池的交接文件，停下；等 coding-agent 生成卡片之后，再跑 B2（每题 3 次）。支持断点续跑，支持 2–3 个并行，每次运行的输出目录互相独立。
2. CNY 总账本：总上限 150，单次上限 1，超出就停。
3. 用 mock 在 3 道合格的题上把 B0 → 交接 → B2 的流程完整走一遍（零模型）。

### 第 8 步：CHECKPOINT-5

写 `docs/sprint/CHECKPOINT-5.md`，内容包括：

- 第 0 步各项的修复结果；11281 重跑的结果；
- 第 2 步的镜像方案决策和依据；
- 题目池：选中多少道，合格多少道，按仓库分列的剔除原因；
- 第 6 步冒烟的注入情况；
- R6 的预计运行次数、花费和耗时；
- 本轮花费。

然后停下，等审计。审计通过后，冻结设计文档第 8 节列出的全部内容，打 tag `a5-main-freeze`，再进入 R6。

## 3. 本轮不做

- 在题目池上调用模型。
- 修改 `b0-v2` 的 prompt、工具、预算和 grader 判定。
- thinking、可移植性清理、ACL 修复。
