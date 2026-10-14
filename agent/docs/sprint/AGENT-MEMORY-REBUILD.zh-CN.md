# coding-agent 记忆重建计划书

日期：2026-09-24。执行者：挂在 `D:\crq\src\coding-agent` 的 Cursor agent。
配套：`D:\crq\src\coding-harness\docs\sprint\HARNESS-CAPABILITY-SPRINT.zh-CN.md`（harness 侧计划，另一个对话执行）。

## 0. 背景：为什么改方向

A5 的 240 行矩阵暂停。harness 侧先把 B0（不加记忆）的解题能力做起来；agent 侧趁这段时间把记忆做成真正有内容、能检索、能说清楚的东西。当前问题（已核对源码）：

- **A5 实际注入走的是另一套代码**。`reposkill_agent/memory/public_runtime_view.py`（139 行）没有用到 A2–A4 做的 `MemoryRecord`、`gate.py`、`validity.py`、`record_store.py`、`dependency_index.py`。
- **检索太粗**：`select_public_episodes` 只看同仓库，按"3 个字母以上的词取交集"打分，`the`、`and` 也计入。实际效果接近"同仓库随便挑 2 条"。
- **B1 和 B2 几乎没有区别**：
  - B1 是原始轨迹的截断 JSON：题目前 500 字、前 8 段观察、动作名。
  - B2 是动作列表 JSON。
  - 两者都没有提炼出"相关代码在哪、怎么跑测试、踩了什么坑、修复思路"。
- **B3 的"有效性"只检查文件是否存在**。
- 代码里硬断言 `len(episodes) != 11`。
- 11 条记忆全都没有用题目自己的测试验证过（`full_grader_validated=false`）。其中 `pytest-5103` 那条，模型改完的下一轮自己就说"实现有问题"。
- 覆盖面有缺口：sphinx 的 4 道目标题一条记忆都没有；源题和目标题的版本跨度较大。
- **版本控制失效**：仓库根目录有 `.git`，但 `git` 报 "not a git repository"。

## 1. 工作方式（放宽后的规则）

之前 A5 的合同、hash lock、双端复核、canonical handoff 更新等流程**全部暂停**，不要再新增这类文件。

保留的硬约束只有这些：

1. **不泄密**：`.env` 和 key 不进 git、不进日志。
2. **不泄露答案**：记忆内容不能包含 20 个 pilot 目标题的 gold patch、test patch、隐藏测试或 F2P/P2P 名单。记忆只能来自**其他题**的公开轨迹和改动。源题集合和目标题集合必须保持不相交，并用单元测试检查。
3. **花钱上限**：本计划默认不调真实模型。如果做 LLM 离线提炼（见第 3 步），累计 **≤ 3 CNY**，每次调用的 token 数和费用记进进度日志。
4. **git 纪律**：小步提交，提交前跑相关测试；不删除旧报告和旧数据。
5. **不改 coding-harness 仓库**。harness 通过 `src/policy/reposkill.py` 调用本仓库的这两个入口：`load_public_episodes(snapshot_path)` 和 `A5PublicMemoryPlugin(variant=, episodes=, repo=, issue=, target_root=, max_bytes=)`，插件方法是 `async decide(policy_input) -> dict`。**旧入口保持可用**，新实现用新的名字并行提供（见第 4 步），在进度日志里写清楚新入口的签名，由用户转给 harness。

日常记录只维护一个文件：`docs/sprint/PROGRESS.md`。每完成一步追加一小段：改了什么、测试结果、下一步计划。

## 2. 分步计划

### 第 0 步：版本控制（先做）

1. 检查 `.git`：`Get-ChildItem .git -Force`。如果它是空的或已损坏，没有可恢复的历史，就把它改名为 `.git.broken-20260924` 做备份，然后执行 `git init`。如果其实有历史、只是权限或 `safe.directory` 的问题，就修复并保留历史。
2. 检查 `.gitignore`：
   - 现在全局忽略了 `*.jsonl`，会导致记忆快照和清单这类小文件无法跟踪。改成只忽略 `traces/` 等目录下的 jsonl；本仓库需要跟踪的小型数据文件（小于 1MB）单独放行。
   - 根目录的论文 PDF，移到 `docs/papers/` 后忽略，或直接忽略。
   - `.tmp/`、`.pytest-run-final/`、`.ruff_cache/` 这类目录加入忽略。
3. 跑一次测试：`python -m pytest -q`（用本仓库实际使用的解释器）。把通过和失败的数量记进 PROGRESS.md。
4. 做初始提交 `baseline snapshot 2026-09-24`。提交前确认没有 `.env`、key，也没有大于 5MB 的文件。打 tag：`pre-memory-rebuild`。

完成标准：`git log` 能看到初始提交，tag 已打，测试基线已记录。

### 第 1 步：如实盘点（不花钱，半天以内）

写 `docs/sprint/MEMORY-INVENTORY.md`，一页以内：

- A5 真实运行路径上用到了哪些模块（`public_runtime_view.py`、`integrations/harness_h4.py` 等）；
- 哪些模块只在离线 demo 或 fixture 里用到（`memory/records.py`、`gate.py`、`validity.py`、`record_store.py`、`builder.py`、`dependency_index.py`，以及 `eval/upgrade_demo.py` 等），各自能做什么；
- 11 条记忆源题的清单：仓库、版本、源目录、轨迹里实际有哪些字段。

目的是分清"已经做好的离线能力"和"真正在实验里生效的东西"，第 3、4 步直接复用前者。

### 第 2 步：接入源题验证结果（依赖 harness，不花钱）

harness 侧会生成 `D:\crq\src\coding-harness\docs\sprint\memory-source-verification.json`，内容是用 grader 给 11 条源题的历史改动打的分：`pass` / `partial` / `fail` / `grader_unavailable`。

