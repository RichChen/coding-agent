# TP04 — 依赖级有效性、冲突与注入 gate

> 历史任务包（2026-09-18）。这是当时发给执行 agent 的任务说明，已被实现取代；当前接口以 [PUBLIC-API](../../upgrade/PUBLIC-API.md) 和 [实现记录](../../upgrade/IMPLEMENTED-TP01-04.md) 为准。

执行更新：2026-09-19 已由本任务实施并离线验证，具体证据/限制见 [实施记录](../../upgrade/IMPLEMENTED-TP01-04.md)。下文保留原任务包说明。

状态：待用户启动；v0.1，2026-09-18；前置 TP03，Codex/Cursor 共用验收。

## 可直接转交的执行说明

在 `D:\crq\src\coding-agent` 阅读总计划第 5/7 节、TP03 schema 和共享契约。实现纯 validity/check/gate 与离线漂移演示，不加模型/工具执行内核，不跑付费实验，不改 legacy 指标/结果。先核对基线和用户改动，只编辑本包文件。

## 动机与范围

现有 `memory/consolidator.py:22 repo_fingerprint` 只识别路径；`memory/retriever.py select/_rank_candidates` 依靠 tags、seed-pair/confidence，没有版本检查；`graph_runner.py:285–293` 将注入后成败当 useful/stale。新机制需独立判定依赖有效性，不能直接复用这些代理字段。

允许新增 `memory/validity.py, dependency_index.py, gate.py`、`tests/test_memory_validity.py, test_memory_gate.py`、`tests/fixtures/upgrade/drift/`、离线 `scripts/demo_memory_validity.py` 与说明。依赖 TP03 MemoryRecord/store 和固定 RepoFacts fixture；可在 TP02 未合入时测试，不依赖 harness。不要改 TP03 schema 含义；必须扩展时记录版本/兼容，先与同仓包协调。

## 输入输出

输入 record revision、当前 repo identity/revision、公开 API 签名/依赖版本/已读文件 hashes、时钟、source policy、剩余策略配额。检查器无磁盘/网络副作用；需要重验时只输出受控 action proposal。

输出 `ValidityResult{status:valid|invalid|unknown,reasons,checked_dependencies,evidence_refs,checker_version,usage}`、候选选择/拒绝理由、重验提案、可选状态 transition 请求；由 store 提交生命周期 revision，由宿主提交 run events 和实际注入 receipt。

组合规则：invalid 优先于 unknown 优先于 valid；validated 生命周期不跳过当前检查；相似度不能翻转 invalid；粗 hash 变化且语义未知→unknown，已知 API 不兼容→invalid；同 commit 仍查环境。TTL 过期→unknown/重验，未过期不是正确性证明。无映射只保守 unknown，不做精确依赖假象。

## 行为验收（6 条）

1. 改依赖 API 签名/版本 range 后旧 record invalid 且不注入，理由能定位依赖；未知版本/缺签名 unknown，默认不注入。所有必需证据匹配才 valid。
2. commit 变化但完整映射证明只改无关文件时原 valid 记录保留；同 commit 但 package 不兼容仍拒绝；粗文件变更无法判断时 unknown。
3. 与静态和整库清空 baseline 对相同初始 store/changes 跑确定性矩阵，记录 stale 误注入和 valid 保留分母，分母零为 N/A；该 demo 标机制验证，不能称真实模型能力分数。
4. 同域相斥经验有冲突组和解释，不同时作为强建议；quarantined/retired 绝不自动再注入；公开重验通过只产生新 revision，旧历史可查。
5. receipt fixture 展示 selected≠actually_injected：宿主裁剪/拒绝不算成功注入；无法观察采用时 unknown；不得从最终通过率填有效性 ground truth。
6. 大文本/重复片段/配额耗尽可输出零条；恶意记忆不能产生越权动作。source split 不合格即拒绝，高 lexical 分数不绕 gate；重验提案成本入账且只使用公开证据。

## 命令、产物与退出条件

现有已核实：`../VERIFICATION.md` 中 `test_memory.py test_memory_matching.py test_injection_policy.py` 已随 44 项通过，Ruff 通过。尚无现成 validity CLI，不得写成“已可运行 demo”。

新增后执行（未运行）：

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PATH='C:\Users\Administrator\.conda\envs\coding-harness;C:\Users\Administrator\.conda\envs\coding-harness\Scripts;' + $env:PATH
& 'C:\Users\Administrator\.conda\envs\coding-harness\python.exe' -m pytest tests/test_memory_validity.py tests/test_memory_gate.py tests/test_memory_records.py tests/test_injection_policy.py -q -o addopts='' -p no:cacheprovider
```

新 demo 的 flags 必须在实现后用 `--help` 验证并写入交付日志，本包不虚构现有参数。交付：规则/理由码表、依赖矩阵、状态图、可离线运行 demo、固定输入/预期/实际 JSON 结果、负例/unknown 报告、成本记录、hash/diff 和行为测试日志。

依赖映射不完整是预期限制；首版 Python API 签名/锁文件规则不代表通用语义失效检测。若宿主尚无 receipt API，用明确标记的 fixture 验证，不提前报告真实注入完成。结束时列实现/fixture/未支持矩阵；真实联调和正收益不属于本包完成条件。
