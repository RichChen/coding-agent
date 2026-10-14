# A5 shared gate approval boundary

2026-09-22。`A5-harness-preflight-50-shared-gates` 是当前冻结的共享门禁收据。它只做离线校验，model calls=0、paid build/pilot 均未启动。

已齐的共享门禁：

- model binding：`deepseek-flash@DeepSeek-V4.1-Flash`、CNY accounting schedule、来源 URL、retrieved/effective date 和 binding hash 均被固定；价格用途是宿主 CNY 账本，不冒充账户发票。
- CNY runtime alignment：总额 `50.000`，build `3.840`，pilot `46.080`，reserve `0.080`；build/pilot 分阶段硬上限和 unknown usage 保留预留均通过离线探针。
- 双 source fingerprint：harness 与 coding-agent 当前快照已绑定；任一侧代码、runner、配置或 grader 改动都必须重新冻结。
- B0–B3：四个 schema fixture 均通过 fail-closed importer；B0 无 injection，B1–B3 都带 candidate/source/evidence 绑定。

`django-13265` 的处置见 `A5-harness-preflight-48-django-contract-resolution`。四个 F2P 方法中两个 baseline 失败、两个 baseline 通过是合同允许的 method-level 结果，保留完整分母和所有精确 ID。

这个边界仍然不是付费许可：24 题基线合同状态保持 23/24，剩余 16 个 memory source 尚未逐项预检，且没有新的显式 paid-build authorization。故收据明确写入 `shared_gates_ready_for_approval=true`、`ready_for_paid_build=false`、`memory_build_eligible=false`。下一步只能由审批者在这些阻断项处理后批准费用建池。
