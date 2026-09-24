# TP03 — 可追溯记录、状态与版本 store

执行更新：2026-09-19 已由本任务实施并离线验证，具体证据/限制见 [实施记录](../IMPLEMENTED-TP01-04.md)。下文保留原任务包说明。

状态：待用户启动；v0.1，2026-09-18；本包可独立离线开发，Codex/Cursor 标准相同。

## 可直接转交的执行说明

工作目录 `D:\crq\src\coding-agent`。先读总计划第 2/5/7 节及共享契约，核对当前文件与快照。实现 TP03 的 record/store/manifest gate，不实现 validity 规则或 LLM builder，不修改原记忆 JSONL/SQLite，不跑 paid eval、不提交推送。跨包需要类型时固定输入 JSON fixture；不要向对方仓库写代码。

## 当前证据、范围与前置

`memory/models.py MemoryHint` 缺 memory_id/revision/代码版本；`procedural.py ProceduralMemory` 只有任务来源等；`consolidator.py repo_fingerprint` hash 路径；`build_procedural` 把 expected_files 和 tags 变成经验；`episodic.py EpisodicStore.append` 先 JSONL 后 SQLite（不是一个事务）。旧数据不足以默认成为新 validated 记忆。

前置 A0 基线快照；独立开发不需 TP01/02，接入公开轨迹必须等其 manifest。允许新增 `memory/records.py, record_store.py, source_manifest.py, migration.py` 与 `tests/test_memory_records.py, test_memory_record_store.py, test_memory_sources.py`，必要时只增 package exports。旧 `models/procedural/episodic/consolidator/retriever` 行为保持，新路径不要复用其答案派生逻辑。排除修改 runtime trace/database 和真实历史文件。

## 输入输出与语义

输入：白名单轨迹 artifact refs（task/run/repo/version/protocol/split/time/hash）、公共验证证据、builder 方法/usage、人工经验注释、可选 legacy 样本副本。输出：总计划第 5 节的 MemoryRecord v1、追加 revision/transition、source rejection audit、只读 snapshot manifest 与 compact hint projection。

store 采用独立 SQLite 单事务提交 record+revision+transition，unique `(memory_id,revision)`、content hash 与前驱引用；artifact 原文不复制进 db。保存格式未知 major 拒绝，旧版本显式 reader/migration。禁止把未知 schema 数据静默解析成“可信提示”。runtime RunEvent 序号不在这里分配。

来源准入为默认 deny：heldout 目标/未来轨迹/diagnostic 来源不能进入 realistic build；真实公开历史和 human-authored 分开记录。跨 repo 内容去重只报告重复/近重复风险，不能证明无训练污染。规则 extractor 本包仅处理结构化输入，不自动读取任意磁盘路径。

迁移输出到新路径，不改旧文件：能校验来源但未公开验证→candidate，缺证据→candidate + unknown，损坏/秘密内容→quarantine audit；无声修补来源或固定 confidence 晋升 forbidden。规则/人工 builder 模型字段为 null/none，调用为零与 usage unknown 有明确区别。

## 行为验收（6 条）

1. record roundtrip 后稳定 ID/revision/hash/来源链可查；任一 compact hint 能回查 task/run/artifact/版本/前提；缺来源不自动 validated。
2. SQLite 事务中断不出现只有 revision 没有对应 transition 的半条记录；重复写相同 revision 可幂等或明确拒绝，不悄悄覆盖。可用临时 db 故障注入验证，非 runtime 恢复实现。
3. 用含 oracle 字段的 legacy 样本副本迁移，新 realistic store 不包含答案信息；原文件 hash 不变；损坏行被单独报告，不吞掉整批或默认成功。
4. source manifest 混入 target/heldout/future task 或 diagnostic source 时拒绝；对同任务改名但 source artifact/hash 重复仍能检测明显重复。未知时间按协议缺失处理，不伪造 chronology。
5. candidate 只能在有允许公开证据、验证版本和明确 transition 时晋升；quarantined 不能自动晋升，retired 不进入候选；用假密钥 fixture 验证 secret exclusion，不读取真实 `.env`。
6. 空新 store 检索/投影返回零条，不能生成 confidence=.92 的默认 repo profile；使用历史和构建成本可查询，但不把注入/成功写成 observed_following=true。

## 命令、产物与风险

已核实并通过：`../VERIFICATION.md` 44 项命令中的 `test_memory.py test_memory_matching.py` 和 Ruff；SQLite 为 Python 标准库，无需依赖安装。

新增后命令（尚未执行/文件尚不存在）：

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PATH='C:\Users\Administrator\.conda\envs\coding-harness;C:\Users\Administrator\.conda\envs\coding-harness\Scripts;' + $env:PATH
& 'C:\Users\Administrator\.conda\envs\coding-harness\python.exe' -m pytest tests/test_memory_records.py tests/test_memory_record_store.py tests/test_memory_sources.py tests/test_memory.py tests/test_memory_matching.py -q -o addopts='' -p no:cacheprovider
```

交付：schema/状态迁移文档、独立 store、只读导入/显式迁移入口、fixture db/source manifests、失败清单与原文件未变证明、测试日志、hash/diff。首版不需要向量库或大历史导入。

风险：旧 source_task_id 不足以还原 run/代码版本；缺历史只能保留 unknown，不能为“迁移覆盖率”造 provenance。ArtifactRef ACL 需与 harness 对齐，先使用固定本地 resolver fixture。遇到不可确认来源/secret 时隔离该条并交审计结果，不整体阻塞其它合法 fixture。
