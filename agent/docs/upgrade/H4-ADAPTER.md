# H4 async PolicyPlugin 适配与单任务交接

2026-09-21 后续状态更新（保留下文 H4 当时快照）：只读核对 harness 的 `R1-CLOSEOUT.zh-CN.md`、`H5-INTEROP.zh-CN.md` 及 `evidence/H5-interop/real-04/summary.json`，外部插件受控注册和 read/search dispatcher 已实现，真实 off/on 各 4 calls、grader 各 4/4。H4 adapter、fixture 生成器和测试的 SHA256 与本仓 H4 review manifest 一致，A5 未修改这些实现。`real-04` 的 on 摘要为 requested=2、prepared_view_injections=5、proposals_rejected=3；不要把旧文中的 2/2 表格当该批最新计数，也不要将 prepared-view 自动映射成模型采用。A5 本轮不重跑 H4/跨仓真实 API；证据路径与限制见 [A5-VERIFICATION](A5-VERIFICATION.md)。

2026-09-21。本批只完成 coding-agent 内的 adapter、单仓合同测试和一个合成任务包；只读核对 coding-harness H4 源码，没有修改对方仓库、导入/运行对方 runtime、调用 API 或启动跨仓联调。

## 对齐的实际接口

核对对象为 `src/policy/plugin.py`、`src/runtime/window.py`、`src/runtime/loop.py`、`src/runtime/session.py` 和 H3 evaluator。读取时的 SHA256 见 [h4-reference-lock.json](h4-reference-lock.json)；这是对齐依据，不是对方发布的正式新协议。

| H4 当前行为 | 本仓映射 |
| --- | --- |
| `async decide(policy_input: dict) -> dict`，wire 0.1 | `RepoSkillH4Plugin` 结构化兼容，不继承或导入对方内部类 |
| 输入 task、message role/hash、repo_revision、budget、state | 仅接纳这些公开字段；未知 major 拒绝，新 minor 扩展丢弃，禁止字段在丢弃前仍检查 |
| loop 的 task 是 task_id/issue_text，H3 又在 issue_text 内序列化 PublicTask | 同时验证最小 loop 形态、完整 H3 公开形态及其 JSON wrapper；任务 ID、描述和 revision 必须匹配 |
| 返回 candidates、state、events、action_proposals | 候选含 id/text/source/reason/priority/valid/repo_revision；state 是普通 JSON；事件不分配宿主序号 |
| proposals 全部拒绝 `dispatcher_not_enabled` | 只提交语义 read/search 建议，不执行、不改成 shell，不记作 tool calls；候选把公开树定位建议提供给主模型 |
| observations 只有 role/hash | 不把 hash 当代码正文，不打开文件或查宿主路径；已有纯 locator 的正文 observation 接口仍保留供将来接入 |
| 宿主账本与窗口控制唯一 | 插件无 client/executor/网络/价格账本，不占用独立模型预算；本地 proposal 数是建议上限，不是宿主消费计数 |
| host prepared-view 中 requested/actually_injected/rejected | adapter 只记 selected/requested 意图；没有模型 operation/attempt 收据就不生成 Memory UseRecord.actually_injected |

入口：[harness_h4.py](../../reposkill_agent/integrations/harness_h4.py)。不改原 `PublicTask` 1.0：本仓数据 DTO 1.0 与 H4 wire 0.1 是不同层。`harness_public_task()` 显式投影到 H3 字段，绝不把完整原对象或私有 EvaluationSpec 附加到 metadata。

最小构造（在未来宿主集成代码中，由可信准备器提供 task 和已审阅 public tree）：

```python
from reposkill_agent.integrations.harness_h4 import RepoSkillH4Plugin

plugin = RepoSkillH4Plugin(public_task, public_tree)
decision = await plugin.decide(h4_policy_input)
# 宿主自行审查候选并执行唯一模型调用；adapter 不执行 decision。
```

`enabled=False` 在有效输入上返回与 H4 NoOp 相同的空 candidates/state/events/proposals。开关两侧没有第二个模型客户端，未运行旧 GraphRunner。

## 状态和保守行为

状态绑定 adapter version、公开任务、tree、memory snapshot、RepoFacts 和 source policy 的 hash。恢复由下一轮输入的 state 完成；新插件实例得到同样的下一轮结果。空 state 表示新 run，不复用实例历史。旧 proposal IDs 留存，已提交 read 不会重提；后续 search 可继续提出，仍不代表已执行。receipt cursor 保持 null。

入口/出口均限制为有限 JSON、64 KiB，错误不回显私有值。async decide 首先提供取消点；计算是有界的本地规则，没有同步网络/I/O、嵌套 asyncio.run 或自建重试。宿主负责 deadline 和最终取消语义；这不是恶意进程内插件的 OS 隔离。

可选 memory 必须由调用方提供冻结的 `MemoryRecord + RepoFacts + SourcePolicy`，使用已有 provenance/validity gate。任何 tool history 出现后，本版都停用这些初始 facts 对应的 memory，即使 base_revision 未变，避免文件已改却继续相信旧事实。H4 缺正文/版本更新通道时不会自动刷新。默认交接样例为空 memory，也不加载未经 provenance 审核的旧 SkillCard。

## 一个公开任务与独立私有评测

生成器：[h4_fixture.py](../../reposkill_agent/eval/h4_fixture.py)；入口：[prepare_h4_fixture.py](../../scripts/prepare_h4_fixture.py)。这属于私有数据准备侧，不是插件依赖。

