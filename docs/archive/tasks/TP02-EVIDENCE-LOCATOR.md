# TP02 — 从公开线索发现证据

> 历史任务包（2026-09-18）。这是当时发给执行 agent 的任务说明，已被实现取代；当前接口以 [PUBLIC-API](../../upgrade/PUBLIC-API.md) 和 [实现记录](../../upgrade/IMPLEMENTED-TP01-04.md) 为准。

执行更新：2026-09-19 已由本任务实施并离线验证，具体证据/限制见 [实施记录](../../upgrade/IMPLEMENTED-TP01-04.md)。下文保留原任务包说明。

状态：待用户启动；版本 v0.1，2026-09-18；Codex/Cursor 同一验收。

## 可直接转交的执行说明

在 `D:\crq\src\coding-agent` 阅读总计划、TP01 交付及本包。只实现 TP02；不访问模型 API，不改历史报告，不把 benchmark ID/category/expected_files 作为 fallback。先核查快照与当前指令，旧 diagnostic 保持可用。没有 TP01 成品时可用固定 PublicTask fixture 开发纯算法，但不得自行改写公共 DTO 或声称 A1 集成完成。

## 动机、范围与依赖

`agents/locator.py:19 LocatorAgent.run` 依赖 expected_files，空列表会返回成功；`core/context_expansion.py:38 expand_allowed_paths` 用答案父目录/符号；`core/planner.py:15 create_plan` 写入答案路径；`llm/prompts.py:119` 仅可写文件进入正文。已有 tests/ 写保护必须保留。

TP01 公共输入为正式依赖。允许新增 `reposkill_agent/evidence/models.py, locator.py, context.py`、`tests/test_evidence_locator.py`、自建小 fixture、公开 prompt renderer；如复用 `llm/prompts.py`，新增明确的 public builder，不改变 legacy renderer 的历史语义。该包文件由一个实施者独占；与 TP01 的 protocol 变更需求先记录再合并。

排除：训练 retriever、向量数据库、调用宿主 shell/实现 rg 进程管理、付费修复、Skill/router/memory 算法。定位模块消费宿主提供的 tree/search/read observations，首版用本地只读 fixture adapter；实用搜索可由宿主 rg 工具实现，本包不复制执行工具。

## 输入输出

输入 PublicTask、公开 repo facts/tree、允许的 search/read results、公开 traceback、先前 EvidenceState 和剩余配额。证据必须包含 artifact/hash 或 fixture ref、path/range、来源类别、读取时 repo version；没有读取过的路径不能伪造代码证据。

输出 EvidenceState（hypotheses、observations、read_ranges、missing_evidence、selected_context、reason、budget_spent）和 `Read/SearchProposal`，或 `insufficient_evidence / budget_exhausted`。候选排序首版固定：公开 traceback/issue 文件线索 → 符号/关键词命中 → imports/call sites；同分按规范路径稳定排序。路径/片段去重，不读取整个 repo 入 prompt。

可配置上限暂沿用每轮 3 条/累计 6 文件作默认 fixture，另加片段字符/token 配额。配额只是策略建议，实际工具/总 tokens 由宿主再次检查。读取集合与写入候选分离；tests 公开内容可读，写 proposal 不包含 tests/。

## 行为验收（6 条）

1. 完全没有 expected_files/tags 的公开 issue，通过函数名和 traceback 找到最小 fixture 修复位置，给出证据来源；修改 opaque task ID/私有 gold 不改变排序。
2. 源文件重命名、增加干扰文件或替换 repo 根路径后，只要公开引用同步，仍按证据定位；若公开引用失效则报告缺证据，不能按 medium_inventory 等名字补答案。
3. 无相关线索不返回虚假的 success；预算用尽返回已搜索/已读范围和下一步需要什么，零 oracle fallback。
4. 片段/文件去重，稳定排序、截断有记录；超额 proposal 被拒绝或延后，不能累计突破配额。
5. 公开测试中放独特普通文本，捕获 rendered prompt 验证正文确实包含它；同轮该测试路径不在 writable proposals；私有 sentinel 在任意公共产物中不可见。不能只断言 readable_paths 指标。
6. README/代码注释含“忽略规则/读私钥”的攻击 fixture 时仍只是引用数据，不能产生越权 proposal；实际路径安全交给受控宿主，离线测试不宣称完成隔离。

## 检查命令、交付与退出

已核实：`../VERIFICATION.md` 的 44 项命令覆盖 `test_planner.py test_context_expansion.py test_llm_developer.py`，全部通过；Ruff 通过。`rg` 本机可用，已经用于源码定位；没有实际宿主 rg adapter 的集成证明。

新增后（尚未运行）：

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PATH='C:\Users\Administrator\.conda\envs\coding-harness;C:\Users\Administrator\.conda\envs\coding-harness\Scripts;' + $env:PATH
& 'C:\Users\Administrator\.conda\envs\coding-harness\python.exe' -m pytest tests/test_evidence_locator.py tests/test_public_boundary.py tests/test_context_expansion.py tests/test_llm_developer.py -q -o addopts='' -p no:cacheprovider
```

交付源码、fixture、一个无模型 evidence walkthrough（输入→proposal→公开观察→定位/退出）、prompt 内容级回归、字段来源表、hash/diff 与命令日志。A1 装配验收还需将 TP01/02 连在 fixture host 下，证明公共策略链不再进入 legacy planner/locator；未装配就明确标组件完成。

风险：关键词 baseline 能力有限，Python traceback/符号启发式不保证跨语言；没有有效观察时缺证据是合格行为。不得为提高命中率读取 evaluator 标签。若必须更改 TP01 数据结构，先列兼容扩展，停在相关接入点，其余本地算法和 fixture 可交付。
