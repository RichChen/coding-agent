# coding-agent 第二轮计划书：让记忆卡有内容

日期：2026-09-25。执行者：挂在 `D:\crq\src\coding-agent` 的 Cursor agent。
前置：第一轮 `AGENT-MEMORY-REBUILD.zh-CN.md` 和 `CHECKPOINT-1.md`。第一轮第 1 节的 5 条硬约束继续有效。
配套：`D:\crq\src\coding-harness\docs\sprint\HARNESS-SPRINT-2.zh-CN.md`。

## 0. 审计结论

第一轮做得扎实：版本控制已恢复，盘点如实，BM25 检索和新插件写好了，B3 接入了真正的 `validity` / `gate` 模块，旧入口保持不动，测试齐全。本轮要解决三个问题：

1. **卡片内容太薄**。样例里写的是 `tests: (none recorded)`，`approach` 只是一串文件名，`pitfalls` 是 `git: not found` 这类噪声。原因是 `public-trajectory.json` 没有保存命令参数。但每个记忆源目录下的 **`run/events.jsonl` 保存着完整的工具调用参数和模型原话**，例如 `docs/upgrade/evidence/A5-memory-pool-76-s2/builds/pytest-dev__pytest-5221/run/events.jsonl` 和 `A5-memory-pool-75-s1-smoke/<id>-reverify/run/events.jsonl`。
2. **不少"坑"是旧 harness 环境造成的**。那批轨迹跑在一个没装依赖、断网的 transport 镜像里，所以出现了缺 six / pluggy、pip 装不上之类的记录。harness 本轮会把运行环境换成装好依赖的镜像，这些"坑"届时不再成立，写进记忆只会误导模型。
3. **B3 的离线检查没有意义**。检查时没有目标仓库的代码，排上的卡全部被拒。20 道目标题的 base 源码包在 `D:\crq\src\coding-harness\docs\upgrade\evidence\A5-harness-preflight-12-host-sources\tasks\<目标题 id>\source.tar.gz`。

另外，源题验证只拿到 1 条结果（5103 partial），原因是 harness grader 有问题。harness 本轮会用新 grader 重跑，结果写回同一个文件。

## 1. 本轮规则补充

