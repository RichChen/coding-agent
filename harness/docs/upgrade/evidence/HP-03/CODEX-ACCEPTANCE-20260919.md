# HP-03 接手验收与直接修补

日期：2026-09-19；HEAD `1f5903b620895ad8af3289ffeae529c15c3576a0`；解释器 `D:\crq\src\coding-harness\.venv\Scripts\python.exe`，Python 3.13.9，Windows。

接手时实跑为 **222 passed / 1 failed / 1 skipped**，失败为 `test_shell_path_still_works`。原 REPORT 的 PATHEXT 根因和全量通过结论不适用于接手现场：PATHEXT 当时已存在；shell 探针依赖 `python` 别名及环境 PATH。该 smoke 现使用带引号的 `sys.executable`，仍验证 shell 路径，不恢复全环境继承。

本轮额外修复：

- `await_with_control` 使用真正有界的 cleanup 等待，超时/异常明确 cleanup_failed；不吞掉并继续执行，保留结构化部分输出；开始前已取消则关闭尚未调度的 coroutine。
- Retry 直接取消也记录失败 attempt；禁止负小数/NaN/布尔 token 或预算上限被取整成零，异常 usage 保留预留。
- 命令正常退出先排空尾部输出；修复 leader 先退出但 wait 尚等 pipe EOF 的竞态，保留真实非零 exit_code。
- 创建进程期间取消会保留 spawn handle 并回收；未能在宽限内取回则明确 unknown，并注册迟到回收。
- artifact 的目录使用宿主 UUID，避免 task_id/call_id 路径注入及重名覆盖。
- Linux 替换弱 marker 测试为六种组合：shell/argv × cancel/忽略 TERM 超时/leader 先退出。fixture 等 ready 后触发，回收返回后取基线再观测 3 秒，检查无活跃子孙，finally 兜底清理。Linux `/proc` 判断区分不能运行的 zombie；这些分支仍未实测。

实际定向结果：首轮修补 **43 passed / 1 skipped**；后续含持久化与旧 oracle/runner 的故障修复选集 **64 passed**；额外恢复/取消选集 **24 passed**。最终全量结果见同日 [HP-04 接手报告](../HP-04/REPORT.md)。曾有一次全量因未加项目规定 PATH 导致 3 项旧 grader/oracle 环境失败，并暴露上述退出码竞态；均已修正前置或实现后复验，不隐藏该失败。

**结论：Windows 已覆盖部分可用；HP-03 仍待 Linux 平台验收，不签全平台通过。** 六个 Linux case 的 skip 不算通过。没有安装 WSL/Docker，没有连接远程机器；未调用付费模型。

参考项目 `C:\Users\23500\Desktop\src\learn-Codex-main` 不存在，未假称读过。保留用户修改 `docs/changes/SOLID-D2-REMAINING-CLOSEOUT.zh-CN.md`；没有提交/推送、修改 coding-agent。
