你接手 `D:/crq/src/coding-harness` 的 A5 memory pool 建设。先读 `AGENTS.md` 和 `docs/upgrade/A5-PRE-MEMORY-CURSOR-CONTRACT.zh-CN.md`，再定点阅读合同列出的配置、coding-agent handoff、脚本、grader 源码和 evidence。只写新 Markdown/evidence；不要覆盖旧目录，不向其他任务发消息，不唤醒旧任务。

本任务目标是建立一个可用、可追溯的小型 memory pool。20 个 source 是候选边界，不是建池前必须全部通过的研究实验；先从 4–6 个多样 source 做 smoke/build，验证端到端 provenance、public/private 隔离、source/trajectory/grader receipt、失败留账和预算，再扩展到约 12–15 条有效 `MemoryRecord`。实际有效数量可以少于 15，必须诚实报告。

不可妥协：不得泄漏 gold patch、test patch、hidden tests、私有 grader 或 target 答案；不得伪造或倒填轨迹；每条记录必须有真实公开观察/动作/验证、source/tree/image hash、trajectory/run/attempt id、可回读 validation receipt 和 provenance review；失败、unknown、invalid_env、retry 和费用必须留账；付费 build 受硬上限和独立 ledger 约束；只对实际要付费建池的 source 强制最小运行 gate。

按 S0→S1→S2→S3 执行：

1. S0 建立 20 行 candidate index，核对 source/repo/base/tree/image/receipt/hash 和旧成功/失败/retry 证据。`62-history-baseline-retry` 的四行可作为 baseline 候选证据；66/67 collect-only 和常量阴性检查不能当 grader-ready。旧证据全部保留。
2. S1 选择 4–6 个多样 source，优先复用可靠 checkout/image/collection，逐个完成最小 gate 和 smoke/build。每个结果保存 public input、真实公开 trajectory、candidate/delta、独立 validation receipt、cleanup、成本、失败原因和 provenance。至少覆盖两个 repo family；失败可以留在样本中，但不能伪造成功。
3. S2 只在 S1 链路稳定后扩展到约 12–15 条 validated/candidate。每个将实际付费的 source 在 build 前单独通过最小 gate和预算 reservation；未采用的剩余 source 不要求先完成 full-repo grader calibration。candidate 与 validated 分态，失败不因数量不足升格。
4. S3 只做公开交接和未来升级清单。把 24 题全量预检、20×4×3 pilot、统计显著性、所有 source full-repo grader calibration 标为可选研究升级，不作为当前建池前置条件。fixture-only receipt 必须如实标注，未发生真实调用则保持 `model_calls=0`、`paid=false`。

命令只写在合同模板中；若后续执行，先确认 CLI/参数真实存在，使用全新输出目录、阶段日志和超时。不要删除目录、手改 receipt/readiness、把 stdout/exit 0 当验证、把 attempt 数当 record 数，也不要因一个来源失败阻塞整个小池。若失败没有新权限/路径/解释器/算法证据，不得原样重试；一次实质修复后最多一次针对性复验。

最终报告合同和新 evidence 路径、4–6 个 smoke/build 的真实状态、实际 validated/candidate 数量、失败/成本 ledger、最关键真实缺口和需要用户另行决定的 paid scope 或研究升级。当前交接本身不运行、不付费、不启动 memory build/pilot。
