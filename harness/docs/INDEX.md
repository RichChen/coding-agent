# 文档索引

这个仓库的文档分四类。想读代码之前，先看这里，不用按目录顺序翻。

## 1. 入口

| 文档 | 内容 |
| --- | --- |
| [../README.md](../README.md) / [../README.zh-CN.md](../README.zh-CN.md) | 安装、跑一次、跑评测、项目结构 |
| [PROJECT-OVERVIEW.zh-CN.md](PROJECT-OVERVIEW.zh-CN.md) | 项目要解决什么问题，和同类工作的差别 |
| [PROJECT-HISTORY.zh-CN.md](PROJECT-HISTORY.zh-CN.md) | 按轮次记录做了什么、哪里做错了、怎么发现的 |
| [LEARNING.zh-CN.md](LEARNING.zh-CN.md) | 按调用顺序读代码的路线和自测题 |
| [CONTAMINATION-NOTES.zh-CN.md](CONTAMINATION-NOTES.zh-CN.md) | 评测污染和答案隔离的处理 |

## 2. 实现说明（当前有效）

| 文档 | 内容 |
| --- | --- |
| [upgrade/H3-IMPLEMENTATION.zh-CN.md](upgrade/H3-IMPLEMENTATION.zh-CN.md) | Docker 执行、干净镜像、宿主机判分 |
| [upgrade/H4-IMPLEMENTATION.zh-CN.md](upgrade/H4-IMPLEMENTATION.zh-CN.md) | 上下文窗口、模型视图、插件接口 |
| [upgrade/H5-DEEPSEEK.zh-CN.md](upgrade/H5-DEEPSEEK.zh-CN.md) | 真实 DeepSeek 接入和预算 |
| [upgrade/H5-INTEROP.zh-CN.md](upgrade/H5-INTEROP.zh-CN.md) | 跨仓库插件的开/关对照 |
| [upgrade/SESSION-USAGE.zh-CN.md](upgrade/SESSION-USAGE.zh-CN.md) | 会话日志：意图先落盘、恢复时复用已提交结果、结果未知就停下 |
| [upgrade/R1-CLOSEOUT.zh-CN.md](upgrade/R1-CLOSEOUT.zh-CN.md) | R1 收口，含四个崩溃窗口的恢复验证 |
| [upgrade/R2-LITE-TRUE-SUMMARY.zh-CN.md](upgrade/R2-LITE-TRUE-SUMMARY.zh-CN.md) | 真摘要与共享预算 |
| [upgrade/R2-EXPERIMENT-CONTRACT.zh-CN.md](upgrade/R2-EXPERIMENT-CONTRACT.zh-CN.md) / [R2-WRAPPER-CONTRACT.zh-CN.md](upgrade/R2-WRAPPER-CONTRACT.zh-CN.md) | R2 实验和包装对照的设置 |
| [upgrade/A5-REAL240-HARNESS-CONTRACT.zh-CN.md](upgrade/A5-REAL240-HARNESS-CONTRACT.zh-CN.md) / [A5-HARNESS-GATE.zh-CN.md](upgrade/A5-HARNESS-GATE.zh-CN.md) | A5 的运行合同和预检门槛 |

## 3. A5 / A6-R 实验证据（`docs/sprint/`）

按时间顺序读：

1. [A5-MAIN-DESIGN.zh-CN.md](sprint/A5-MAIN-DESIGN.zh-CN.md)：题池、功效、B0/B2 的定义。
2. [A5-MAIN-FREEZE.md](sprint/A5-MAIN-FREEZE.md)：冻结的输入和 hash。
3. [CHECKPOINT-1.md](sprint/CHECKPOINT-1.md) 到 [CHECKPOINT-7.md](sprint/CHECKPOINT-7.md)：逐轮记录。第 6 份最长，包含 B0/B2 的统计和排除规则。
4. [A5-MAIN-INVENTORY.md](sprint/A5-MAIN-INVENTORY.md)、[A5-CASE-DATA.md](sprint/A5-CASE-DATA.md)：运行清单和案例数据。
5. [A6-R-PLAN.zh-CN.md](sprint/A6-R-PLAN.zh-CN.md) → [A6-R-FREEZE.md](sprint/A6-R-FREEZE.md) → [CHECKPOINT-A6-1.md](sprint/CHECKPOINT-A6-1.md) 到 [CHECKPOINT-A6-3.md](sprint/CHECKPOINT-A6-3.md)：第二次尝试实验。
6. [AUDIT-A6-*.zh-CN.md](sprint/AUDIT-A6-1.zh-CN.md)：审计方对每轮的核查记录。

历史的阶段计划和启动指令（`HARNESS-SPRINT-*.zh-CN.md`、`HARNESS-CAPABILITY-SPRINT.zh-CN.md`、`R4-START-PROMPTS.zh-CN.md`、`A6-R-START-PROMPTS.zh-CN.md`）保留在这里，因为 `CHECKPOINT-A6-2/3` 把其中两份记为原样入库的预注册材料。它们是当时的执行指令，不是使用说明。

[PROGRESS.md](sprint/PROGRESS.md) 是按时间追加的执行流水（约 47 KB），用来追查某一步的细节，不是入口文档。

## 4. 运行证据（`upgrade/evidence/`）

每个子目录是一次真实运行的记录：命令、日志、收据、失败原因。

- [H3](upgrade/evidence/H3/README.md)、[H4](upgrade/evidence/H4/README.md)、[H5](upgrade/evidence/H5/README.md)、[H5-interop](upgrade/evidence/H5-interop/README.md)：容器与真实模型运行。
- [R2-lite](upgrade/evidence/R2-lite/README.md)、[R2-real](upgrade/evidence/R2-real/README.md)、[R2-real/wrapper-01](upgrade/evidence/R2-real/wrapper-01/README.md)：摘要与包装对照。
- [A5-harness-preflight-*](upgrade/evidence/A5-harness-preflight-09/README.md)：A5 预检。
- [full-repo-grader](upgrade/evidence/full-repo-grader/README.md)：整仓 grader 校准。

`evidence/` 里有些 `session/` 子目录带 ACL 限制，读不了是正常的，不影响其他文件。
