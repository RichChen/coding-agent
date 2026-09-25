# v4 记忆协议

标签来自源题自己的 SWE-bench 测试，由 harness grader 给出，不来自 20 道 pilot 目标题。
源题和 `configs/a5/canonical-handoff.json` 的 `target_tasks` 不相交，构建时会断言。
交接文件里如果出现 pilot 目标题 id，构建脚本直接停止。
不在这 15 道源题里的运行会被忽略。
F2P / P2P 计数只用于打标签，不写进卡片正文。

选轨迹的规则是固定的，不看卡片内容：

1. 新环境下有解出的运行时，取 `repeat` 最小的那一次，标 `validated_fix`，`label_origin=source_task_swebench_tests`。
2. 新环境下都没解出时，取 `repeat` 最小的那一次，标 `failed_attempt`，来源同上。
3. 新环境下没有运行时，用旧记忆池轨迹，标签来自 `memory-source-verification.json`；grader 不可用则为 `unverified`，`label_origin=legacy_verification`。

和 v3 的差别：目录兼容 sprint 布局；`changed` 支持 base64；失败尝试不渲染 approach；
只保留真正的测试命令；记忆源扩到 15 道（缺运行的先不编造卡片）。
这一版状态：interim。
