# HARNESS R6 修订 1：运行时 source-only 比对修复与全量预检

日期：2026-09-28。依据：CHECKPOINT-6a 审计。

canary 停下是对的，诊断也正确：构建时排除了 `pre_install` 里 `sed` 改写的文件，运行时没有排除，12 道题（sphinx 11 道、pytest-8399）会在运行前比对失败。镜像本身没有问题，这也不是泄漏。

这些 `sed` 都是 SWE-bench 规格里确定性的依赖锁定（例如 `Jinja2<3.0`、`pytest -rA`、`>=>=` → `>=`）。

执行顺序：F1 → F6，完成后按 `HARNESS-SPRINT-6.zh-CN.md` 继续第 1 步的剩余部分和第 2 步。遇到停止条件照旧写 CHECKPOINT-6a。

## F1 被改写的文件按"重放后的期望内容"校验（采用做法 2）

1. 把 `sprint5_prepare_main.py` 里推导 `rewritten` 的逻辑抽成共用函数，返回"文件 → 按顺序作用于它的 sed 命令列表"。解析规则和现在一致。
2. 新脚本（或同一模块里的函数）为每道受影响的题计算期望 hash：
   - 从 `source.tar.gz` 取出原文件；
   - 在该题的 clean image 里用 `--network none` 起一个临时容器，只在 `/tmp` 的 tmpfs 里按原顺序执行这些 sed 命令；
   - 取结果文件的 sha256。

   结果写到 `docs/sprint/rewritten-expected/<task>.json`，内容包括 sed 命令原文、原文件 sha、期望 sha。
3. `source_only_check` 增加参数 `overrides: dict[path, sha]`。在 override 里的文件按期望 sha 比对，其余文件照旧按压缩包 manifest 比对。**不再有"跳过不比"的文件。**
4. 构建路径（`sprint5_prepare_main.py`）和运行路径（`run_swe_task.py`）都改为调用同一个函数，使用同一份 override。
5. 对 12 道受影响的题，用新规则离线核对镜像，必须全部通过。如果有任何一个文件和期望 sha 对不上，就停下报告，不要回退到做法 1。
6. 测试：override 文件内容正确时通过；override 文件内容被改动时失败；不在 override 里的文件被改动时失败。

## F2 零花费全量预检

`run_a5_main.py` 新增 `--preflight`。对全部 56 道合格题，执行运行前的所有检查，但不调用模型：

- 解析镜像；
- 检查 `answer_isolation_pass`；
- source-only 比对（含 override）；
- 核对 grader id 和校准 JSON；
- 生成 public task。

结果写到 `runs/a5-main-logs/preflight.json`。**必须 56/56 通过**，否则停下报告。

## F3 全量 mock 端到端

新增只允许和 `--mock` 同时使用的 `--out-root`。对全部 56 道跑一次 mock B0 r1，写到 `runs/a5-main-mock-e2e/`，费用为 0。

mock 客户端会直接停止，所以 grader 评的是空改动。用脚本检查全部 56 道：

- 没有 `answer_isolation_failed`，没有 infra_error，grader 没有崩溃；
- F2P 全部失败（等于校准里的 `empty_f2p`）；
- P2P 的通过数和总数等于校准里的 `empty_p2p`，并且没有 `missing`。

有任何一道不一致就停下报告。结果汇总写进 CHECKPOINT-6a。

## F4 sphinx-8593 这个槽位的处理

`runs/a5-main/sphinx-doc__sphinx-8593/b0/r1/` 整个移到 `runs/a5-main-halted/sphinx-doc__sphinx-8593/b0/r1/`，只移动，不删除。`runs/a5-main/b0-report.json` 也移到 `runs/a5-main-halted/`。

规则：模型调用为 0、花费为 0、因 harness 运行前检查的 bug 失败的运行，不算实验数据，可以移出后重跑这个槽位。这条规则写进冻结修订记录。**有模型调用的运行一律不适用这条规则。**

## F5 infra_error 停止线

改为：infra_error 次数 ≥ 3，**并且**超过已完成运行数的 10%，才停止。加测试。

## F6 冻结修订

1. 在 `A5-MAIN-FREEZE.md` 末尾加"修订 1"一节，写明：
   - 原因；
   - F1–F5 的提交；
   - F4 的规则；
   - 两次已完成的 canary 运行（django-13964 r1、sklearn-13142 r1）继续有效，理由是它们的 `pre_install` 不改写源码文件，比对结果不受影响，并注明它们跑在 `02c8671` 上；
   - F2、F3 的结果。
2. 保留原 tag `a5-main-freeze`，不移动。全量测试通过后，在修订提交上打新 tag `a5-main-freeze-r1`。

## 之后

F1–F6 全部通过后，不用再停下等审计，直接继续：

1. 真实运行 sphinx-8593 的 B0 r1，补完 canary，检查项和第 1 步一样。
2. 通过后进入第 2 步全量 B0。已有的 django-13964 r1 和 sklearn-13142 r1 按续跑规则保留。
3. B0 跑完或触发停止条件时，写 CHECKPOINT-6a 并停下。不要开始 B2。

coding-agent 侧本轮不需要任何操作，继续等 `main-b0-runs.json`。
