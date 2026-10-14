# CHECKPOINT-P2：发布前整理（A 部分）和 monorepo（B 部分）

日期：2026-10-14。执行方：本地 Cursor agent。依据：`docs/publish/PUBLISH-CONTRACT.zh-CN.md` 第 1、3、4、6、7 节，`docs/publish/AUDIT-P1.zh-CN.md` 第 0–5 节。

**结论：A 部分 6 步都已提交；monorepo 建在 `D:\crq\src\coding-agent-mono\`，243 个提交、23 个 tag、`.git` 18.5 MiB；第 4 节 6 项检查都没有阻断项。没有 push，没有改写历史，没有调用模型或付费 API。停在这里等审计。**

本文件和附件 `CHECKPOINT-P2-LISTS.md` 没有提交，留在 harness 工作区，由审计决定是否提交。

## 1. A 部分的提交号

| 步 | 仓库 | 提交 | 内容 |
| --- | --- | --- | --- |
| A1 | harness | `fbdffd6` | 35 个 private 文件 `git rm --cached`，本地保留；新建 `docs/upgrade/evidence/README.md` |
| A2 | harness | `aad745d` | `.tmp/` 根目录 20 个 `.py` 复制到 `scripts/audit/`（与原文件逐字节相同），加 `scripts/audit/README.md` |
| A3 | harness | `5dd05df` | `docs/AGENT-INTERVIEW-GUIDE.zh-CN.md`、`docs/INTERVIEW-DEMO.zh-CN.md` `git rm --cached`，加进 `.gitignore` |
| A3 | agent | `572337d` | `docs/SESSION-HANDOFF.zh-CN.md` `git mv` 到 `docs/archive/`，README“参考”一节的路径同步 |
| A4 | agent | `d2ca276` | 新建 `docs/memory-v2/DIAGNOSIS-AND-LITERATURE.zh-CN.md`；`MEMORY-FINAL-REPORT` 两处引用改指新文件；`.gitignore` 加 `HANDOFF-BRIEF`、`OPTIONS` |
| A5 | agent | `8959cc4` | README 第 20 行的本机解释器路径改成“任意 Python 3.11+ 环境（上面命令里的 `python`）” |
| A6 | harness | `62864e8` | 合同和 prompt 从 `docs/` 移到 `docs/publish/`；提交 `docs/publish/` 下 5 个文件 |

现在两个原仓库的 HEAD：harness `62864e8`，agent `d2ca276`。harness 工作区除了本文件和附件之外是干净的；agent 工作区只剩未跟踪的 `docs/memory-v2/papers/`（见第 5 节第 2 条）。

### 1.1 A1 的细节

- 移出的是审计第 1 节认定的 35 个：`H5-interop/*/handoff/private/*` 16 个，`R2-real/{pilot-01,wrapper-01}/private/*` 15 个，`full-repo-grader/attempt-0{1,2}/private/{known-good,overlay}.json` 4 个。`scripts/sprint2_debug_gold.py` 按审计保留。
- `docs/upgrade/evidence/README.md` 写明：private 材料只在本地，HEAD 不跟踪（`.gitignore` 规则 `docs/upgrade/evidence/**/private*`）；历史里还能看到一部分，即 `7bb4395` 的 7 个 `private-spec*.json`（`b5cb425` 已删）和这次 `git rm --cached` 的 35 个；sha256 仍记在被跟踪的 manifest 里。
- HEAD 里还提到这些文件的地方（只列不改）。没有任何 markdown 链接指向 `private/`。
  - 记录 sha256 的证据 JSON：`H5-interop/{offline-01..04,real-01..04}/handoff/manifest.json`，`R2-real/pilot-01/experiment.json` 第 329–331 行，`R2-real/wrapper-01/experiment.json` 第 846–857 行，`R2-real/wrapper-01/pilot-01-hashes.json` 第 20–22 行，`full-repo-grader/cli-known-good-assignments.json:6`，`full-repo-grader/cli-known-good/assigned.json:6`。
  - 文档：`docs/upgrade/FULL-REPO-GRADER-HANDOFF.zh-CN.md:46`（提到 `private-spec`）。
  - 用通用相对路径读 private 的脚本：`scripts/audit_repo_grader.py:35-36`、`preflight_repo_grader.py:40-41`、`prepare_repo_grader.py:88-89`、`run_reposkill_interop.py:108`、`run_summary_pilot.py:179`、`run_summary_wrapper.py:199`。
  - agent 侧是通用写法，不指向被移出的文件：`docs/upgrade/H4-ADAPTER.md:55`、`reposkill_agent/eval/h4_fixture.py:126-127`、`tests/test_harness_h4_adapter.py:260,275`。

### 1.2 A2 的扫描结果

20 个脚本提交前按第 4 节第 1–3 项扫过：

- 密钥 0 命中。
- 私有字段只出现在读取逻辑里，不含 patch 内容：`audit_b0_deltas.py` 第 27、52 行，`audit_v6.py` 第 70–77 行。
- 本机路径：大多数脚本里有 `D:\crq`；`extract_codex.py:5` 有 `C:\Users\Administrator\.codex\sessions`，`user_msgs.py:5` 有 `C:\Users\Administrator\.cursor\projects\...\agent-transcripts`。按第 4 节第 3 项，这类命中不阻断。没有扫描结果干净的脚本被排除，20 个都提交了。
- `scripts/audit/README.md` 写明：这些是一次性审计脚本，不维护；`case_mem.py` 就是 `A5-CASE-DATA.md` 引用的 `.tmp/case_mem.py`；脚本写死了本机路径；`audit_b0_deltas.py` 和 `audit_v6.py` 读本地 `runs/sprint5-main-private/`，只在内存里比较；`extract_codex.py`、`user_msgs.py` 读的是本地对话记录（记录本身没有进 git）。

### 1.3 A3 的细节

- `README.md`、`README.zh-CN.md`、`docs/LEARNING.zh-CN.md`、`docs/PROJECT-OVERVIEW.zh-CN.md` 里没有指向两份面试文档的链接（逐个检查，0 处），所以不需要删链接。
- 其他提到这两个文件名的地方都是纯文本，没有改：`docs/archive/` 下的 `DEMO-SCRIPT`、`IMPROVEMENT-PLAN`、`SOLID-*`，`docs/changes/` 下的 `P0-4-DEMO-PACK`、`P0-A-CLOSEOUT`、`SOLID-A-BATCH-CLOSEOUT`、`SOLID-D2-DEMO-CLOSEOUT`。agent 仓库里没有提到它们的地方。
- agent 的 `SESSION-HANDOFF` 只同步了 README 里的路径。`docs/codebase-structure-detailed.zh-CN.md:345`、`docs/project-chronology.zh-CN.md:404,463` 和文件自身第 130 行还写着旧路径，都是纯文本，没有改（和 P-1 的做法一致）。

### 1.4 A4 的细节和一处偏离

- 新文件第一行是“摘自 2026-10-13 的方案调研，原文件未公开”，后面依次是 OPTIONS 第 1、2、7 节，用脚本按标题切出、原样拼接，节标题保留原来的“## 1.”“## 2.”“## 7.”。
- **偏离（用户在本轮已确认）：** 第 7 节“读过的文件”里有一行指向桌面上的个人求职分析笔记，路径名透露了求职对象。按用户选择，这一行改成“- 一份本机个人笔记（未公开）”。其余 90 行逐字相同（脚本核对：不在原文里的行只有这 1 行）。
- 新文件里仍有 9 行 `D:\crq` 路径（第 7 节“读过的文件”），属于第 4 节第 3 项，不阻断。另外查过“面试、求职、岗位、简历、投递、resume、Desktop”，0 命中。
- `MEMORY-FINAL-REPORT.zh-CN.md` 第 20 行改成 `memory-v2/DIAGNOSIS-AND-LITERATURE.zh-CN.md` 第 2 节，第 43 行改成同一文件第 1 节。因为新文件保留了原节号，节号不需要变。
- agent `.gitignore` 加了 `docs/memory-v2/HANDOFF-BRIEF.zh-CN.md` 和 `docs/memory-v2/OPTIONS.zh-CN.md`。

### 1.5 A6 的细节

`docs/publish/` 提交了 5 个文件：`AUDIT-P1.zh-CN.md`、`CHECKPOINT-P1.md`、`CHECKPOINT-P1-LOCAL-INFO.md`、`PUBLISH-CONTRACT.zh-CN.md`、`PUBLISH-START-PROMPTS.zh-CN.md`。合同和 prompt 原来没有被跟踪，所以是普通移动，不是 `git mv`。

提交前扫过：

- `bearer` 的命中（`CHECKPOINT-P1.md:232`、`PUBLISH-CONTRACT.zh-CN.md:83`）都是写检查规则的那一行，不是密钥。
- 私有字段名和本机路径都出现在描述检查的文字里，不含 patch 内容。
- 这几份文件写了“读者是面试官”“用作简历链接”“求职背景”，也写了 `tmp/pdfs/resume-review/` 已删除这件事。是否提交，本轮问过用户，用户选择全部原样提交。

## 2. monorepo

位置：`D:\crq\src\coding-agent-mono\`，分支 `main`，HEAD `f22a261`。

做法：

1. 空的初始提交 `6474df2`。
2. 从两个原仓库 fetch `main`（`--no-tags`），tag 用 refspec `refs/tags/*:refs/tags/harness/*` 和 `refs/tags/*:refs/tags/agent/*` 改名带入。
3. `git subtree add --prefix=harness`（`d2b0bdb`）、`git subtree add --prefix=agent`（`c479478`）。没有用 `--squash`，原始提交全部保留。
4. 加子 README 头部和链接修正（`6085865`），加根 README（`f22a261`）。
5. 删掉了两个指向本机路径的 remote，`.git/config` 里没有 remote。P-3 需要另加 `origin`。

| 量 | 值 |
| --- | --- |
| 提交数 | 243（harness 170 + agent 68 + 初始 1 + 两次 subtree 合并 2 + README 2） |
| tag 数 | 23（`harness/` 14 个，`agent/` 9 个，都是轻量 tag） |
| `.git` 大小 | 19,376,165 字节（18.5 MiB）；`size-pack` 15.15 MiB，2 个 pack |

核对（脚本）：23 个 tag 的提交号和原仓库对应 tag 逐一相同；`HEAD:harness` 的树等于 harness `62864e8` 的树，`HEAD:agent` 的树等于 agent `d2ca276` 的树（README 提交之前核对）。冻结 tag 指向的是原始提交，根目录是原来的布局。用 `git worktree add <临时目录> agent/a6-retry-freeze-r2` 实际检出过一次，`scripts/analyze_a6_retry.py` 和 `docs/sprint/A6-R-PREREG.zh-CN.md` 都在，之后删掉了这个 worktree。

### 2.1 子 README（合同 3.2）

- `harness/README.md`、`harness/README.zh-CN.md`、`agent/README.md` 顶部各加了 3 行（两行引用说明加一个空行）：这是 monorepo 的一部分，原来是独立仓库，历史保留；总览回根目录 README。
- harness 两份 README 第 7 行（加头后是第 10 行）各有 2 个 `../coding-agent/...` 链接，改成 `../agent/...`。agent README 里没有指向 harness 的链接。正文其他部分没有改。
- 这些修改只在 monorepo 里，原仓库的 README 没有动。

## 3. 第 4 节检查结果

| 项 | 结果 | 阻断 |
| --- | --- | --- |
| 1 密钥 | 0 个可疑命中；`.env` 从未被跟踪 | 否 |
| 2 私有评测材料 | 历史中 129 个路径含这些字段，其中 107 个在 HEAD；按审计第 0 节只列不阻断 | 否 |
| 3 本机信息 | HEAD 中 `C:\Users\` 71 个文件，`D:\crq` 744 个文件；根 README 0 处 | 否 |
| 4 大小 | `.git` 18.5 MiB；HEAD 和历史里都没有超过 5 MB 的文件 | 否 |
| 5 测试 | harness 661 passed、22 skipped；agent 366 passed、1 skipped | 否 |
| 6 链接 | 根 README 两份共 24 个相对链接，0 个断链 | 否 |

### 3.1 密钥扫描

本机没有 gitleaks，也没有 detect-secrets。按合同用正则方案扫了 monorepo 全部历史：`rev-list --objects --all` 得到 8401 个 blob，逐个用 `cat-file --batch` 读。

- `sk-[A-Za-z0-9]{20,}`：0 命中。
- `Authorization: Bearer`：2 处，都是模板写法（值是变量）。
- `api_key\s*[:=]`：96 处。分类是：占位符 32，环境变量或变量 32，表达式 21，短字面量 9，空值 2；可疑 0。短字面量和表达式又逐行看过一遍（字符串只显示长度），都是测试里的假值、`your-deepseek-api-key` 这类示例，或者函数参数。
- 可疑命中 0，所以没有文件名或行号需要报告。
- `.env`：历史中没有任何 `.env` 或 `.env.*` 路径（`.env.example` 除外，内容是 `your-api-key`）。

### 3.2 私有评测材料

完整清单在附件 A 节，每个路径都标了字段，也标了是否在 HEAD。分类如下：

- **HEAD 里的 107 个：** 大多只出现字段名，没有 patch 内容。包括读写这些字段的代码和测试（如 `harness/scripts/run_swe_task.py`、`build_a6_attempts.py`、`agent/scripts/build_memory_cards.py`），描述合同和审计的文档（`docs/sprint/`、`docs/archive/`、`docs/changes/`、`docs/publish/`），以及 preflight 证据里记录 `test_patch` 哈希或路径的 receipt JSON。`harness/reports/examples/tmp_requests_{2674,863}_log.json` 和 `swebench_lite_real.md` 里有 SWE-bench 公开数据的 `FAIL_TO_PASS`。
- **不在 HEAD 的 22 个：** 都是子树并入前原始提交里的路径。其中 18 个只是同名文件的旧位置（如 `scripts/run_swe_task.py`），对应的带前缀文件已在 HEAD 里。另外 4 个是 P-1 已从 HEAD 移出的历史文件：`swebench_candidates.jsonl`、`swebench_candidates_short.jsonl`、`tmp_requests_2674.jsonl`、`tmp_requests_863.jsonl`，内容是 SWE-bench 公开数据。
- 本轮移出的 35 个 private 文件，内容里不含这三个字段名，所以不在这份清单里。它们仍在历史里，见 1.1。

### 3.3 本机信息（HEAD 中的被跟踪文件）

| 模式 | 文件数 | 出现次数 |
| --- | --- | --- |
| `C:\Users\` | 71 | 142 |
| `23500` | 53 | 81 |
| `Administrator` | 61 | 127 |
| `D:\crq` | 744 | 4496 |

文件名和逐文件计数在附件 B 节。比 P-1 多出的主要来自 `scripts/audit/`、`docs/publish/` 和 `DIAGNOSIS-AND-LITERATURE`。根目录 `README.md`、`README.zh-CN.md` 和子 README 新加的头部都是 0 处。

### 3.4 大小

- `.git` 是 19,376,165 字节；`count-objects -vH`：in-pack 12246 个对象，size-pack 15.15 MiB。
- HEAD 里没有超过 5 MB 的文件，历史里也没有超过 5 MB 的 blob。P-1 提到的两个 `known-good.json`，每个约 2 MB。
- `harness/tests/fixtures/repos` 在 HEAD 里有 15,868 个被跟踪文件，和合同里的数一致，没有动。

### 3.5 测试

- harness：`D:\crq\src\coding-harness\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp=<系统临时目录>`，结果 661 passed、22 skipped，耗时 99.45 s，退出码 0。
- agent：系统 Python（Anaconda 3.13.9，pytest 8.4.2），`python -m pytest -q -p no:cacheprovider --basetemp=<系统临时目录>`，结果 366 passed、1 skipped，耗时 213.91 s，退出码 0。agent 的 `pyproject.toml` 默认把 basetemp 和 cache 放在 `traces/` 下；为了不碰 `traces/`，用命令行参数改到了系统临时目录。
- 跑完后两个原仓库都没有被跟踪文件的改动。

### 3.6 链接

- 用脚本检查根 `README.md` 和 `README.zh-CN.md`：各 12 个相对链接，全部指向 monorepo 里存在的文件。
- 同一脚本核对过根 README 里每个数字都能在链接文件里找到：deepseek-flash、40 次、9/51、56、−1.8、[−8.3, +4.8]、0.72、−6.6、[−17.7, +3.8]、0.29、53、22、159、168/168、318/318 在 `MEMORY-FINAL-REPORT`；14 题、32/42、18/42 在 harness `PROJECT-HISTORY`；9 份、7/27、26/27 在 `wrapper-01/README.md`；20261013 在 `A6-R-PREREG`。
- 也检查了“revolutionary、significant、革命性、显著”这类词，两份根 README 都没有。
- 子 README：harness 两份 0 断链。agent README 有 1 个原来就断的链接，`reports/upgrade/a5-offline-20260921-v1/report.md`（`reports/` 下的产物没有被跟踪）。正文里还有一处原有的“显著”。按 3.2 节“正文其余部分不改”，这两处都没有动。

### 3.7 跨仓库和本机绝对路径的代码引用（合同第 1 节，只列不修）

HEAD 里有 53 个代码或配置文件、122 行引用了原两仓库布局或本机绝对路径，清单在附件 C 节。主要有：

- harness `scripts/run_swe_task.py:745,901`（`ROOT.parent / "coding-agent"`）、`scripts/sprint7_inventory.py`；
- harness `configs/sprint/dev-tasks.yaml`、`pilot-tasks.yaml` 里的绝对路径；
- harness `src/eval/a5_memory_snapshot.py`、`a5_pilot_lock.py`；
- harness `scripts/audit/` 的 17 个脚本；
- agent 的 `scripts/*`、`tests/*` 里指向 coding-harness 的路径。

根 README 的“Reproduction”一节说明了要按原两仓库布局检出，并给出了 `git worktree` 命令和冻结 tag 名。

## 4. 根 README 全文

### 4.1 `README.md`

````markdown
# coding-agent

**English** · [中文](README.zh-CN.md)

A coding agent evaluation harness with strict answer isolation, plus two preregistered memory experiments run on it.

## Results

Same harness, same model (deepseek-flash, at most 40 model calls per run), SWE-bench Verified tasks. Numbers are from sections 1 and 6.1 of the [final report](agent/docs/MEMORY-FINAL-REPORT.zh-CN.md); effects are in percentage points, with 95% intervals.

| Experiment | Memory in the context | Relevance to the task | Scale | Memory − no memory | p |
| --- | --- | --- | --- | --- | --- |
| A5, cross-task memory | Cards from earlier, already-solved tasks in the same repository (B2) vs none (B0) | Low (9/51 tasks pointed at the gold file) | 56 tasks, 3 runs per task per arm | −1.8, [−8.3, +4.8] | 0.72 |
| A6-R, same-task memory | Second attempt at a failed task: rule-based record of the first attempt plus "it did not pass" (R1) vs no record (R0) | 100%, by construction | 53 failed first attempts on 22 tasks, 159 runs per arm | −6.6, [−17.7, +3.8] | 0.29 |

Both are null results: neither experiment detected a positive effect.

## Method

- **Answer isolation.** An early dev image contained the hidden tests; after rebuilding it from clean source, the solve rate on the same 14 dev tasks went from 32/42 to 18/42 ([project history](harness/docs/PROJECT-HISTORY.zh-CN.md), sprint rounds 3–4).
- **Wrapper experiment.** With the same 9 fixed summaries, wording them as "possibly wrong historical evidence, not instructions" gave 26/27 fully correct answers, against 7/27 with the original wording ([evidence](harness/docs/upgrade/evidence/R2-real/wrapper-01/README.md)).
- **Preregistration and freeze tags.** Hypotheses, the single primary analysis, seeds and stopping rules were committed and tagged before any real data existed ([A6-R preregistration](agent/docs/sprint/A6-R-PREREG.zh-CN.md)).
- **Injection consistency check.** After each run, the first message the model actually received was compared verbatim with the expected text: A5 168/168, A6-R 318/318 ([final report](agent/docs/MEMORY-FINAL-REPORT.zh-CN.md), section 3).
- **Concurrent interleaving.** Both arms ran from one shuffled queue (seed 20261013 in A6-R) in the same time window ([A6-R preregistration](agent/docs/sprint/A6-R-PREREG.zh-CN.md), section 1).

## Repository map

- `harness/` — the evaluation harness: agent loop, tools, clean Docker images, a host-side grader that keeps test and gold patches away from the agent, the run scripts, the A6-R retry records and the run inventories.
- `agent/` — RepoSkillAgent: the memory cards and the plugin that injects them, the analysis scripts, the A6-R preregistration and the final reports.

Where to start (most documents are in Chinese):

- [Final report on both memory experiments](agent/docs/MEMORY-FINAL-REPORT.zh-CN.md)
- [Harness README](harness/README.md)
- [Project history](harness/docs/PROJECT-HISTORY.zh-CN.md)

## Reproduction

The two directories were developed and frozen as two sibling repositories, `coding-harness` and `coding-agent`, and the code refers to the other repository through that layout; some configs and evidence files also record absolute paths from the original machine. These paths were not rewritten here, so that the frozen tags still point at the code that actually ran. The tags keep the original commits, so a frozen state can be checked out in the original layout:

```
git worktree add ../coding-harness harness/a6-retry-freeze
git worktree add ../coding-agent agent/a6-retry-freeze-r2
```

Freeze tags:

- A5: `harness/a5-main-freeze`, `harness/a5-main-freeze-r1` to `-r4`, `agent/a5-main-freeze`
- A6-R: `harness/a6-retry-freeze`, `agent/a6-retry-freeze`, `agent/a6-retry-freeze-r1`, `agent/a6-retry-freeze-r2`

Running the agent needs Docker, the SWE-bench images and a DeepSeek API key. The analysis commands are listed in the appendices of the [A5 final report](agent/docs/A5-FINAL-REPORT.zh-CN.md) and the [final report](agent/docs/MEMORY-FINAL-REPORT.zh-CN.md).

## Related project

agentic-rl, a separate project that is not public yet, looks at changing agent behaviour through training (SFT, GRPO) instead of through the context.
````

### 4.2 `README.zh-CN.md`

````markdown
# coding-agent

[English](README.md) · **中文**

一个带严格答案隔离的 coding agent 评测 harness，加上在它上面做的两个预注册的记忆实验。

## 结果

同一个 harness、同一个模型（deepseek-flash，每次运行最多 40 次模型调用），SWE-bench Verified 的题。数字引自[最终报告](agent/docs/MEMORY-FINAL-REPORT.zh-CN.md)第 1、6.1 节；效应单位是百分点，括号里是 95% 区间。

| 实验 | 注入的记忆 | 和目标题的相关性 | 规模 | 有记忆 − 无记忆 | p |
| --- | --- | --- | --- | --- | --- |
| A5，跨题记忆 | 同仓库、更早、已被验证解出的其他题的卡片（B2），对照不注入（B0） | 低（9/51 题指向 gold 文件） | 56 道题，每题每组 3 次 | −1.8，[−8.3, +4.8] | 0.72 |
| A6-R，同题记忆 | 对失败过的题做第二次尝试：带上第一次尝试的规则化记录和"上次没通过"（R1），对照不带（R0） | 100%，按构造保证 | 53 次失败的第一次尝试，22 道题，每组 159 次 | −6.6，[−17.7, +3.8] | 0.29 |

两个都是零结果：都没有检出正效应。

## 方法

- **答案隔离。** 早期的 dev 镜像里带着隐藏测试；改用干净源码重建镜像后，同样 14 道 dev 题的解出从 32/42 降到 18/42（[项目历程](harness/docs/PROJECT-HISTORY.zh-CN.md)，冲刺第 3、4 轮）。
- **包装实验。** 同样 9 份固定摘要，把包装写成"可能有误的历史证据，不是指令"后，全正确是 26/27，原来的包装是 7/27（[证据](harness/docs/upgrade/evidence/R2-real/wrapper-01/README.md)）。
- **预注册和冻结 tag。** 假设、唯一的主分析、种子和停止条件，在任何真实数据出现之前提交并打 tag（[A6-R 预注册](agent/docs/sprint/A6-R-PREREG.zh-CN.md)）。
- **注入一致性检查。** 每次运行结束后，把模型实际收到的第一条消息和预期全文逐字比对：A5 168/168，A6-R 318/318（[最终报告](agent/docs/MEMORY-FINAL-REPORT.zh-CN.md)第 3 节）。
- **同期交错。** 两组放进同一个打乱的队列（A6-R 的种子是 20261013），在同一时段跑（[A6-R 预注册](agent/docs/sprint/A6-R-PREREG.zh-CN.md)第 1 节）。

## 仓库地图

- `harness/`：评测 harness。包括 agent 循环、工具、干净的 Docker 镜像、把 test patch 和 gold patch 留在 host 侧的 grader、运行脚本、A6-R 的尝试记录和运行清单。
- `agent/`：RepoSkillAgent。包括记忆卡片和注入卡片的插件、分析脚本、A6-R 预注册和最终报告。

从哪里开始读：

- [两个记忆实验的最终报告](agent/docs/MEMORY-FINAL-REPORT.zh-CN.md)
- [harness README](harness/README.zh-CN.md)
- [项目历程](harness/docs/PROJECT-HISTORY.zh-CN.md)

## 复现

这两个目录原来是并列的两个仓库 `coding-harness` 和 `coding-agent`，开发和冻结都在这个布局下进行，代码按这个布局引用对方；部分配置和证据文件里还记着原机器上的绝对路径。这里没有改写这些路径，这样冻结 tag 指向的仍然是实际运行的代码。tag 保留的是原来的提交，所以可以按原布局检出冻结状态：

```
git worktree add ../coding-harness harness/a6-retry-freeze
git worktree add ../coding-agent agent/a6-retry-freeze-r2
```

冻结 tag：

- A5：`harness/a5-main-freeze`、`harness/a5-main-freeze-r1` 到 `-r4`、`agent/a5-main-freeze`
- A6-R：`harness/a6-retry-freeze`、`agent/a6-retry-freeze`、`agent/a6-retry-freeze-r1`、`agent/a6-retry-freeze-r2`

运行 agent 需要 Docker、SWE-bench 镜像和 DeepSeek API key。分析命令见 [A5 最终报告](agent/docs/A5-FINAL-REPORT.zh-CN.md)和[最终报告](agent/docs/MEMORY-FINAL-REPORT.zh-CN.md)的附录。

## 关联项目

agentic-rl 是另一个项目，还没有公开，研究的是靠训练（SFT、GRPO）而不是靠上下文来改变 agent 的行为。
````

## 5. 需要审计决定的事

1. **DIAGNOSIS 里那一行的偏离**（见 1.4）：用户本轮已确认，请审计知悉。
2. **agent `docs/memory-v2/papers/`**：3 个 arXiv PDF（2507.06229、2507.23361、2509.25140），一直没有被跟踪，也没有被 ignore，所以 `git status` 里会一直显示。本轮没有动。可以加进 `.gitignore`，也可以保持原样。
3. **根 README 的取舍**：
   - 结果表只用了第 1、6.1 节的数。A5 的 B0 解出 115/168 在第 4 节，没有放进表里。
   - p 值用的是第 1 节的 0.72 和 0.29，没有用 5.2 节的 0.288。
   - 冻结 tag 列了全部 A5、A6-R 相关 tag；`harness/a5-main-closeout` 不是冻结 tag，没有列。
4. **monorepo 里的子 README 和原仓库不同**：头部 3 行和 `../agent/` 链接只在 monorepo 里改了，原仓库 README 没有改。
5. **本文件和附件 `CHECKPOINT-P2-LISTS.md` 还没有提交。** 附件里有 744 个含 `D:\crq` 的文件名。
6. **P-3 前要做的：** monorepo 没有 remote，需要 `git remote add origin https://github.com/RichChen/coding-agent.git` 后再 `git push origin main --tags`。按合同第 5 节，审计确认之后才 push。
