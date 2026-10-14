# 首批离线实施验收合同 v1

冻结日期：2026-09-19；授权：用户“你直接实施”。范围 TP01–TP04 及其离线装配；不含付费实验、对方仓库变更或真实沙箱保证。旧目标/任务包是设计基线，当前授权和本记录更新执行状态。

问题：不使用 oracle 的公开策略能否发现线索；来源不合规或已失效经验能否被可靠拒绝，并保留不受影响经验？不假设提高模型修复成功率。

固定 baseline：现有 legacy 接口/测试保留；新数据使用自建小型公开 fixture，人工内容明确标注，不称真实未知 GitHub issue。有效性四组为无记忆/静态/变化清空/依赖检查；同一候选池与变更集。顺序确定，无随机 seed 或模型调用。未来付费 E-A1/E-A2 仍未冻结。

必须通过：TP01–04 各 6 条行为验收；oracle sentinel 非干扰；公开测试进入正文但不进入写候选；source allowlist/时间/split/hash 拒绝；SQLite 版本提交原子性；invalid/unknown 不自动注入；相关变化拒绝、无关变化保留；隔离/冲突记录拒绝；宿主收据与 selected 分离。fixture ground truth 只用于评估函数，不传 validity checker。

失败信号：答案字段进入公开产物；缺来源晋升 validated；存储中断留下半条 revision；相似度绕过失效；把未知费用记零；把选中当采用；新增代码破坏旧接口。失败必须修复或明确报告，不能修改本合同迎合输出。

测量：漂移矩阵按 decision/record revision 计数，stale_injected/stale_candidates、valid_retained/valid_candidates，零分母为 null。所有实际注入/成功均区分 fixture 与真实宿主。记录测试命令、结果、源码快照与 diff。CPU wall time 可实测；离线无外部模型调用，模型费用为 0。秘密与历史报告不进入快照。

验收产物：源码/行为测试、demo CLI、schema 与支持说明、基线 zip/hash、固定 fixture 结果及变更清单。研究方法依据 research-workflow；本批是工程/机制验收，不产生模型能力收益结论。
