# 整仓 grader 证据索引

本目录仅为 grader/环境校准，模型调用0。公开接线只用 `audit-01/public-handoff.json` 指向的 public 文件；其余均留在宿主验证侧。

| 目录 | 结果与保留原因 |
| --- | --- |
| attempt-01 | 原始完整上游归档、250文件源树、首次构建；Werkzeug2.3.7，测试overlay遗漏TOML资源 |
| validation-01 | not_ready；base/known-good均473pass、9fail、2skip；完整保留失败，不删测试 |
| attempt-02 | 复用同一归档，补齐既有测试资源，依赖仅将Werkzeug固定为2.2.2 |
| validation-02 | 记录pip-freeze bytes无法JSON序列化的中断，manifest及failure.json保留 |
| validation-03 | 完整测试与所有拒绝行为正确；缺依赖在conftest阶段触发exit4，旧汇总谓词误判not_ready；原结果保留 |
| validation-04 | 最终ready，484固定身份、482必测通过、2既有skip、5类阴性验收通过 |
| audit-01 | 独立离线22项核验、完整12任务环境清单、源代码快照、公开handoff |
| cli-known-good | 独立CLI验收pass，482/484，2项允许skip |
| cli-missing | 独立CLI对缺失候选拒绝；仍保留1任务/484项测试分母 |

validation-01的旧报告沿用H3模板，里面的“success rate”仅是校准候选pass比例，不是agent成绩。最终报告已使用独立整仓模板，不报告该混淆指标。validation-03到04仅修正阴性验收汇总逻辑，不改变候选评分、测试或依赖。

最终测试命令与结果在 `verification.json`。完整接口说明：`../../FULL-REPO-GRADER-HANDOFF.zh-CN.md`。
