# 合同：把 coding-harness 和 coding-agent 整理后发布到 GitHub

日期：2026-10-14。执行方：本地 Cursor agent。审计方：Claude Code。
目标仓库：`https://github.com/RichChen/coding-agent.git`（私有，空仓库）。

## 0. 目标和读者

- 读者是面试官：从简历上的链接点进来，3 分钟内看懂这个项目做了什么、结论是什么、证据在哪里。
- 两个项目放进**同一个仓库**（monorepo），保留两边的完整 git 历史和 tag。
- 本地目录要整理干净：根目录只留入口文件，过程文档归档，临时目录删除。

## 1. 结构决定（审计已定，不要改）

最终的 GitHub 仓库布局：

```
coding-agent/                 （GitHub 仓库根）
├── README.md                 总入口：一页讲清两个项目和结论（英文）
├── README.zh-CN.md           同上的中文版
├── harness/                  原 coding-harness 仓库，历史保留
└── agent/                    原 coding-agent 仓库，历史保留
```

合并方法：用 `git subtree add`（或 `git read-tree --prefix` 的等价做法）把两个仓库分别放进 `harness/`、`agent/`，保留提交历史。两边原来的 tag 改名后带入，加前缀 `harness/` 和 `agent/`，例如 `harness/a5-main-freeze`、`agent/a6-retry-freeze-r2`。

