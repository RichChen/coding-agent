# A5-03 收据、全成本与结果审计

动机：选择不等于注入、prepared view 不等于模型采用。前置：A5-01/02 固定 DTO；可用独立 fixture 验收。

范围：新增 `experiments/audit.py, offline.py`、`scripts/run_a5_offline.py`；ResultRow、UsageAttempt、InjectionAudit、summarize、estimate_cost。输入固定 assignments 和 host receipt/usage/evaluation JSON；输出逐任务结果、首 attempt 分母、重跑记录、paired diff、全成本/unknown、dry-run。只做数据分析，不执行 grader/模型、不修改 H4。

验收：missing/invalid_env/degraded 保留；缺 operation/attempt/hash 不算实际注入；额外/失败模型调用全部有账且缺 usage=unknown；缺 split 证据拒绝解释；4 dev smoke 排除主分母；12/20×3 dry-run 不调用 API。产物：JSON 报告、manifest、成本估算、测试、实际 diff。

风险：H5 prepared-view metadata 不能自动转换为实际模型注入证据；缺 host 明细时保留 unknown。退出：离线测试/报告可重建且付费执行入口未开放。命令：`python -m pytest tests/test_a5_audit.py`、`python scripts/run_a5_offline.py --output <new-dir>`（实现后核实）。

完成：`audit.py`、`offline.py`、离线脚本、JSON/Markdown 报告和 dry-run 已交付。39 项定向和 222 项扩大回归通过；主报告可以从冻结 manifests 与保存的 ResultRow 重建。缺行/构建漏账/未知 usage 不填零；私有检查与公开 index 分离。实际命令及变更清单见 [A5-VERIFICATION](../A5-VERIFICATION.md)。
