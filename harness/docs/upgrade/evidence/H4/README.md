# H4 验收（2026-09-20）

结论：H3 未发现新增阻断项，进入并完成 H4 基础版。none/masking 窗口策略、原始历史与模型视图分离、no-op/fixture 插件、宿主注入额度与审计、持久恢复已验收。summary 与 mask-then-summary 的摘要生成仍为明确标记的本地 fixture，不是实际 LLM 摘要或质量实验。

## 最终结果

| 验证 | 实际结果 | 证据 |
| --- | --- | --- |
| 全量 Windows 测试，显式启用 Docker | **306 passed / 6 skipped / 0 failed / 0 errors**，62.72s | `windows-regression-final.xml`，312 tests |
| H4 新增行为测试 | **21 passed**（窗口/插件 15，loop/恢复 6） | `tests/test_context_window.py`、`tests/test_h4_loop.py` 对应 JUnit |
| H3 真实 Docker 复验 | **13 passed** | 同一 JUnit，`h3-regression-final/` |
| H3 mock 模型 → 容器修复 → 独立 grader | grader pass，容器清理成功 | `h3-regression-final/e2e/evaluation-result.json` |
| none 超额 | provider/model 和工具调用均为零 | `test_preflight_overflow_has_zero_model_calls_and_no_tool_effect` |
| raw 与 view 分离 | 原始 20KB 观察仍在 session/operation；模型视图已遮蔽 | `final-02/raw-view.json`、对应测试 |
| 真实进程退出后恢复 | 子进程退出码 73；复用已准备 view；插件调用次数仍为 2；文件追加仅一次 | `test_real_crash_restores_prepared_view_without_duplicate_plugin_or_effect` |
| 配置变化 / 新任务 | 恢复时拒绝变更策略；新任务不继承上一任务插件状态 | 对应两个测试 |
| 插件边界 | 有效候选注入、旧版本/超额拒绝、未知 major 拒绝、minor 可选字段兼容、私有字段拒绝、actions 不执行 | 对应窗口测试 |
| 异步插件卡住 | deadline / cancel 都停止，无模型调用 | `test_plugin_await_obeys_deadline_and_cancel` |
| 同轨迹四策略演示 | none/masking 拒绝；两个摘要 fixture 形成合法视图，3 条候选仅注入 1 条 | `demo-final/manifest.json`、`results.json`、`report.md` |

6 项 skip 是 Windows 无法直接执行的 Linux 原生进程组测试；H3 上一轮已在真实 WSL2 Linux 容器跑过 6 passed，本轮未改该后端，不重复把旧证据记成新运行。H3 的 Docker 验收本轮全部实际运行，未跳过。

## 实际命令

```powershell
$env:PATH='D:\crq\base\Anaconda3;D:\crq\base\Anaconda3\Scripts;' + $env:PATH
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONDONTWRITEBYTECODE='1'
$env:HARNESS_DOCKER_TESTS='1'
$env:HARNESS_H3_EVIDENCE='docs/upgrade/evidence/H4/h3-regression-final'
$env:HARNESS_H4_EVIDENCE='docs/upgrade/evidence/H4/final-02'
$env:HTTP_PROXY=$null; $env:HTTPS_PROXY=$null; $env:ALL_PROXY=$null
$env:NO_PROXY='127.0.0.1,localhost'
.\.venv\Scripts\python.exe -m pytest tests -q -p no:cacheprovider --tb=short --basetemp=tmp/h4-full-final --junitxml=docs/upgrade/evidence/H4/windows-regression-final.xml

.\.venv\Scripts\python.exe scripts/demo_h4.py --output-dir docs/upgrade/evidence/H4/demo-final
git diff --check
```

复跑请更换 evidence/output/basetemp 路径，保持原始证据。Docker/pytest 临时目录访问使用了获准的宿主执行权限。

## 保留的调试记录

首轮针对性测试暴露模块初始化循环引用，已移至实际调用时加载。第二轮旧 compact 测试发现旧事件约定变化，恢复了 `context_compacted` 兼容事件与 compact-only 列表语义。摘要额度测试原来保留三条近期大观察，按规则无法放入小窗口；改为明确保留一条后验证摘要状态继承，而没有降低保护规则。

`windows-regression.xml` 是新增跨任务清空状态测试前的 **305 passed / 6 skipped**。`windows-regression-final.xml` 是增加该修补和测试后的最终结果；`demo-01`、`h3-regression`、`final` 为此前证据，均保留。

## 范围边界

本轮无真实/付费模型调用，无 coding-agent 仓库改动，无真实 RepoSkill 连接。模型窗口值必须按实际 provider 配置；UTF-8 字节准入是保守工程额度，provider usage 单列。插件为受信进程内代码，公开 JSON 接口不构成恶意 Python 的隔离边界。真实 LLM 摘要、插件主动工具/模型调度和跨仓适配未声称完成。

完整设计与用法见 [H4 说明](../../H4-IMPLEMENTATION.zh-CN.md)。
