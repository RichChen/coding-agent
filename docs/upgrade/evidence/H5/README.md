# DeepSeek 真实调用验收证据

2026-09-21，Windows + Docker Desktop `desktop-linux`。结论：**Flash 非思考模式的真实 SSE / 工具 / Docker / 独立 grader 链路已验证**；H5 单仓真实任务与跨仓联调均已完成，R1 已按声明范围收口。完整范围和限制见 [R1 收口记录](../../R1-CLOSEOUT.zh-CN.md) 与 [H5-DEEPSEEK.zh-CN.md](../../H5-DEEPSEEK.zh-CN.md)。

## 结果入口

- [成功候选 patch](deepseek-flash-attempt-03/candidate.patch)：模型只改动 `boltons/strutils.py` 一行。
- [原版独立测试](deepseek-flash-attempt-03/baseline-evaluation.json)：8 passed / 10 failed / 18 collected。
- [候选独立测试](deepseek-flash-attempt-03/run/evaluation-result.json)：18 passed / 0 failed / 18 collected。
- [从冻结快照再次独立复验](independent-regrade/results.json)：新的 18 个容器，18/18 通过，无模型调用。
- [离线审计总账](audit/audit.json)：所有三次尝试计入，包括一次运行环境失败、一次源码准备失败；两次付费运行共 24 calls / 91,540 provider tokens。
- [最终全量回归](windows-regression-final.xml)：**316 passed、6 skipped、0 failed**，67.86 秒；其中真实 Docker **15 项全部执行通过**，新增 DeepSeek/源码校验 **8 项通过**。6 项 skip 为 Linux 原生进程组测试，在 Windows 宿主不支持，不能算通过。

`windows-regression.xml` 是新增源码校验测试前的 315 passed / 6 skipped；`docker-fix-regression.xml` 是 126/127 恢复、OOM/输出限额与当时 7 项 DeepSeek 测试的 10 passed 针对性回归。它们保留为过程证据，不代替最终文件。

## 三次尝试完整记录

1. `deepseek-flash-attempt-01/`：基线 8/18。真实模型正确修改并通过公开测试，但末尾执行不存在的 git，旧运行器将 127 错判为必须销毁会话，未获得候选快照。独立结果 `invalid_env`，不能算成功。12 calls / 45,546 tokens。
2. `deepseek-flash-attempt-02/`：下载原始上游文件时 `httpx.ReadError`，尚未创建模型运行、未调用模型。`preparation.json` 明确标注由原 CLI traceback 补录，不伪装成当时程序自动生成。
3. `deepseek-flash-attempt-03/`：126/127 恢复修补后，用首次下载的原版 seed 并核对硬编码 SHA256，基线仍为 8/18。12 calls / 45,994 tokens，候选 18/18。没有复用第一次已编辑候选，也没有覆盖失败目录。

本轮不是重复采样实验；不能用单次成功报告中的 100% 当成所有尝试的成功率。完整分母为三次启动尝试，其中两次进入模型阶段，一次最终获得独立通过结果。

## 可核对的身份和边界

固定公开报告：[mahmoud/boltons PR #475](https://github.com/mahmoud/boltons/pull/475)。修复前 commit：`967864f89791509f9eb36b22b4579d36b72a6df2`。切片只有两个原版上游文件和宿主编写的公开复现测试；没有运行完整上游套件。

所有付费尝试使用同一个 public task、base 和 private spec：

```text
base_hash:         24cb5b38cfcedf39aa712e0c86c779b32fbc5bb25b1fa4b266fe3e18529d36ec
private_spec_hash: f72355c6e0adf0281335ff11f695dec54fd5fdddeb6e866ef830b72af04c4cfd
public_task_hash:  ea4d968de5e1aeb82fc2c72d0d5f3ea82878f913fed2bb57b2577a069c5b0494
candidate_hash:    0ead6619edbe9e890c584610aaf162932c123abb6bf4bdb054336ff71b4c02cb
```

`sources.json` 保存 HTTPS 来源与原文件 SHA256，LICENSE 随切片保留。模型只收到公开 DTO；private spec 位于 seed 之外，从不传入模型或挂入容器。所有工具都在独立非特权 Linux 容器内执行，network=none，无宿主挂载；API key 仅由宿主 LLM client 使用。grader 在 agent 终止并清理后接收冻结候选，重建测试环境。

成功目录 `run/` 保留 manifest（含未提交源码 fingerprint）、base/candidate 快照、run-result、evaluation-result、导出的 events.jsonl、session 的 SQLite/原始观察/artifact 及离线报告 bundle。审计已证明：终态与只读 replay 相等、JSONL 与 SQLite 相等、候选 hash 在执行器/grader 一致、测试身份固定、报告离线重生成逐字节一致。原始日志按私有运行证据处理；精确扫描未发现当前配置 key。

## 复验命令

以下命令不调用模型；新 output 目录不可与已有目录重名：

```powershell
.\.venv\Scripts\python.exe scripts/run_grader.py --assignments docs/upgrade/evidence/H5/regrade-assignments.json --output-dir runs/deepseek-regrade-new
.\.venv\Scripts\python.exe scripts/audit_deepseek.py --evidence-root docs/upgrade/evidence/H5 --output-dir runs/deepseek-audit-new --check-key-config configs/deepseek.yaml
```

grader 需要 Docker；审计无需 Docker/网络，仅 `--check-key-config` 读取当前配置 key 作精确泄漏比对，不会输出它。首次网络模型列表查询返回 `deepseek-flash`、`deepseek-v4-pro`；实际修复只使用 Flash。官方价格/模型别名可能变化，本次映射与费用估算以 2026-09-21 为准，不声称模型权重快照固定或费用已经与账户账单核销。