任务 `public-settings-001`：修复 `parse_settings` 对空行、空白和值中等号的处理。公开目录只有原始错误源码 `settings.py` 和 `public_checks.py`，可以复现空行异常；没有 gold patch、私有探针或目标未来轨迹。

已生成的 任务包 manifest（本地生成，未入库：`reports/upgrade/h4-handoff-20260921-v2/manifest.json`） 固定公开源码与所有 artifact hash：

- `agent-public-task.json`：本仓 PublicTask 1.0。
- `public-task.json`：未来 H3 `PublicTask.from_mapping` 可接收的字段形态。
- `public-workspace/`：唯一可给 agent 挂载的目录，不能挂载交接包根目录或本项目根目录。
- `private/evaluation-spec.json`：H3 `EvaluationSpec.from_mapping` 的形态，固定 4 个黑盒函数探针、editable_paths、base_hash 和 digest-pinned image；expected 仅给后置 grader。
- `private/agent-evaluation-index.json`：本仓独立 EvaluationSpec，用于记录私有引用，不传给插件。
- `fixture/`：实际 wire 样例和本地调用 adapter 得到的开/关 decisions，尚非 harness 调用或模型注入记录。

base hash 使用 H3 的 canonical(path→内容 SHA256) 算法，区别于本仓 export audit hash。image 引用来自 harness H3 证据中的固定 digest；本轮没有拉取镜像或验证可用性。public budget 明示最多 4 次模型调用/120 秒；其余宿主窗口、步数、token 和费用上限单列 manifest，不能假装本仓 input/output token 配额已由 H4 逐项执行。

生成新的交接目录（不覆盖旧证据、不读 API key）：

```powershell
python scripts/prepare_h4_fixture.py --output reports/upgrade/h4-new-bundle --image coding-harness-h3-tests@sha256:18872d18b9bc347cf4441b1d9b53b9662ea719f057bd471c7d4cbfce4dc2e78e
```

## 跨仓联调前仍需满足的条件

当前 `RunSession._run_impl` 明确只允许内置 NoOpPolicyPlugin/FixturePolicyPlugin。外部 RepoSkill 插件不能直接进入持久 H3 run；本仓不继承 FixturePolicyPlugin 冒充内置插件，也不绕过该检查。未来宿主需要受控的自定义插件注册及配置指纹，指纹必须覆盖公开任务、tree、snapshot 和 adapter version，不能只覆盖 name/version。

按用户指定顺序，等 harness 单独真实运行通过并保留证据后，再做一次跨仓联调，插件关/开各一个 fresh run。两次用同一个公开 seed、私有 spec、模型配置、预算、窗口策略和空 memory；分别保留模型调用账本、context.prepared、requested/注入/拒绝记录、proposal 拒绝原因、candidate snapshot 与独立 grader 结果。失败照常保留，不按答案调整预算重跑。这是链路烟测，不据两个样本推断修复率提升。

如果到时仍没有 dispatcher，联调仅验证“候选增强 + 模型原有工具调用”；不能标为插件工具执行。如果仍只提供 prepared-view 注入 metadata，不映射成带 operation/attempt 的本仓 InjectionReceipt。费用上限需随实际 provider 价目冻结，manifest 的 `real_api_ready=false` 明确表示当前准备包不会自动发起收费运行。

## 单仓验证

`tests/test_harness_h4_adapter.py` 覆盖 wire shape、NoOp、H3 wrapper、公开/私有 sentinel、unknown major/minor、64 KiB/NaN、任务/revision/snapshot 绑定、恢复后不重复 proposal、独立新 run、取消、初始 memory 拒绝/选中与工具后停用、公开源码复现、artifact hash、私有答案不干扰决策。测试不依赖 coding-harness 安装。

2026-09-21 扩大回归：183 passed，58.46 秒；最终对齐 fixture 的消息 hash 后，定向复验：35 passed，0.63 秒；Ruff 全仓通过。JUnit：adapter-final.xml（本地生成，未入库：`reports/upgrade/h4-verification-20260921/adapter-final.xml`）、regression.xml（本地生成，未入库：`reports/upgrade/h4-verification-20260921/regression.xml`）。两组有重叠，不相加计数。此轮 Windows 符号链接测试也通过；仍不代表 OS 沙箱隔离验收。旧交接目录保留，后续使用 v2 目录，其中 raw-messages 与 role/hash 按 H4 的消息对象 hash 算法绑定。

回归使用现有 Conda 解释器/PATH，无依赖安装；沙箱内 pytest basetemp 触发 WinError 5 后，经执行审批重跑离线测试。旧 CLI 写默认报告、外部 baseline 和 benchmark 全集不在本次扩大回归内；旧报告和失败证据未覆盖。实际命令：

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PATH='C:\Users\Administrator\.conda\envs\coding-harness;C:\Users\Administrator\.conda\envs\coding-harness\Scripts;' + $env:PATH
& 'C:\Users\Administrator\.conda\envs\coding-harness\python.exe' -m pytest tests --ignore=tests/test_cli.py --ignore=tests/test_llm_ablation.py --ignore=tests/test_external_baselines.py --ignore=tests/test_phase7_benchmark.py -q -o addopts='' -p no:cacheprovider --basetemp=traces/upgrade_h4_regression_20260921_01 --junitxml=reports/upgrade/h4-verification-20260921/regression.xml
```

复跑需更换 basetemp/output，避免 pytest 清空已保留的测试证据目录。
