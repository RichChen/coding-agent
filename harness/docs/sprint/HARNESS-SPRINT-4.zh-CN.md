# coding-harness 第四轮计划：修复答案隔离并重建有效基线

日期：2026-09-25。

本计划覆盖第三轮审计矫正文件中的冲突部分：
`docs/sprint/AUDIT-3-CORRECTION.zh-CN.md`。

## 0. 先冻结结论

- `b0-v1` 的 42 次运行保留，但统一标为“测试可见条件下的历史结果”，不再作为 SWE-bench B0 基线。
- 当前 `memory-source-runs.json` 和 coding-agent 的 interim v4 不得用于 final 记忆或模型实验。
- 不能只把 workspace 的测试文件恢复成 original。旧镜像的 `/opt/repo` 本身含 test patch，模型仍可从 shell 读取它。
- R4 不做 thinking、不跑 pilot 模型、不扩充实验变体、不修 ACL。

## 0.1 沿用的规则

- 第一轮的硬约束继续有效：不提交密钥和 `.env`；不提交任何 private 文件；小步提交；不 force push；不删除旧证据。
- 开工前先提交 `AUDIT-3-CORRECTION.zh-CN.md`、本计划书和 `R4-START-PROMPTS.zh-CN.md`，然后打 tag `sprint4-start`。继续往 `PROGRESS.md` 追加记录，标题用"第四轮 R4-N"。
- 根目录的 `cursor-a602-latest.txt` 是对话导出的临时文件，不要提交，删掉或加进 ignore。第三轮的 4 个诊断脚本移到 `scripts/diagnostics/` 后提交。
- 本轮真实模型花费上限 20 CNY，单次运行不超过 1 CNY。

## 1. R4-1：构建真正干净的 image

新增一种 clean baseline image 构建方式，输入是原始源码归档和依赖配置：

- `/opt/repo` 只含 base revision 的源码，以及依赖安装必须生成的、单独列入 manifest 的构建产物；不得含 test patch、gold patch 或 known-good 代码。
- 不把旧 `baseline.tar.gz`、`known-good` image 或 pilot known-good image 作为 agent image。
- receipt 增加 clean image digest、排除构建产物后的原始源树 hash、镜像 source-only hash、生成的 native artifact 清单和构建输入 hash。
- `BaselineImageBackend` 支持 clean image，并把 `/opt/repo` 的树 hash 写入 host-side summary。测试补丁路径和 nodeid 不进入 prompt、工具输出或 agent workspace。
- grader 继续在 host 侧持有 test patch；启动 clean image 后先复制原始树，再应用 candidate delta，最后覆盖 test patch。

优先复用 `preflight_a5_repo_baseline.py` 的依赖 profile，但归档输入必须是 original archive。若暂时保留旧镜像兼容路径，旧镜像只能用于历史复核，不能启动新的模型运行。

需要注意的两个细节：

- 旧的 Dockerfile 会把归档本身 `COPY` 到 `/opt/<archive>`，镜像里的 `/workspace` 层也保留着一份源码。clean image 里**不能有任何含 test patch 或 gold 的文件副本**，不只是 `/opt/repo`。
- `BaselineImageBackend` 的 `LINK_NATIVE` 和 `prepare_repo_runtime()`，是靠 `/opt/known-good.tar.gz` 或 `/opt/baseline.tar.gz` 来区分"源码里自带的 .so"和"构建生成的 .so"的。找不到归档时，它会**静默跳过链接**，`.so` 留在 `/workspace` 的 tmpfs 里，sklearn 可能导入失败。clean image 要换成新的判别依据（比如 native artifact 清单）。找不到依据时必须报错，不能静默跳过。用 sklearn 题做零模型验证：agent 容器和 grader 容器里都能 `import sklearn` 并收集到测试。

## 2. R4-2：答案隔离检查

每次运行开始前执行 host-side 检查并写入 summary：

- `/opt/repo` 的 source-only hash 与 original tree 一致；允许的 native artifact 必须逐项出现在 manifest，不能用整体字节 hash 掩盖源码差异；
- workspace 中 test patch 路径与 original 字节一致；original 中不存在的 test patch 文件不存在；
- workspace 中没有 gold patch 路径的 gold 内容；
- clean image 的检查失败时，运行直接标记 `answer_isolation_failed`，不调用模型。