**两个本地仓库本身不动。** 合并在新目录 `D:\crq\src\coding-agent-mono\` 里做。原仓库保持现状，作为备份和回退点。

路径影响：两边代码里互相引用的路径（`ROOT.parent / "coding-agent"`、`D:\crq\src\coding-harness` 之类）在 monorepo 里会失效。**本合同不要求修**，只要求做两件事：在 README 里说明"复现需要按原来的两仓库布局检出"；在第 4 节的检查里列出这些引用。理由是 A5、A6 的冻结 tag 指向的是原布局下的代码，改路径会让"冻结代码 = 运行代码"这条证据链断掉。

## 2. 发布前的整理（在两个原仓库里，各自小步提交）

### 2.1 必须从 git 中移除的（`git rm --cached`，本地文件保留）

| 仓库 | 路径 | 原因 |
| --- | --- | --- |
| harness | `tmp_requests_*.jsonl`、`swebench_candidates*.jsonl`（根目录） | 临时产物 |
| harness | `CLAUDE.md`、`AGENTS.md`、`CLAUDE-CODE-IMPROVEMENTS.md`、`CLAUDE-CODE-RESUME-POLISH.md` | 给 AI 工具的指令文件，里面有本机绝对路径 |
| harness | `docs/upgrade/evidence/**/handoff/private/**`（共 36 个含 private/gold 的路径，先逐个列出） | 名字带 private 的评测材料，先审计再决定 |
| agent | 根目录的 `*-PLAN.zh-CN.md`、`*-RUNBOOK.zh-CN.md`、`NEW-PROJECT-BRIEF.zh-CN.md` | 移到 `docs/archive/`（用 `git mv`，不是删除） |

**注意：`git rm --cached` 只影响之后的提交，已经提交过的文件仍然留在历史里。** 第 1 节要求保留完整历史，所以这些文件在 push 之后，仍然能从旧提交里看到。仓库是私有的，这一点影响不大；但用户以后如果要把仓库改成公开，就要另做决定：要么接受历史里有这些文件，要么另建一个不带历史的公开仓库。P-1 的 CHECKPOINT 必须把这一点写明，并列出历史中出现过、但最新提交里已经移除的敏感路径。

`private` 那一项要先停下审计：把 36 个路径和每个文件的前 3 行写进 CHECKPOINT，由审计决定移除还是保留。只列内容摘要，不要贴 gold patch 或 test patch 全文。

### 2.2 移进归档目录（`git mv`）

- harness 根目录的 `LEARNING.zh-CN.md`、`PROJECT-OVERVIEW.zh-CN.md` → `docs/`。
- harness `docs/` 下的 `SOLID-*`、`IMPROVEMENT-PLAN`、`DEMO-SCRIPT` 等过程文档 → `docs/archive/`。
- 两边 `docs/sprint/` 不动：它是 A5/A6 的证据链，审计文件、CHECKPOINT、冻结记录都在里面，路径被大量互相引用。

### 2.3 本地删除（不在 git 里，删前列清单）

harness：`.tmp*/`、`.pytest*`、`.a5-test-basetemp/`、`tmp*/`、`__pycache__/`、`cursor-a602-latest.txt`。
agent：`.tmp/`、`.pytest-run-final/`、`.ruff_cache/`、`.git.broken-20260924/`（确认是空目录再删）。

**不删**：`runs/`、`traces/`、`.venv/`、`.swebench_envs/`、`baseline/`、`.env`、根目录 PDF。它们已经被 ignore，留在本地，供复现用。删除前把要删的目录和大小写进 CHECKPOINT。

### 2.4 `.gitignore` 补充

两边都加：`.tmp*/`、`.pytest*/`、`.ruff_cache/`、`*.broken-*/`、`.claude/`、`.agents/`、`.cursor/`。

## 3. 新写的文档

### 3.1 monorepo 根 `README.md`（英文）和 `README.zh-CN.md`

不超过一屏半，结构固定：

1. 一句话：这是什么（一个带严格答案隔离的 coding agent 评测 harness，加上在它上面做的两个预注册的记忆实验）。
2. 结果表：A5、A6-R 两行，数字照抄 `agent/docs/MEMORY-FINAL-REPORT.zh-CN.md` 第 1、6.1 节，不要四舍五入成别的值。
3. 方法亮点，4–5 条，每条一句话加一个指向证据文件的链接：答案泄漏的发现与修复（32/42 → 18/42）；包装实验（7/27 → 26/27）；预注册和冻结 tag；注入一致性检查；同期交错。
4. 仓库地图：`harness/`、`agent/` 各一句话，加上"从哪里开始读"的 3 个链接（最终报告、harness README、项目历程）。
5. 复现说明：原两仓库布局，以及冻结 tag 的名字。
6. 关联项目：agentic-rl 只写一句话，不放链接（那个仓库还没公开）。

写作要求：平实，不用"革命性""显著"之类的词；零结果照实写，不要包装成正结果；每个数字都能在链接的文件里找到。

### 3.2 两个子目录的 README

各自顶部加 3 行："这是 monorepo 的一部分，返回根目录看总览"，并修掉指向对方仓库的绝对路径链接，改成相对路径 `../agent/...`、`../harness/...`。正文其余部分不改。

## 4. 发布前检查（全部通过才能 push）

1. **密钥扫描**：对 monorepo 的**全部历史**跑 `gitleaks detect`（没有就用 `pip install` 装固定版本的 `detect-secrets`，或用正则扫 `sk-[A-Za-z0-9]{20,}`、`api_key\s*[:=]`、`Authorization: Bearer`）。`.env` 在两边历史里从来没被跟踪过，扫描要确认这一点。有任何命中就停下，不 push。
2. **私有评测材料**：全部历史里出现 `FAIL_TO_PASS`、`test_patch`、`"patch":` 字段的文件，列出路径。按 2.1 节，这些在审计决定之前不 push。
3. **本机信息**：扫描 `C:\\Users\\`、`23500`、`Administrator`、`D:\\crq` 出现在哪些被跟踪的文件里，只列计数和文件名。这些不阻断（证据文档里有大量本机路径），但新写的 README 里不能有。
4. **大小**：monorepo 的 `.git` 大小；单个文件超过 5 MB 的列出来。harness 的 `tests/fixtures/repos` 有 15,868 个文件，保留，不要动。
5. **测试**：在两个原仓库里各跑一次全量测试，写下结果（harness 用 `.venv`，agent 用系统 Python）。monorepo 里不要求测试能跑（路径原因，见第 1 节）。
6. **链接**：根 README 里的所有相对链接，在 monorepo 里都要指向存在的文件，用脚本检查。

## 5. push

- 只 push 到 `https://github.com/RichChen/coding-agent.git`，分支 `main`，tag 一起推（`git push origin main --tags`）。
- 这是对外发布，**第 4 节全部通过，并且审计确认之后才 push**。仓库保持私有，改成公开由用户在 GitHub 网页上自己操作。
- 不 force push。不 push 原来的两个本地仓库。

## 6. 轮次

| 轮 | 内容 | 停在 |
| --- | --- | --- |
| P-1 | 第 2 节的整理（两个原仓库），2.1 private 的清单，第 4 节第 1–3 项在原仓库上的预扫描 | `CHECKPOINT-P1.md`，等审计决定 private 和扫描命中 |
| P-2 | 建 monorepo，写第 3 节的文档，跑第 4 节全部检查 | `CHECKPOINT-P2.md`，等审计确认 |
| P-3 | push | 回复 GitHub 上的提交号和 tag 数 |

CHECKPOINT 文件放在 `D:\crq\src\coding-harness\docs\publish\`。

## 7. 硬约束

- 不改 `docs/sprint/` 下的任何文件，不改 `runs/`，不改任何冻结 tag 指向的提交。
- 不重写两个原仓库的历史（不用 `filter-repo`、不 rebase）。如果密钥扫描在历史里有命中，停下等审计。
- 密钥不能出现在终端输出、日志或 CHECKPOINT 里，命中时只写文件名和行号。
- 不删除任何被 git 跟踪的文件的本地副本，只做 `git rm --cached` 或 `git mv`。
- 小步提交，每条提交信息说明做了什么。
