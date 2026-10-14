# coding-agent

[English](README.md) · **中文**

一个带严格答案隔离的 coding agent 评测 harness，加上在它上面做的两个预注册的记忆实验。

## 结果

同一个 harness、同一个模型（deepseek-flash，每次运行最多 40 次模型调用），SWE-bench Verified 的题。数字引自[最终报告](agent/docs/MEMORY-FINAL-REPORT.zh-CN.md)第 1、6.1 节；效应单位是百分点，括号里是 95% 区间。

| 实验 | 注入的记忆 | 和目标题的相关性 | 规模 | 有记忆 − 无记忆 | p |
| --- | --- | --- | --- | --- | --- |
| A5，跨题记忆 | 同仓库、更早、已被验证解出的其他题的卡片（B2），对照不注入（B0） | 低（9/51 题指向 gold 文件） | 56 道题，每题每组 3 次 | −1.8，[−8.3, +4.8] | 0.72 |
| A6-R，同题记忆 | 对失败过的题做第二次尝试：带上第一次尝试的规则化记录和"上次没通过"（R1），对照不带（R0） | 100%，按构造保证 | 53 次失败的第一次尝试，22 道题，每组 159 次 | −6.6，[−17.7, +3.8] | 0.29 |

两个都是零结果：都没有检出正效应。

## 方法

- **答案隔离。** 早期的 dev 镜像里带着隐藏测试；改用干净源码重建镜像后，同样 14 道 dev 题的解出从 32/42 降到 18/42（[项目历程](harness/docs/PROJECT-HISTORY.zh-CN.md)，冲刺第 3、4 轮）。
- **包装实验。** 同样 9 份固定摘要，把包装写成"可能有误的历史证据，不是指令"后，全正确是 26/27，原来的包装是 7/27（[证据](harness/docs/upgrade/evidence/R2-real/wrapper-01/README.md)）。
- **预注册和冻结 tag。** 假设、唯一的主分析、种子和停止条件，在任何真实数据出现之前提交并打 tag（[A6-R 预注册](agent/docs/sprint/A6-R-PREREG.zh-CN.md)）。
- **注入一致性检查。** 每次运行结束后，把模型实际收到的第一条消息和预期全文逐字比对：A5 168/168，A6-R 318/318（[最终报告](agent/docs/MEMORY-FINAL-REPORT.zh-CN.md)第 3 节）。
- **同期交错。** 两组放进同一个打乱的队列（A6-R 的种子是 20261013），在同一时段跑（[A6-R 预注册](agent/docs/sprint/A6-R-PREREG.zh-CN.md)第 1 节）。

## 仓库地图

- `harness/`：评测 harness。包括 agent 循环、工具、干净的 Docker 镜像、把 test patch 和 gold patch 留在 host 侧的 grader、运行脚本、A6-R 的尝试记录和运行清单。
- `agent/`：RepoSkillAgent。包括记忆卡片和注入卡片的插件、分析脚本、A6-R 预注册和最终报告。

从哪里开始读：

- [两个记忆实验的最终报告](agent/docs/MEMORY-FINAL-REPORT.zh-CN.md)
- [harness README](harness/README.zh-CN.md)
- [项目历程](harness/docs/PROJECT-HISTORY.zh-CN.md)

## 复现

这两个目录原来是并列的两个仓库 `coding-harness` 和 `coding-agent`，开发和冻结都在这个布局下进行，代码按这个布局引用对方；部分配置和证据文件里还记着原机器上的绝对路径。这里没有改写这些路径，这样冻结 tag 指向的仍然是实际运行的代码。tag 保留的是原来的提交，所以可以按原布局检出冻结状态：

```
git worktree add ../coding-harness harness/a6-retry-freeze
git worktree add ../coding-agent agent/a6-retry-freeze-r2
```

冻结 tag：

- A5：`harness/a5-main-freeze`、`harness/a5-main-freeze-r1` 到 `-r4`、`agent/a5-main-freeze`
- A6-R：`harness/a6-retry-freeze`、`agent/a6-retry-freeze`、`agent/a6-retry-freeze-r1`、`agent/a6-retry-freeze-r2`

运行 agent 需要 Docker、SWE-bench 镜像和 DeepSeek API key。分析命令见 [A5 最终报告](agent/docs/A5-FINAL-REPORT.zh-CN.md)和[最终报告](agent/docs/MEMORY-FINAL-REPORT.zh-CN.md)的附录。

## 关联项目

agentic-rl 是另一个项目，还没有公开，研究的是靠训练（SFT、GRPO）而不是靠上下文来改变 agent 的行为。
