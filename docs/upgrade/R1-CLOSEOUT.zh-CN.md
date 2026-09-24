# R1 收口记录

日期：2026-09-21。本文是 `IMPLEMENTATION-PLAN.md` 中 R1 里程碑的收口记录，按已保存的实现、测试和运行证据核对，不代表发布版本号。

## 结论

R1 在声明范围内完成。范围是 H1–H3、H4 的接口/`none`/`masking`，以及至少一个真实模型驱动的端到端修复任务。真实 Docker/Linux 后端、独立 grader、持久事件与可重放产物均有实际证据；H5 的真实 DeepSeek Flash 单仓修复和一次 RepoSkill 跨仓联调也已完成。

这次收口不把历史失败尝试改写成成功，也不把单任务结果解释成修复率、策略收益或基准成绩。`real-02`、DeepSeek `attempt-01/02` 等目录继续保留，并按 `invalid_env` 或准备失败计入相应分母。

## R1 对照矩阵

| R1 要求 | 当前结果 | 主要证据 |
| --- | --- | --- |
| 故障 demo：非法/断流调用不执行、取消阻止后续写、输出和环境有界 | 通过。工具参数、流式聚合、deadline/cancel、输出额度和受控环境均有回归；无模型的反例可重复。 | [HP-01](evidence/HP-01/REPORT.md)、[HP-02](evidence/HP-02/REPORT.md)、[HP-03](evidence/HP-03/CODEX-ACCEPTANCE-20260919.md)、[H5 最终回归](evidence/H5/windows-regression-final.xml) |
| 写后崩溃与四窗口恢复、replay/resume | 通过。跨进程 fixture 覆盖 intent 前、intent 后、效果后和 result 后；非幂等副作用保守为 `unknown`，replay 不调用执行器。 | [HP-04](evidence/HP-04/REPORT.md)、[会话使用说明](SESSION-USAGE.zh-CN.md) |
| 真实 Docker/Linux 隔离、资源、取消和销毁 | 通过。Docker Desktop `desktop-linux` / WSL2 上真实运行；无宿主挂载、默认无网络、资源限制、后代进程清理和遗留容器检查均有证据。 | [H3 验收](evidence/H3/README.md)、[H3 final](evidence/H3/final/)、[H5 Docker 回归](evidence/H5/docker-regression-final/) |
| 独立验证方与完整分母 | 通过。公开任务与私有 spec 分离，候选冻结后由独立 grader 重建；采集数、失败和 `invalid_env` 不被剔除，报告可离线重建。 | [H3 验收](evidence/H3/README.md)、[DeepSeek 证据](evidence/H5/README.md) |
| 真实端到端修复任务 | 通过一次明确成功。固定 `mahmoud/boltons` PR #475 切片由 DeepSeek Flash 修改，独立黑盒 18/18 通过；完整三次启动分母和费用/用量均保留。 | [H5 说明](H5-DEEPSEEK.zh-CN.md)、[H5 证据](evidence/H5/README.md)、[独立复验](evidence/H5/independent-regrade/) |
| manifest/events/artifacts/run/evaluation/report 可关联、可重放 | 通过。成功运行保存 SQLite session、JSONL、artifact、manifest、run/evaluation result 和离线 report；审计核对 SQLite/JSONL、replay 状态、候选 hash 与报告重生成。 | [DeepSeek attempt-03](evidence/H5/deepseek-flash-attempt-03/run/)、[H5 audit](evidence/H5/audit/audit.json)、[H3 e2e](evidence/H3/final/e2e/) |
| README、预算、恢复和机制案例 | 通过。H3/H4/H5/会话说明及本收口文档已链接；超时清理、写后崩溃、窗口/插件和真实任务的正负边界均有记录。 | [H3 实现说明](H3-IMPLEMENTATION.zh-CN.md)、[H4 实现说明](H4-IMPLEMENTATION.zh-CN.md)、[H5 跨仓报告](H5-INTEROP.zh-CN.md) |

## H4/H5 联调状态

`real-04` 是当前唯一计入 dispatcher 联调成功的 full-host 证据：插件 off/on 各 4 次 Flash 调用，独立 grader 均 4/4；on 变体有 2 个候选注入、3 个被宿主拒绝的 action proposal、`plugin.dispatch` journal、replay、key/canary 检查。宿主只开放固定 Docker workspace 内的 `read`/`search`，shell、写入、绝对路径、父级遍历和隐藏路径均拒绝。历史 `real-01`、受限环境的 `real-02` 和顺序错误的 `real-03` 不覆盖该结论。

## 明确保留的限制

- grader 是固定 Python 函数/JSON 黑盒 runner，不是任意 pytest 仓库适配器。
- 宿主被强杀或 Docker daemon 长时间不可达时，不承诺自动恢复旧容器；需按 session 记录的容器名核查后新建 run。
- 真实模型只验收 DeepSeek Flash、非思考模式；Pro、真实思考字段回放和真实 LLM 摘要没有验收。
- H4 插件是受信进程内 Python；注册/指纹和 dispatcher 是宿主治理边界，不是恶意插件沙箱。
- 联调是单个合成公开任务的机制烟测，不能推导性能、修复率或策略收益。

## 停止点

R1 到此收口。本轮不开始 R2、Pro/思考模式、多任务或性能实验、完整 SWE-bench/上游套件统计，也不新增真实模型调用。后续若继续，应先另立范围和证据合同。