- 开工前打 tag `mem2-start`。继续往 `docs/sprint/PROGRESS.md` 追加记录，标题用"第二轮 第 N 步"。
- 默认不调模型。第 3 步的 LLM 提炼是可选的，花费上限仍是 3 CNY。
- 解压目标题源码时放到仓库外的临时目录，比如 `D:\crq\tmp\a5-targets\<id>\`，不要进 git。**只解压 `source.tar.gz`（base 源码），不要读同目录或其他地方的 gold / test patch。**

## 2. 分步计划

### 第 1 步：从原始事件流重新提取（不花钱）

1. 为每条记忆源定位 `run/events.jsonl`：优先用快照行 `source_dir` 下的 `run/events.jsonl`；75-s1-smoke 的源目录是 `-reverify` 结尾，以快照指向的那个为准。找不到的记进 PROGRESS。
2. 注意 payload 可能被外置成 artifact 引用（`artifact_ref`，`sensitive: true`），实际内容在同一个 run 目录的 session 或 artifacts 里。两种情况都要处理，读不到就跳过该字段，并记录原因。
3. 提取以下内容：
   - **读过和改过的代码范围**：`read_file` 的 path 和 offset / limit，`search_code` 的 pattern 和 path；
   - **实际跑过的命令**：`run_command` 的 `command`。只保留和测试、复现相关的命令（含 `pytest`、`runtests.py`、`python -c`、`python -m` 的），去重，截断到合理长度；
   - **模型对问题的诊断**：从模型文本里找出第一次准确说出原因的段落，以及最终回答，各取 1–3 句；
   - **改动的函数和类**：解析 `candidate-delta.json`，对比 base 和改动后的内容，找出被改动的 `def` / `class` 名字（能用 `ast` 就用 `ast`，失败时退回正则）。
4. **泄漏检查**：这些事件是模型在源题上运行时产生的，理论上不含 grader 私有信息，但仍要检查。对 20 道目标题的 gold / test patch 片段和 F2P 名单做 sentinel 检查，保证提取结果里没有这些内容。

### 第 2 步：过滤旧环境造成的噪声（不花钱）

写一个可测试的过滤函数，把以下几类从 `pitfalls` 和命令里去掉，或者单独标记为 `legacy_env_artifact`，不渲染给模型：

- `pip install`、`pip download`、`No module named (six|pluggy|attr|py|more_itertools|...)` 这类缺依赖的问题；
- `git: not found`、网络不可用、`find /` 全盘搜索；
- 手写 stub 模块（`/tmp/stubs` 之类）。

保留和仓库本身相关的经验，例如"测试在 `testing/` 下"、"django 用 `tests/runtests.py`"、"某模块必须和某模块一起改"。规则清单写进代码注释和 PROGRESS。

### 第 3 步：重新生成记忆卡

用第 1、2 步的结果重新填 `MemoryCard`。每张卡渲染后控制在约 1500 字节，头部的验证状态标记保持不变。目标是每张卡都有：

- `files`：改过的在前，带关键行号范围；
- `tests`：至少一条实际跑过的测试命令（如果源轨迹里确实没跑过，就写 `none run in source attempt`，不能再写 `none recorded`）；
- `approach`：诊断的 1–2 句，加上改动的函数 / 类名；
- `pitfalls`：过滤后剩下的仓库相关经验，允许为空。

**可选 LLM 提炼**（≤ 3 CNY）：规则提取后 `approach` 仍然空泛的卡，每条调用 1 次，输入是诊断原话和 diff 摘要，输出 2–3 句思路。保存 prompt、模型、token 数和费用，并标记 `llm_distilled`。先做规则版，看过结果再决定要不要做这一项。

新快照另存为 `benchmarks/a5/memory-cards-v3.jsonl`，不覆盖 v2。补测试：字段非空的比例、渲染后不超长、sentinel 检查、过滤函数的用例。

### 第 4 步：B3 对着真实目标源码检查（不花钱）

1. 把 20 道目标题的 `source.tar.gz` 解压到仓库外的临时目录（见第 1 节），**只解压 base 源码**。
2. 用真实目录作为 `target_root`，重跑 20 道题 × B1 / B2 / B3 的离线检索。记录每道题选中哪些卡、打多少分，以及 B3 的 `valid` / `invalid` / `unknown` 和原因。
3. 如果 B3 大面积因为"路径不存在"拒绝（版本跨度大，文件被挪走了），加一条规则：路径不存在，但卡片里的关键函数 / 类名能在目标树里搜到，就判为 `unknown`（`relocated`），不判 `invalid`。`unknown` 按现有 gate 规则处理，并在报告里单独计数。改规则前后的数字都要记下来。

### 第 5 步：接入新的源题验证结果

harness 会更新 `D:\crq\src\coding-harness\docs\sprint\memory-source-verification.json`，格式不变，可能新增可选字段 `calibrated`。

- 文件更新了（看修改时间，或者 `pass` / `partial` / `fail` 的条数变多了），就重新生成 v3 卡片的状态字段。
- 还没更新，就先按现有文件生成，在 PROGRESS 里注明"等 harness 第二轮第 4 步"。

## 3. 审计节点

写 `docs/sprint/CHECKPOINT-2.md`，一页以内：

- `mem2-start..HEAD` 的提交列表；
- 贴 3 张 v3 卡的渲染原文：django、pytest、sklearn 各 1 张；
- 11 张卡的字段完整度表：每张卡的 `tests`、`approach`、`pitfalls` 是否有实质内容；
- 20 道目标题 × B1 / B2 / B3 的离线选择表，B3 用真实目标源码，改规则前后的数字都列出来；
- 验证状态分布；
- 是否做了 LLM 提炼、花了多少钱。

然后停下，等审计。

## 4. 本轮不做的事

- 不扩充记忆源，不造新轨迹（等 harness 的 B0 稳定之后再做）。
- 不改 coding-harness 仓库，不跑真实 A5。
- 不改旧入口 `load_public_episodes` / `A5PublicMemoryPlugin`，新入口 `MemoryCardPlugin` 的签名保持不变。
