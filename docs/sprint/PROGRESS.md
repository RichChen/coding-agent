# 记忆重建进度

## 第 0 步：版本控制（2026-09-24）

- `.git` 是 2026-07-02 留下的空目录，`git status` 报 not a git repository，没有可恢复历史。已改名为 `.git.broken-20260924`，并重新 `git init`。
- `.gitignore`：去掉全局 `*.jsonl`，改为忽略 `traces/`、`reports/`、`.tmp/`、`.pytest-run-final/` 下的 jsonl；`benchmarks/`、`configs/`、`docs/` 里小于 1MB 的数据文件可以跟踪。根目录 `/*.pdf` 直接忽略。补上 `.tmp/`、`.pytest-run-final/`。另外忽略 `reports/**/workspaces/` 和 `reports/**/graph_workspaces/`，与已有的 `traces/workspaces/` 一致，避免把实验沙箱副本提交进去。文件仍留在磁盘上。
- 测试：`python -m pytest -q`，269 passed，1 skipped，0 failed（169s）。
- 下一步：第 1 步，写 `docs/sprint/MEMORY-INVENTORY.md`。

## 第 1 步：如实盘点（2026-09-24）

- 新增 `docs/sprint/MEMORY-INVENTORY.md`。运行时入口是 `public_runtime_view.py`（11 条快照，不走 `MemoryRecord`）和 `harness_h4.py`（走 `gate`/`validity`，但不读这 11 条）。`records.py`、`builder.py`、`gate.py`、`validity.py`、`record_store.py`、`dependency_index.py` 停在离线 demo 和单测。
- 11 条源记忆的仓库、短版本、源目录和轨迹字段已列入盘点。轨迹没有 `run_command` 参数，`failure_notes` 全空。
- 这一步只加文档，没有相关测试可跑。
- 下一步：第 2 步，读 harness 的 `memory-source-verification.json`；没有就先标 `unverified`。

## 第 2 步：接入源题验证结果（2026-09-24）

- `D:\crq\src\coding-harness\docs\sprint\memory-source-verification.json` 还不存在。11 条先全部按 `unverified` 处理，文件出现后同一函数会补上映射。
- 新增 `reposkill_agent/memory/source_verification.py`：`pass`→`validated_fix`，`partial`→`partial_attempt`，`fail`→`failed_attempt`，其余（含 `grader_unavailable`、缺文件、未知 source）→`unverified`。
- 测试：`python -m pytest -q tests/test_source_verification.py`，3 passed。
- 下一步：第 3 步，用规则从 11 条轨迹和 `candidate-delta.json` 提炼记忆卡，不调模型。

## 第 3 步：记忆提炼（2026-09-24）

- 在 `records.py` 增加 `MemoryCard` / `CardDependency`，沿用 `StrictModel` 和 `contains_secret`。没有另建一套记录类型，也没有把它伪装成已验证的 `MemoryRecord`。
- `memory/cards.py` 用规则提取：改过的路径排在读过的前面，测试命令和坑从 observation 里抓，修复思路只写改了哪些文件。不贴 diff，不调模型（费用 0）。
- 新快照 `benchmarks/a5/memory-cards-v2.jsonl`，11 张卡，125519 字节。验证文件仍缺失，11 张都是 `unverified`。渲染上限 1500 字节。
- 测试：`python -m pytest -q tests/test_memory_cards.py tests/test_source_verification.py`，6 passed。目标题 ID 与 11 个源题不相交；目标题 gold/test patch 里长度 ≥ 80 的新增行没有出现在卡片渲染文本里。
- 下一步：第 4 步，BM25 检索和 `MemoryCardPlugin`（B0–B3），旧入口保持不动。

## 第 4 步：检索和变体（2026-09-24）

