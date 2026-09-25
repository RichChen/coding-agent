# R4 启动 prompt

## 发给 coding-harness agent

请执行 `D:\\crq\\src\\coding-harness\\docs\\sprint\\HARNESS-SPRINT-4.zh-CN.md`。

开工前完整读取 `AUDIT-3-CORRECTION.zh-CN.md`、本计划书、`CHECKPOINT-3.md` 和 `PROGRESS.md`。先做只读审计，证明旧 `baseline.tar.gz` 的 `/opt/repo` 含 test patch；不要启动 provider、模型或真实 pilot。

本轮最重要的修正是：只恢复 workspace 文件不够，模型仍能从 `/opt/repo` 读取测试。因此必须构建 clean image：`/opt/repo` 来自 original archive，只含原始源码和依赖，test patch/gold patch 只留在 host-side grader。先完成 clean image、全文件系统扫描、答案隔离检查和 zero-model calibration。dev 题的这些门槛全部通过、证据写进 PROGRESS 之后，直接运行 14×3 的 `b0-v2`，不需要停下来申请。任何隔离检查失败都立即停止，不要继续花钱。本轮模型花费上限 20 CNY。做完 R4-5，写好 `CHECKPOINT-4.md` 后停下，等审计。

## 发给 coding-agent agent

请执行 `D:\\crq\\src\\coding-agent\\docs\\sprint\\AGENT-MEMORY-4.zh-CN.md`。

先读取 harness 的 `AUDIT-3-CORRECTION.zh-CN.md` 和本计划书。不要把现有 `b0-v1` handoff 或 interim v4 变成 final，不要跑 memory smoke，不要调用模型。可以先补 B2 的 validated-only 过滤及单元测试；等收到 `profile_tag: b0-v2`、42 条且全部 `answer_isolation_pass=true` 的 handoff 后，再按计划重建 v4 final。
