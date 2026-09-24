# A5-02 同池四变体

动机：将结构化表示和 validity 的效应从不同预算/检索池中分离。前置 A5-01。

范围：新增 `experiments/variants.py` 的 select_variant，复用 tokens/check_validity/MemoryRecord；不修改 H4 或 D0–D3。输入 PublicTask、EvidenceState/RepoFacts、合同、同一历史池与 source policy；输出候选、排序、requested/selected/rejected、validity reason 和无实际注入的 proposal。

验收：B0/空池零候选；B1–B3 原始检索排名和配额一致；B2/B3 文本一致且只差 validity；known stale 与 unknown 在 B3 拒绝；身份/标签不参与匹配；oracle sentinel 不进索引/输入/提示。产物：选择器、4 个 dev smoke、测试与逐条决策。

风险：规则检索不能证明真实收益；B2 绕过 current validity 是对照定义，不绕过来源或已隔离状态。退出：4 smoke 全符合合同，无虚构 repair success。命令：`python -m pytest tests/test_a5_variants.py`（实现后核实）。

完成：`variants.py`、4 场景 fixture 和定向测试已实现。测试含同池排名、top-3/最多 2 条、多字节 4096-byte 整条拒绝、冲突/重复、B2/B3 文本一致和 opaque task ID/seed 非干扰。smoke 的 B3 selected 为 0/1/0/0，所有实际模型注入为 0。验收见 [A5-VERIFICATION](../A5-VERIFICATION.md)。