- 新入口：`load_memory_cards(path) -> tuple[MemoryCard, ...]`（在 `memory/cards.py`）。`MemoryCardPlugin(variant, cards, repo, issue, target_root, max_bytes=4096, min_score=1.0)`，方法 `async decide(policy_input) -> dict`，返回 `schema_version`、`candidates`、`state`、`events`、`action_proposals`。旧的 `load_public_episodes` 和 `A5PublicMemoryPlugin` 没改。
- 检索是自写 BM25，带停用词，再加上题目里的路径和符号与 `relevant_files` 的重合加分。低于 `min_score` 时一条都不选，事件状态为 `no_relevant_memory`。没有 `len(episodes) != 11` 这类断言。
- B0 不注入。B1/B2/B3 用同一批卡、同一个 `rank_cards`、同一个 `max_bytes`。B1 注入截断轨迹，B2/B3 注入记忆卡渲染。B3 用 `validity.check_card_dependencies` 和 `gate.validity_reasons`；`invalid` 不注入。
- 测试：`python -m pytest -q tests/test_memory_card_plugin.py tests/test_memory_validity.py tests/test_memory_gate.py`，插件 5 passed，原有 validity/gate 仍通过。
- 下一步：写第 5 步扩充方案和 `CHECKPOINT-1.md`，然后停下等审计。

## 第 5 步方案与审计节点（2026-09-24）

- 只写了方案，没有造新轨迹，没有调模型。费用记录：0。
- `docs/sprint/CHECKPOINT-1.md` 含提交列表、两张渲染样例、20 道目标题的 B1/B2/B3 离线检索、新入口签名、扩充方案。
- 离线检索：sphinx 四题和 `sympy-20154` 一条都选不到。B3 在没有目标仓库检出时，排上的卡都因路径不存在被拒绝。
- 扩充若要做，13 条新源题、约 3.2–6.5 CNY，超过 3 元观察线，留给审计之后。
- 下一步：停。等用户把 CHECKPOINT-1 交给审计者。

## 补第 2 步：验证文件已到（2026-09-25）

- `coding-harness/docs/sprint/memory-source-verification.json` 已存在。重新生成 `memory-cards-v2.jsonl`，只改了状态字段。
- `pytest-dev__pytest-5103` 为 `partial`，卡片改为 `partial_attempt`（F2P 0/1，P2P 20/64，数字不写入卡片）。
- 其余 10 条是 `grader_unavailable`，仍为 `unverified`：django 3 条是文件数上限，sympy/sklearn 6 条是传输配额，`pytest-5221` 的 grader 没有给出 pass/partial/fail。
- 测试：`python -m pytest -q tests/test_memory_cards.py tests/test_source_verification.py`，6 passed。

## 第二轮 第 1 步：从原始事件流提取（2026-09-25）

- 开工 tag：`mem2-start`（`c4ecbf0`）。
- 11 条源的 `source_dir/run/events.jsonl` 都在。后面的 `state.saved` 整段 payload 是 `artifact_ref`，正文在 `run/session/artifacts`。读不到的字段会跳过并记下原因；这 11 条没有跳过。
- 新模块 `memory/event_extract.py`：读文件的行号范围、`search_code` 的 pattern、测试相关命令（`pytest` / `runtests.py` / `python -c` / `python -m`）、模型诊断和最终回答各 1–3 句、用 `ast` 把 `search_replace` 对上改动后的 `def`/`class`。
- 11 条里 `django-10924` 和 `sklearn-11040` 没有符合条件的测试命令。`django-10914`、`sklearn-10297`、`pytest-5221` 没对上改动符号。
- 测试：`python -m pytest -q tests/test_event_extract.py`。目标题 ID 和 gold/test patch 里长度 ≥ 80 的新增行没有出现在提取结果里。
- 下一步：第 2 步，滤掉旧镜像里的缺依赖、git 不存在、全盘搜索和 stub。

## 第二轮 第 2 步：过滤旧环境噪声（2026-09-25）

