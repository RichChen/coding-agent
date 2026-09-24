# H0 现场基线与证据

日期：2026-09-18。本文记录本轮实际执行的检查、文档保存与离线测试，不是产品功能完成声明。

## 仓库和用户工作

- 仓库：`D:\crq\src\coding-harness`。
- HEAD：`1f5903b620895ad8af3289ffeae529c15c3576a0`，`docs(d2): demo script and interview materials A-D closeout`。未 fetch 远端。
- 起始 git status 只有 `docs/changes/SOLID-D2-REMAINING-CLOSEOUT.zh-CN.md` 修改。未编辑；起始 SHA-256 为 `0768AEE687387CB07164E51DCBA8500A8337DD6EFA4E6C6593468FA799B222BE`。
- 本轮只新增 docs/upgrade 文档，未改 src/tests/configs/datasets，未提交/推送。

## 原文与参考

已完整读取根 AGENTS.md 和三份目标文档。docs/upgrade 起始不存在，使用文件编辑工具新增后，以下副本与来源逐字节 hash 一致：

| 原文文件 | SHA-256 |
|---|---|
| 01_coding-harness_总修改目标_v1.0.md | 1A9396E21228B7CDBE35A76AFEF4B2D5DBC3304289256243500C322DCEA1CDF2 |
| 00_双项目协作与接口约定_v0.1.md | 77EB8DD2E7A5FDC9A47EE04669A03077E797BD8A08ABF54D78FB14C6E8C306C9 |
| 02_coding-agent_总修改目标_v1.0.md | CA71B7ECAC9D1BCC1A449F8446F894B4351B1E203FC6EEB7320B39D0DC97CB2F |

来源目录：`C:\Users\Administrator\Documents\Codex\2026-09-14\x20\outputs\project_upgrade`。保持原文版本与内容，不在副本里修改公共契约。

指定参考 `C:\Users\23500\Desktop\src\learn-Codex-main` 不存在；候选 `D:\crq\src\learn-Codex-main`、`C:\Users\Administrator\Desktop\src\learn-Codex-main` 也不存在。D:\crq\src 仅发现名字不同的 learn-claude-code-main 和 learn-fastapi-langgraph；未把它们当作同一参考，未宣称读过 s_full.py。

本轮不重新联网核验岗位/论文，不读取或修改协作方源码。coding-agent 现状描述引用其目标交接，不冒充本轮对对方仓库的独立审计。

## 工具与依赖

| 项目 | 观察 |
|---|---|
| 默认 python | WindowsApps alias，无法启动 |
| 实际解释器 | D:\crq\base\Anaconda3\python.exe，Python 3.13.9 |
| 已有库 | pytest 8.4.2、httpx 0.28.1、pydantic 2.12.4、PyYAML 6.0.3 |
| 缺失库 | pytest-asyncio |
| 其他已有 conda | rsdet/tarsg 都是 Python 3.10.20，且缺关键项目依赖，不满足完整验收 |
| Docker | PATH 未发现 docker，不代表遍历磁盘证明没有安装，但当前无可用后端证据 |
| WSL | wsl --status 退出 1，无诊断文本，本轮未证实可用 Linux 环境 |
| CLI | run_single.py --help、run_eval.py --help 均 exit 0，仅核实参数入口 |

## 实际测试基线 C0

沙箱内首次运行：72 passed、31 skipped、45 errors。45 个 setup 错误为 pytest 访问 `C:\Users\Administrator\AppData\Local\Temp\pytest-of-Administrator` 时 PermissionError，不归因于产品代码。按执行环境审批流程获准后，沙箱外用同一代码/解释器重跑：

```text
117 passed, 31 skipped, 1 warning in 18.34s
PytestConfigWarning: Unknown config option: asyncio_mode
```

conftest.py 在缺 pytest-asyncio 时跳过 coroutine tests，warning 同样来自插件缺失。31 skipped 不算通过；历史文档的“148 passed”不是当前完整基线。没有安装依赖或修改 conftest 来制造绿灯。

实际命令（PowerShell，仓库根目录；沙箱外重跑版）：

```powershell
$env:PATH='D:\crq\base\Anaconda3;D:\crq\base\Anaconda3\Scripts;' + $env:PATH
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONDONTWRITEBYTECODE='1'
& 'D:\crq\base\Anaconda3\python.exe' -m pytest tests -q -p no:cacheprovider --tb=short
```

若未来使用 --basetemp，必须使用经确认的专用临时子目录；pytest 可能清理已有 basetemp，不能使用仓库根/用户目录。测试框架临时输出不是产品源码改动。

已有测试文件均被 C0 收集。没有为各包重复运行相同子集；新测试入口在 TASK-PACKAGES.md 明确标“计划新增”，尚未运行。HP-01 须使用项目专用 Python >=3.11 和完整 dev 依赖重新验收。

## 已执行的无网络行为反例

P1：非法 JSON、空白名单和缺 usage。使用假 URL/凭据，仅调用本地函数，不发请求、不创建工具进程：

```powershell
& 'D:\crq\base\Anaconda3\python.exe' -c 'from src.llm.client import LLMClient; from src.tools.command import RunCommandTool; c=LLMClient("https://unused.invalid", "fake", "fixture"); r=c._parse_response({"choices":[{"message":{"tool_calls":[{"id":"t1","function":{"name":"write_file","arguments":"{"}}]}}]}); print("invalid_json_arguments=",r.tool_calls[0].arguments); print("empty_allowlist_inherits=",RunCommandTool._build_subprocess_env([]) is None); print("absent_usage=",r.usage)'
```

结果：

```text
invalid_json_arguments= {}
empty_allowlist_inherits= True
absent_usage= {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}
```

P2：重复评测主均值排除异常轮，与完整分母不同：

```powershell
& 'D:\crq\base\Anaconda3\python.exe' -c 'from src.eval.metrics import EvalMetrics,aggregate_repeated_metrics; a=EvalMetrics(config_name="x",total_tasks=1,passed=1,success_rate=100,avg_steps=2); b=EvalMetrics(config_name="x",total_tasks=1,failed=1,success_rate=0,avg_steps=0,model_error_count=1); r=aggregate_repeated_metrics("x",[a,b]); print("runs=",r.run_count,"valid_runs=",r.valid_run_count,"reported_mean=",r.success_rate.mean,"all_assigned_rate=",50)'
```

结果：`runs= 2 valid_runs= 1 reported_mean= 100 all_assigned_rate= 50`。旧实现仍保留原始 runs，但主统计过滤了异常轮；新协议要保留全分母，旧报告不覆盖。

其他风险均按源码符号记录在 IMPLEMENTATION-PLAN.md：本轮没有派生失控进程来复现超时泄漏，没有容器验证或崩溃恢复演示；这些是后续任务包的验收内容。

## 已核实的 CLI help

```powershell
& 'D:\crq\base\Anaconda3\python.exe' scripts/run_single.py --help
& 'D:\crq\base\Anaconda3\python.exe' scripts/run_eval.py --help
```

single 支持 task/--config/--workspace；eval 支持 --dataset/--configs/--compare/--runs/--cost-per-1k。当前不存在 resume/replay/offline-demo 的 CLI 验收证据；计划中的新入口必须实现后再核实。

## 证据限制

没有付费模型调用、真实 provider stream、真实 Docker/Linux、CPU/网络隔离结果；没有大规模下载。三份目标中的技术与岗位材料仅作为交接背景，不能称已复现或全国调研完成。后续每包记录解释器、命令、exit、passed/failed/skipped、平台、事件/产物路径和剩余限制。
