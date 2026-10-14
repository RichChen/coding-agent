# coding-agent 第四轮计划：只用答案隔离后的轨迹重建 v4

日期：2026-09-25。

配套计划：`D:\\crq\\src\\coding-harness\\docs\\sprint\\HARNESS-SPRINT-4.zh-CN.md`。
审计矫正：`D:\\crq\\src\\coding-harness\\docs\\sprint\\AUDIT-3-CORRECTION.zh-CN.md`。

## 0. 硬门槛

- 当前 `memory-cards-v4.manifest.json` 的 `interim` 状态保持不变，不得改成 `final`。
- 当前 `memory-source-runs.json` 的 `b0-v1` 数据被测试可见条件污染，只能保留作历史证据。
- 只有收到 `profile_tag: b0-v2`、每条运行都是 `answer_isolation_pass: true` 的新 handoff 后，才重建 final v4。
- 本轮不调用模型、不新增 sphinx 源题、不跑 B0/B2 实验。

## 1. 等待并核对 handoff

收到新 handoff 后，先检查：

- schema、profile tag、harness commit；
- 每道 dev 题各 3 条运行；如果 harness 在 PROGRESS 里列出了被排除的题，就按排除后的题数核对；source id 不能和 pilot 有交集；
- clean image digest、source-only hash 和允许的 native artifact 清单；
- 每条运行的隔离状态为通过；
- handoff 的 SHA256 与 harness 的 `CHECKPOINT-4.md` 或 `PROGRESS.md` 里记录的一致。

开工前先提交本计划书，再打 tag `mem4-start`。继续往 `PROGRESS.md` 追加记录。本轮做完 B2 过滤之后，如果 handoff 还没有出现，就写 `CHECKPOINT-4.md` 停下，不要轮询等待。

任一条件失败就停在审计节点，不构建 final。

## 2. 重建 v4

用新运行的事件流和 candidate delta 重新生成卡片：

- 优先选择同一 source 中最小 repeat 的 `solved` 运行；没有 solved 才选择最小 repeat 的失败运行作审计记录；
- `validated_fix` 只允许来自 clean profile 且 grader pass 的运行；
- legacy 或旧 b0-v1 轨迹不能被标成 `validated_fix`；
- 卡片正文不包含 test patch、gold patch、隐藏 nodeid 或目标题答案；
- manifest 的 `build_inputs.memory_source_runs_sha256` 必须等于新 handoff SHA256，`status` 才能设为 `final`。

## 3. B2 注入规则

首轮正式实验只保留 B0 与 B2。B2 只向模型注入 `verification_status == validated_fix` 的卡片；failed/unverified 卡片不成为正式实验条件，也不作为负面导航变体。

留一法继续由 harness 在插件前过滤当前 source id。保留现有卡片格式、字节上限和 B3 代码路径，暂不为 B1/B3 增加实验矩阵。

## 4. 代码和测试

- 为 B2 的 validated-only 过滤补单元测试；
- 保持 extractor 对 memory_pool 和 sprint 两种目录格式的兼容；
- `PermissionError` 只在有独立可复现的业务错误时顺手处理，不把沙箱 ACL 作为 R4 目标；
- 运行现有卡片、插件、source verification 测试；不调模型。

## 5. 停止条件

如果新 handoff 缺失、隔离失败、source 与 pilot 重叠、或卡片中出现私有测试内容，立即停止并报告，不用旧数据补洞、不手改单张卡片。