- `memory/legacy_env.py` 的 `is_legacy_env_artifact` / `split_legacy`。命中的条目标成旧环境噪声，不渲染给模型。
- 滤掉：`pip install` / `pip download`；`No module named` 后面是 six、pluggy、attr、py、more_itertools、numpy、mpmath、packaging、pytz、sqlparse；`git: not found`；`find /`；`/tmp/stubs`；域名解析失败、拉不到包、连接被拒绝。
- 保留：`testing/` 下的测试、`tests/runtests.py`、必须一起改的模块。
- 测试：`python -m pytest -q tests/test_legacy_env.py`，2 passed。
- 下一步：第 3 步，用规则重填记忆卡，写成 `memory-cards-v3.jsonl`，先看结果再决定是否用 LLM。

## 第二轮 第 3 步：重新生成记忆卡（2026-09-25）

- `memory/cards_v3.py` 用事件提取结果重填 `MemoryCard`。改过的路径在前，并带上读过的行号。测试命令来自 `run_command`；源轨迹里没跑过就写 `none run in source attempt`。`approach` 是诊断原话加改动的函数或类名。`pitfalls` 只留仓库相关的句子，旧环境噪声不渲染。
- 命令过滤收紧：路径里的 `_pytest` 不再被当成 pytest 命令。一条命令里夹了 `pip` 或 `find /` 的片段会丢掉，旁边的 `python -c` 仍保留。
- 新快照 `benchmarks/a5/memory-cards-v3.jsonl`，123959 字节，不覆盖 v2。11 张里 8 张有测试命令，3 张是 `none run`（`django-10924`、`pytest-5103`、`sklearn-11040`）。
- 看过规则版之后不做 LLM 提炼。诊断句已经点到 `FILE_UPLOAD_PERMISSIONS`、`visit_Call`、`n_neighbors`、`fit_predict` 这类具体位置，费用 0。
- 测试：`python -m pytest -q tests/test_memory_cards_v3.py tests/test_memory_cards.py tests/test_legacy_env.py`，8 passed。渲染不超过 1500 字节，目标题 ID 和 gold 片段没有进卡片。
- 下一步：第 4 步，把 20 道目标题的 `source.tar.gz` 解压到仓库外，重跑 B1/B2/B3。

## 第二轮 第 4 步：对着真实目标源码做 B3（2026-09-25）

- 20 道目标题只解压了 `source.tar.gz` 到 `D:\crq\tmp\a5-targets\<id>\`，没有读 gold 或 test patch，没有进 git。
- 改规则前：sklearn 四题的 B3 一张卡都注不进去。`sklearn-11281` 和 `sklearn-11040` 是因为旧路径不在（`mixture/base.py`、`neighbors/base.py`）。其余拒绝多是符号不在原文件里。
- 加了规则：路径不存在，但关键函数或类名能在目标树里搜到，记为 `unknown` / `relocated`，不记 `invalid`。`unknown` 仍按现在的插件规则注入。
- 改规则后：四道 sklearn 题都注入了 `sklearn-11281`（`fit_predict` 被挪走但仍能搜到）。`sklearn-11040` 的符号在目标树里搜不到，仍然 `invalid`。
- sphinx 四题和 `sympy-20154` 改规则前后都是一条都选不到。
- 另外收紧了测试命令切分：引号里的分号不再被切开，`pip show` 视为旧环境噪声。v3 快照已按这个重写。
- 测试：`python -m pytest -q tests/test_relocated_dependency.py tests/test_memory_card_plugin.py tests/test_memory_cards_v3.py`，通过。
- 下一步：第 5 步，看验证文件有没有更新。

## 第二轮 第 5 步：源题验证（2026-09-25）

- 再读了 `coding-harness/docs/sprint/memory-source-verification.json`。仍是 10 条 `grader_unavailable`、1 条 `partial`（`pytest-5103`），没有 `calibrated` 字段，也没有新的 pass/fail。
- v3 卡片状态不用重写：`pytest-5103` 已是 `partial_attempt`，其余 `unverified`。等 harness 第二轮第 4 步把新 grader 结果写回同一个文件。
- 已写 `docs/sprint/CHECKPOINT-2.md`。停下等审计。
