# A5 与 coding-harness 整仓 grader 的接线交接

宿主CLI消费入口：[pilot20-harness-consumption-manifest.json](../../configs/a5/pilot20-harness-consumption-manifest.json)，直接传给harness的 `scripts/a5_preflight.py --manifest`。该文件以字节hash绑定canonical JSON及公开审查文件，显式含20个memory IDs/opaque-ID映射和4条preflight子集。旧CLI字段 `historical_pool` 仅是4条子集的兼容别名，`planned_history_build_jobs=20`；每个source的 `paid_build_allowed=false` 且必须有自己的preflight。旧CLI只检查24题，不能据其结果推断20来源逐项gate或独立预算runtime已实现。已请求harness消费后重跑只读gate，具体回执另存，不覆盖旧证据。

2026-09-21 canonical 收口：唯一宿主入口改为 [canonical-handoff.json](../../configs/a5/canonical-handoff.json)，冲突与ID清单见 [收口报告](A5-CANONICAL-HANDOFF-RESOLUTION.md)。20 targets、20 memory sources、4 preflight history 是三个不同集合；4条是20来源的子集。先过20+4的24题零模型离线gate，其余16来源再分别通过自身repo/环境/baseline/grader gate，不能自动解锁。当前只有计划，无可运行冻结；本轮禁用所有paid build/pilot，停在handoff等待。旧v12包作为不可覆盖的输入证据保留，不是执行许可。harness预算和公开审查hash仍待按本报告对齐，未声明双端消费完成。

2026-09-21。coding-harness 的整仓 grader 已完成 Flask-4992 的端到端验收，但这不等于 Django、SymPy、scikit-learn、pytest、Sphinx 的环境都已 ready。本仓只保存交接要求，不修改 coding-harness，也不启动模型。

每个 build job 必须由 harness 宿主创建新 workspace，给 agent 的输入只有公开 PublicTask 和公开 base；私有 `EvaluationSpec`、test patch、gold patch、F2P/P2P 和原始 parquet 留在宿主 grader 侧。agent 停止、候选快照和清理完成后，harness 独立执行完整 pytest collection 和私有 spec，导出 operation、attempt、usage、候选 hash、grader artifact 和 cleanup 状态。

本仓的 [harness-build-handoff.json](../../reports/upgrade/a5-funded-build-preparation-20260921-v12/harness-build-handoff.json) 已为 20 个来源生成同一格式的宿主接线记录。`base_snapshot` 和 `candidate_snapshot` 目前明确为 `null`，因为它们必须由目标仓库对应的 harness 环境预检产生；不能把 Flask 镜像或现有裁剪 fixture 套到其他仓库。

正式建池前需要逐来源满足：完整 base 字节快照和 source hash、固定 Python/pytest/依赖镜像、非空唯一测试身份、baseline 缺陷复现、私有 known-good 校准、测试/配置篡改阴性拒绝、网络/挂载/资源边界、容器清理，以及全部失败和 invalid_env 的收据留存。满足这些条件后才可把 assignment 从 `awaiting_repo_grader_readiness` 改为可运行；没有 receipt 的 attempt 不得进入 raw trajectory 或 MemoryRecord。

正式 pilot 仍要重新冻结双方 source fingerprint、model snapshot、价目和唯一预算账本。建池与 pilot 使用不同账本；pilot 上限约 50 CNY，memory build 按实际需要单独计账。记忆 snapshot 冻结后不再写入，随后才执行 B0–B3 的 240 条 assignment。
