# A5-01 合同和数据冻结

动机：没有 split 与来源证据不能解释效果。前置：阅读 A5-PLAN、既有 SourcePolicy/MemoryRecord。

范围：新增 `experiments/contracts.py` 的 ExperimentContract、DatasetManifest、MemoryBuildManifest、validate_manifests；配置在 `configs/a5/`。输入为公开任务、reviewed 来源 metadata、固定历史/构建记录；输出为可 hash 的 JSON、明确缺项和 pilot readiness。不得联网补数据、接管 runtime 或改旧数据。

验收：跨 split ID/hash/duplicate group 拒绝；未审核/缺元信息拒绝；所有原文和 MemoryRecord 源一一一致；版本和 common profile hash 固定；真实 pilot 缺数据/价目/货币上限拒绝启动。产物：DTO、测试、冻结清单和 12/20×3 配置。

风险：合成 split 不能证明自然时间顺序或模型训练无污染。退出：smoke 清单可完整审计，真实任务缺失如实 pending。命令：`python -m pytest tests/test_a5_contracts.py`（实现后执行核实；最终精确命令见 A5-VERIFICATION）。

完成：`contracts.py`、`configs/a5/pilot-{12,20}.json` 和 `test_a5_contracts.py` 已实现；交付包保存冻结 hash 与原始来源字节。目标/未来/diagnostic 来源、split 重复和缺审查均拒绝，contract 的 model_copy 漂移也重新校验。真实 pilot 数据不伪造。验收见 [A5-VERIFICATION](../A5-VERIFICATION.md)。
