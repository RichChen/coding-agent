# v4 记忆协议

标签来自源题自己的 SWE-bench 测试，由 harness grader 给出，不来自 20 道 pilot 目标题。
源题和 `configs/a5/canonical-handoff.json` 的 `target_tasks` 不相交，构建时会断言。
交接文件里如果出现 pilot 目标题 id，构建脚本直接停止。
不在这 15 道源题里的运行会被忽略。
F2P / P2P 计数只用于打标签，不写进卡片正文。

选轨迹的规则是固定的，不看卡片内容：

1. 新环境下有解出的运行时，取 `repeat` 最小的那一次，标 `validated_fix`，`label_origin=source_task_swebench_tests`。
2. 新环境下都没解出时，取 `repeat` 最小的那一次，标 `failed_attempt`，来源同上。
3. `validated_fix` 只来自 `b0-v2` 且 `answer_isolation_pass` 的 grader pass。旧轨迹和 `b0-v1` 不能标成 `validated_fix`。
4. final 不用旧记忆池补洞。`pytest-5221` 不在这批 dev 运行里，所以没有卡片。

和 v3 的差别：目录兼容 sprint 布局；`changed` 支持 base64；失败尝试不渲染 approach；
B2 只注入 `validated_fix`；卡片来自 clean image 的运行。
这一版状态：final。
