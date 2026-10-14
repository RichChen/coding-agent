# A0 核查记录

日期：2026-09-18；工作目录 `D:\crq\src\coding-agent`。本文件记录已执行检查，不是未来功能通过证明。

## 阅读、指令与复制

完整阅读三份目标文档及 `research-workflow/SKILL.md`、其 `references/research-contract.md`。首轮合并输出发生截断后分别补读目标文件尾部和 harness 全文，不以截断输出冒充完整阅读。没有读取 `.env` 内容，没有联网查询论文/JD。

仓库根目录/源码/tests/scripts/docs/configs/benchmarks/`.agents` 未发现 AGENTS.md；已检查 `D:\AGENTS.md`、`D:\crq\AGENTS.md`、`D:\crq\src\AGENTS.md`、本项目 AGENTS.md 均不存在。`.agents` 为空。全目录 `rg` 曾遇 `.tmp/pytest_basetemp` 访问错误，后续限定到相关目录，未修改权限或强读旧临时目录。

原件目录：`C:\Users\Administrator\Documents\Codex\2026-09-14\x20\outputs\project_upgrade`。写前检查本仓 `docs/upgrade/` 不存在同名目标文件；通过 apply_patch 新增。写后逐文件验证文本与字节 SHA256 全部一致：

| 文档 | 原件/副本共同 SHA256 |
|---|---|
| 00_双项目协作与接口约定_v0.1.md | `77EB8DD2E7A5FDC9A47EE04669A03077E797BD8A08ABF54D78FB14C6E8C306C9` |
| 01_coding-harness_总修改目标_v1.0.md | `1A9396E21228B7CDBE35A76AFEF4B2D5DBC3304289256243500C322DCEA1CDF2` |
| 02_coding-agent_总修改目标_v1.0.md | `CA71B7ECAC9D1BCC1A449F8446F894B4351B1E203FC6EEB7320B39D0DC97CB2F` |

一次哈希比较 PowerShell 命令因 foreach 直接接管道的语法错误未执行，修正为先收集数组后比较成功；没有通过 shell 写文件。

## Git 与源码记录

`git status --short` 失败：`fatal: not a git repository (or any of the parent directories): .git`。`.git` 为空普通目录，不是已有可用 repo；没有 init、commit、push。Git 无法据此判断用户脏改动。

`planning-source-manifest.json` 记录 102 文件（源码/测试/脚本/配置以及 README、pyproject、gitignore），UTC 捕获时间在文件内；限定排除 secrets、benchmarks、reports、traces、PDF 等。生成时机在只读检查和离线测试之后、产品实施之前；本轮未对这些产品文件执行编辑。该记录不含文件正文，非可恢复快照；实施前需要另做 allowlist snapshot。文档写入后复核 102 文件，changed=0；docs/upgrade 全部 Markdown 本地链接检查 broken=0。

## 解释器和工具

`Get-Command python` 指向 `C:\Users\Administrator\AppData\Local\Microsoft\WindowsApps\python.exe`，启动报“系统无法访问此文件”。没有把这个失败当作 Python 不支持项目。

已运行的解释器/版本检查：

```powershell
& 'C:\Users\Administrator\.conda\envs\coding-harness\python.exe' -c "import sys, importlib.metadata as m; print(sys.executable); print(sys.version); print({p:m.version(p) for p in ['pydantic','PyYAML','typer','rich','pytest','ruff']})"
```

输出：Python 3.11.15；pydantic 2.13.4、PyYAML 6.0、typer 0.25.1、rich 15.0.0、pytest 8.4.2、ruff 0.15.20。仅借用已有解释器，未安装/更新依赖。

## 已运行的定向测试命令

执行前阅读相关测试及 ModelClient/CLI 的调用路径，选用 mock/monkeypatch 测试，不调用付费 API；未运行会走真实配置的 script eval。PATH 仅对子进程有效，确保 fixture 内的 `python -m pytest` 能找到相同解释器。

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PATH='C:\Users\Administrator\.conda\envs\coding-harness;C:\Users\Administrator\.conda\envs\coding-harness\Scripts;' + $env:PATH
& 'C:\Users\Administrator\.conda\envs\coding-harness\python.exe' -m pytest tests/test_contracts.py tests/test_planner.py tests/test_memory.py tests/test_memory_matching.py tests/test_skills.py tests/test_skill_domain.py tests/test_injection_policy.py tests/test_llm_client.py tests/test_llm_developer.py tests/test_context_expansion.py tests/test_llm_call_state.py -q -o addopts='' -p no:cacheprovider --basetemp=traces/upgrade_plan_check_20260918
```

实测结果：`44 passed in 21.05s`，exit 0。产物在 `traces/upgrade_plan_check_20260918/`，独立于历史主报告。该命令是本次准确记录；再次运行不要复用已有 basetemp（pytest 会清理它），应选新唯一临时目录或省略 override。没有删除历史目录。

覆盖：旧合同/trace、planner、memory matching/store、skill/domain、router、mock client、LLM patch/repair、context expansion、跨任务 call-state reset。通过并不说明 realistic/oracle 隔离、真正 validity、独立 grader 或真实 OpenHands 已存在。未运行全套测试，特别未把这些 44 项称完整 suite。

## 已运行的静态与入口检查

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
& 'C:\Users\Administrator\.conda\envs\coding-harness\python.exe' -m ruff check reposkill_agent tests scripts --no-cache
& 'C:\Users\Administrator\.conda\envs\coding-harness\python.exe' -m reposkill_agent --help
```

Ruff：`All checks passed!`。CLI：exit 0，列出 `run-baseline`、`run-graph`、`list-tasks`；说明文字在当前终端部分编码显示异常，命令帮助结构可读。只查 help，未执行真实 run。新的 PublicTask/validity demo 命令本轮尚不存在，任务包中新增测试命令都明确标“新增后/未运行”。

## 历史证据核验

只读解析 `reports/llm/20260704_092308/llm-ablation-summary.json`：48 tasks、2 repeats、mock_llm=false、seed_memory=false、max_calls=3。L0/L2/L5 分别 96 行，44/68/77 成功；调用总数 99/153/147；对应 0.458333/0.708333/0.802083。核对同目录 Markdown 一致。未重新调用模型、未独立重验历史每个 patch、未复核历史费用/完整 provider snapshot，因此不声称本轮复现了历史分数。

旧源码路径可证明 fake adapter 与真实模型兼容，结合保存结果说明历史边界；不能仅凭当前源码证明运行时历史依赖完全相同。`docs/limitations.md` 已记录手工数据、旧负结果、repeat 内记忆、external baselines 未实跑和历史代码差异，计划保留这些说明。

## 未执行项与交付范围

未跑全套 suite/模型/容器/跨仓真实集成；未下载 benchmark；未读 keys；未改 `.env`、旧源码、旧报告或对方仓库。产品改造仍待用户开始指令。新增文档只在 `docs/upgrade/`，测试临时输出单列；没有把未来验收描述为已经通过。