- 文件已经存在，就读进来。每条记忆的验证状态映射为 `validated_fix`（pass）、`partial_attempt`（partial）、`failed_attempt`（fail）或 `unverified`（其他情况）。
- 文件还不存在，就先全部标为 `unverified`，接着往下做，等文件出现后再补。

### 第 3 步：记忆提炼重做（主要工作）

目标：每条源记忆生成一张有内容的**记忆卡**。沿用或扩展现有的 `MemoryRecord`（`memory/records.py`），不要另起炉灶。每张卡至少包含：

| 字段 | 来源 |
|---|---|
| `repo`、`version`、`source_id` | 快照行 |
| `issue_summary`（1–2 句） | 轨迹里的 `issue_summary` |
| `relevant_files`（读过和改过的路径，改过的排在前面） | 轨迹 `actions` 里 `tool:path` 格式的条目 |
| `test_commands`（实际跑过的测试命令） | 轨迹里 `run_command` 的参数；如果轨迹没记参数，就从 observations 里提取，提取不到就留空 |
| `env_pitfalls`（缺依赖、导入错误、大文件读取的绕法等） | `failure_notes` 和 observations |
| `fix_approach`（修复思路，2–4 句） | `candidate-delta.json` 的改动文件和 diff 摘要，只写文件和思路，不贴整段代码 |
| `verification_status` | 第 2 步 |
| `dependencies`（相关的文件和符号） | 用于第 4 步的 B3 |

做法：

1. **先用规则提取**，能填多少填多少，全程不调模型。
2. **可选**：对规则填不好的 `fix_approach` 和 `env_pitfalls`，用 LLM 离线提炼。每条源记忆 1 次调用，累计 ≤ 3 CNY。prompt、模型、token 数和费用都要保存，生成的内容标记为 `llm_distilled`。
3. 渲染给模型看的文本时，每张卡控制在大约 1500 字节以内，开头标明验证状态，例如 `[historical attempt on a different issue in this repo; status=unverified — use as navigation hints, not as the answer]`。
4. 新快照另存为 `memory-cards-v2.jsonl`，不覆盖旧快照。

补单元测试：

- 卡片字段完整；
- 渲染后的文本不超长；
- 20 个 pilot 目标题的 ID、gold patch 片段都不会出现在任何卡片里（用 sentinel 检查）；
- 源题集合和目标题集合不相交。

### 第 4 步：检索和变体重做

新建入口，旧入口保留：

- `load_memory_cards(path) -> tuple[MemoryCard, ...]`
- `MemoryCardPlugin(variant=, cards=, repo=, issue=, target_root=, max_bytes=4096)`，提供 `async decide(policy_input) -> dict`，返回格式和 `A5PublicMemoryPlugin` 相同：`schema_version`、`candidates`、`state`、`events`、`action_proposals`。

检索：

- 在同仓库内按 BM25 打分（自己写一个简单实现就行，不引入向量库），带停用词表；再加上"题目文本里提到的路径、模块名或符号"和卡片 `relevant_files` 的重合加分。
- **允许一条都不选**：分数低于阈值时返回空，并记录 `no_relevant_memory`。
- 去掉 `len(episodes) != 11` 这类数量硬断言。

变体定义，按总目标文档 E-A1 的原意：

- **B0**：不注入。
- **B1 简单检索**：用同一套 BM25 检索**原始轨迹文本**，注入截断后的原文。
- **B2 结构化经验**：同一套检索，注入**记忆卡**渲染后的文本。
- **B3 结构化经验 + 有效性检查**：在 B2 的基础上，用现有的 `memory/validity.py` 和 `gate.py` 检查 `dependencies`。至少要检查文件存在，以及关键符号（函数名、类名）还在目标仓库里；检查结果分成 `valid`、`invalid`、`unknown`，`invalid` 的卡不注入。拒绝原因写进 events。

B1、B2、B3 三组必须使用同一个来源池、同一个检索器、同一个注入字节上限。

补单元测试：

- B0 不注入；
- B1 和 B2 在同一题上选中的来源相同，只是文本形式不同；
- B3 在符号被删除的 fixture 上会拒绝；
- 低分时一条都不选；
- 注入总字节不超过上限。

### 第 5 步（审计后再做）：扩充记忆来源

sphinx 没有记忆；其他仓库每个只有 2–4 条。扩充需要用 harness 跑真实模型来造轨迹，应该等 harness 的 B0 能力提升之后再做，否则造出来的还是低质量轨迹。这一步只写方案，不执行：需要哪些源题（不能和 20 个目标题重叠）、预计花费多少。

## 3. 审计节点（完成第 4 步后停下）

写 `docs/sprint/CHECKPOINT-1.md`，内容一页以内：

- `pre-memory-rebuild..HEAD` 的提交列表；
- 11 张记忆卡的示例：挑 2 张，贴出渲染后的原文；
- 每道 pilot 目标题在 B1、B2、B3 下会选中哪些记忆，打多少分。这一项零成本，直接离线跑检索就能得到，用来提前判断有没有题"一条都选不到"；
- 新插件入口的签名，以及 harness 侧需要改的地方（通常只是 `register_public_memory` 换一个工厂函数）；
- 第 5 步的扩充方案和预算估计。

然后停下，等用户找审计者看过再继续。

## 4. 本阶段不做的事

- 不跑真实 A5 矩阵，不跑 pilot 目标题。
- 不更新 `configs/a5/canonical-handoff.json` 这类旧协议文件，也不新增合同或 lock。
- 不改 coding-harness 仓库。
- 不引入向量数据库，也不做 LLM router 或多 agent 调度。