delta 导出以 original workspace 为基准。只有模型真正修改测试文件时才把它列入 delta，并记录 `test_files_touched`；初始化或清理动作不能制造 delta。

用零模型对至少三道题验证：workspace 搜索不到 test patch 新增内容，`/opt/repo` 也搜索不到；空 delta 的导出为空。

除此之外，每个 clean image 构建完成后，做一次**全文件系统扫描**，零模型：

- 从 test patch 和 gold patch 里各取几行新增的特征行，比如新增测试函数的定义行。
- 在容器里对 `/`（排除 `/proc`、`/sys`、`/dev`）做 `grep -rF`，包括所有压缩包。压缩包先列出其中的成员，再检查成员内容，或者直接断言镜像里没有源码归档。
- 任何命中都判定为 `answer_isolation_failed`。
- 扫描结果写进 receipt。三道题只是冒烟用，**这个扫描要对所有 clean image 都做**。

## 3. R4-3：重新校准 grader

对每道 dev 和 pilot 候选题只做零模型校准，使用 clean image：

1. empty delta 的 F2P 至少有一个失败；
2. gold delta 的全部 F2P 通过；
3. empty 与 gold 的 nodeid 结果必须有变化；否则记录 `delta_has_no_effect` 并判定不合格；
4. P2P 只在 gold 稳定后纳入，gold 失败的 P2P 按固定规则排除并记录原因。

当前原始结果（`runs/sprint3-pilot-calibrate/results.jsonl`）里有打分的 16 道题，empty 和 gold 的计数全部相同：9 道两者的 F2P 都通过（sklearn 25747、25500，sphinx 8595、8721，sympy 20442、20154、24152，django 13448、13590），7 道两者的 F2P 都是 0（pytest 7432，sklearn 25570、25638，sphinx 8713、10451，sympy 18532，django 15781）。PROGRESS 第 6 步表格里的 9 和 7 是对的，CHECKPOINT-3 里写的"6 道"是错的。这证明旧校准链路不能作为题目适用性结论。

dev 和 pilot 的校准互不阻塞：R4-4 只要求 14 道 dev 题的 clean image 通过隔离检查和校准。pilot 的 clean image 和校准可以在 B0 运行期间继续做，结果写进 R4-5。

## 4. R4-4：在 clean profile 上重跑 B0

14 道 dev 题的全文件系统扫描、答案隔离检查和校准全部通过，并且结果已经写进 PROGRESS 之后，直接开跑，不需要再停下来申请。如果有 dev 题没有通过，就用通过的题跑，并在 PROGRESS 里列出被排除的题和原因。

- 新 profile/tag 使用 `b0-v2`；
- 14 道 dev 题，每题 3 次，共 42 次；
- 产出 `runs/sprint4-b0-v2/`、结果表和新的 `docs/sprint/memory-source-runs.json`；
- handoff 必须写 `profile_tag: b0-v2`、每次运行的 `answer_isolation_pass: true` 和 clean image digest；
- 预计约 16 CNY，单次仍不超过 1 CNY；
- 运行期间不改 prompt、工具集、grader 判定或检索规则。

旧 v1 只作为“测试可见条件”对照保留，报告中与 v2 并列，不合并统计。

## 5. R4-5：交接和停止条件

R4 结束时必须有：

- 每道题的 clean image 和校准结果；
- 每次运行的答案隔离结果；
- v1/v2 的逐题解出次数；
- 新 handoff 的 SHA256；
- 未决问题和实际花费。

以上内容写进 `docs/sprint/CHECKPOINT-4.md`，然后停下，等审计。

任一运行发现 test patch、gold 内容或隐藏测试可见，立即停止该波，不重放已完成运行。

coding-agent 在收到 `profile_tag: b0-v2` 的 handoff 前不得把 interim v4 变成 final，也不得跑 memory smoke 或 A5-lite。

## 6. 明确不做

- 不把 failed/unverified 做成新的正式实验变体；
- 不在当前污染数据上调整 retrieval；
- 不把绝对路径、ACL、thinking、可移植性清理混入 R4 主线；
- 不在 pilot 上调用模型。
