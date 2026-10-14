# H5 单仓真实模型接入：DeepSeek Flash

2026-09-21。完成真实模型 → Docker 工具循环 → 冻结候选 → 独立 grader 的首条链路，不依赖 coding-agent 插件。**这是 H5 的单仓部分；R1 总体收口见 [R1 收口记录](R1-CLOSEOUT.zh-CN.md)。**

随后完成跨仓准备与联调，见 [H5 跨仓联调报告](H5-INTEROP.zh-CN.md)。本文件的单仓证据仍独立保留。

## 验证结果

任务取自 [boltons 公开缺陷报告 PR #475](https://github.com/mahmoud/boltons/pull/475)，固定修复前 commit `967864f89791509f9eb36b22b4579d36b72a6df2`。仅取原版 `boltons/strutils.py` 和 LICENSE，附加 3 个宿主编写的公开复现测试；不是完整仓库测试或 SWE-bench 任务。没有把上游修复 patch、PR 解决方案正文、私有用例或预期答案提供给模型。

模型仅能编辑 `boltons/strutils.py`。18 项独立黑盒探针在模型调用前冻结，覆盖 Unicode 分隔符、普通数字文本、混合换行、空行、自定义换行及两个无关函数回归。每项探针使用独立的新容器，预期值留在宿主，不能通过修改测试或打印成功标记蒙混过关。

| 尝试 | 真实调用 | provider tokens | 独立结果 |
| --- | ---: | ---: | --- |
| attempt-01 | 12 | 45,546 | `invalid_env`：命令不存在被运行器错误升级为会话终止，没有候选快照 |
| attempt-02 | 0 | 0（尚未调用） | `invalid_env`：源码下载阶段 HTTP ReadError |
| attempt-03 | 12 | 45,994 | 原版 8/18 → 模型候选 18/18 |

三次尝试均保留。第一次模型自己运行的公开测试虽通过，也没有当成独立成功证据。第三次只有一行源码差异，由真实模型通过 `edit_file` 产生，宿主没有代写修复。源码下载失败后增加 `--source-dir`，仅接受与固定上游 SHA256 一致的原始文件，不能用已修复版本作为基线。

证据及最终回归统计见 [evidence/H5/README.md](evidence/H5/README.md)。这不是统计实验，不能用这一个缺陷宣称模型修复率或策略收益。

## 官方 API 协议

2026-09-21 实际读取并核对：

- [模型与价格](https://api-docs.deepseek.com/quick_start/pricing)：`deepseek-flash`（当日文档映射 DeepSeek-V4.1-Flash）、`deepseek-v4-pro`（DeepSeek-V4-Pro-0813）；模型列表 API 对现有账号也返回这两个 ID。
- [思考模式与工具回传](https://api-docs.deepseek.com/guides/thinking_mode)：默认开启思考；携带 tools 时须回传历史 `reasoning_content`。
- 本轮显式发送 `"thinking":{"type":"disabled"}`，使用真实 SSE 流和多轮 tool call/result。普通兼容配置默认为 `None`，不擅自给其他 provider 加 DeepSeek 参数。

`llm.thinking` 当前只接受 `disabled` 或未配置。`enabled` 明确拒绝，因为还没实现完整 reasoning replay；不能只打开该参数就声称支持思考模式。新字段进入持久会话配置指纹，防止改变模式后误恢复。H4 wire `0.1`、插件 DTO 和 no-op 行为不变。

本轮端到端只运行了 Flash，**没有实测 Pro 或思考模式**。记录的是请求模型 ID 与当日官方版本映射，不是不可变模型权重快照。

## 用量与费用

保留 provider 的 prompt/completion/total、cache hit/miss、可选 reasoning tokens 计数，流式和非流式统一处理。不保存任意额外 provider 字段。缺失数据仍为 unknown/null。

全部付费尝试合计 **24 次调用、91,540 tokens**：输入 88,098，输出 3,442；输入缓存命中 43,008，未命中 45,090。没有隐藏失败轮次、摘要费或插件调用：本轮摘要没有发生，插件为 no-op，grader 不调用模型。

官方当日 Flash 每百万 tokens 峰时美元价：缓存命中 $0.006、未命中 $0.30、输出 $1.20；非峰时半价。按返回的缓存计数估算全轮费用区间 **$0.00896–$0.01792**。未核对账户账单/优惠，实际 `cost_usd` 留 null；这不是精确扣费声明。价格版本及公式随证据保存。

用户已授权真实 token 使用；配置仍有每 run 的安全限额：40 步、50 次模型 attempt、1,000,000 累计 tokens、单步 120 秒、总计 1200 秒，最大输出 8192 tokens。请求窗口准入 131072 是保守本地配置，不宣称等于官方 1M 上下文容量的实测值。

## 运行方式

密钥沿用 `.env` 的 `LLM_API_KEY` 或同名环境变量；不要粘贴到命令、配置文件或报告。`configs/deepseek.yaml` 固定官方 HTTPS 端点，默认 Flash，不受旧 `.env` 的 `LLM_MODEL=deepseek-v4-pro` 影响。模型运行容器 network=none、无宿主挂载、无 API key；网络请求只由宿主客户端发起。

```powershell
.\.venv\Scripts\python.exe scripts/run_deepseek.py --allow-paid --output-dir runs/deepseek-new-attempt
```

输出目录必须不存在。固定镜像必须预先可用；没有 Docker、无法复现基线或未配置 key 时不继续付费模型阶段。不自动安装 git、pytest 或下载容器依赖。

复用已下载原版文件（仍校验硬编码 SHA256）：

```powershell
.\.venv\Scripts\python.exe scripts/run_deepseek.py --allow-paid --source-dir docs/upgrade/evidence/H5/deepseek-flash-attempt-01/seed --output-dir runs/deepseek-new-attempt
```

可用 `DEEPSEEK_MODEL=deepseek-v4-pro` 切换模型；这只是配置入口，不是 Pro 已验收。只运行 `--help` 或离线审计不消费 tokens。

离线核对所有已记录尝试、SQLite 与 JSONL 一致性、终态 replay、快照/spec 身份、用量总账和报告重生成：

```powershell
.\.venv\Scripts\python.exe scripts/audit_deepseek.py --evidence-root docs/upgrade/evidence/H5 --output-dir runs/deepseek-audit-new --check-key-config configs/deepseek.yaml
```

`--check-key-config` 只做当前配置 key 的精确字节泄漏检查，不输出 key，也不声称是通用秘密扫描器。原始会话及 artifact 仍按私有运行证据对待。

## 本轮发现并修补的执行问题

首次真实运行末尾调用不存在的 git，shell 返回 127。原 Docker 后端将 126/127/137 全部当严重资源/执行故障，导致已经改好的文件来不及快照。现在 126/127 作为可恢复的 `nonzero_exit` 工具失败返回，模型能换用其他工具；137（SIGKILL/OOM）、输出超限、超时及取消仍销毁整个会话。新增两个真实 Docker 测试验证失败后可继续执行且候选被保存，原 OOM/输出限额测试同时通过。没有放宽宿主挂载、网络、资源或私有测试边界。

## 仍未纳入本轮验收的部分

coding-agent/RepoSkill 的 dispatcher-enabled full-host off/on 重跑已在 `H5-INTEROP.zh-CN.md` / `evidence/H5-interop/real-04/` 收口，未改对方仓库。仍未实现真实模型摘要或思考字段完整回传；未跑 Pro；未跑完整 boltons 上游测试或官方基准；未做多任务/策略对照实验。H3 的任意 pytest 仓库适配和 Docker 硬中断自动恢复限制不变。

AGENTS.md 指向的参考目录 `C:\Users\23500\Desktop\src\learn-Codex-main` 本机不存在，本轮未声称已读取该参考实现；沿用本仓现有网关/运行器边界做窄改动。
