# 审计：P-1（发布前整理）

日期：2026-10-14。审计对象：`docs/publish/CHECKPOINT-P1.md` 和它的附件，以及 harness `fc29b0f..e28ee35`、agent `fbe92b8..ed58384` 这几个提交。

**结论：通过，可以进入 P-2。下面是需要一并处理的决定。**

## 0. 用户已确认的总方针

仓库将来会**带完整历史公开**，用作简历链接。也就是说，历史里出现过的东西（本机路径、AI 工具指令文件、`7bb4395` 里的 7 个 private-spec、4 个 SWE-bench 候选 jsonl）都会被人看到。这一点用户已经接受，理由如下：

- 扫描结果是密钥 0 命中，`.env` 从来没被跟踪过；
- SWE-bench 的 FAIL_TO_PASS 本来就是公开数据；
- private-spec 对应的是合成任务，或者自建的 Flask 验证任务，不是 A5、A6 用的题；
- 冻结 tag 和 commit 号是这个项目可信度的主要来源，改写历史会让它们全部失效。

所以：**不改写历史，不另建快照仓库。** 下面的处理只决定最新提交（HEAD）里留下什么，目的是让面试官浏览时看到的内容干净、一致。

## 1. 36 个 private 路径：全部从 HEAD 移出（`git rm --cached`，本地保留）

理由：harness 自己的 `.gitignore` 早就写了 `docs/upgrade/evidence/**/private*`，这 36 个文件是在规则加进去之前被跟踪的，属于遗留问题。这个项目的卖点是答案隔离，如果仓库首页一点进去就有 `private/known-good.json`（整仓正确答案）和 `overlay.json`（隐藏测试），会让人起疑。移出以后，项目和自己定的规则一致。这些文件仍然在历史里，也在本地，证据没有丢。

- 4.1 的 16 个、4.2 的 15 个、4.3 的 4 个，一起移出。
- 4.4 的 `scripts/sprint2_debug_gold.py` **保留**。它是代码，不含 patch 内容。
- 在 `docs/upgrade/evidence/README.md`（不存在就新建）里加一段说明：评测侧的 private 材料只放在本地，HEAD 里不跟踪；历史提交里还能看到一部分，原因是规则加得晚。
- 列出所有还在 HEAD 里、链接指向这 36 个文件的文档，只列不改。

## 2. `.tmp/`：审计脚本进 git，其余留在本地

`.tmp/` 里 668 MB 的 `swebench_build/` 和 177 MB 的 `swebench_oracle_py39/` 是可以重建的环境，`scripts/build_swebench_lite_subset.py` 和 `setup_swebench_envs.py` 把它们当作默认路径。它们已经被 ignore，留在本地，不动。

`.tmp/` 根目录下有 20 个 `.py`，是审计时写的一次性脚本。`case_mem.py` 被 `A5-CASE-DATA.md` 引为核对脚本，丢了就没法复跑。处理方式：

- 把这 20 个 `.py` **复制**（不是移动）到 `scripts/audit/`，提交。原文件留在 `.tmp/`，因为冻结的文档写的是 `.tmp/case_mem.py`，不能改。
- 新建 `scripts/audit/README.md`，内容是：这些是审计侧的一次性脚本，不维护；`case_mem.py` 就是 `docs/sprint/A5-CASE-DATA.md` 里引用的 `.tmp/case_mem.py`，复跑时把它复制回 `.tmp/`，或者直接从这里运行。
- 提交前对这 20 个文件做一次第 4 节第 1–3 项的扫描。有私有内容或密钥就不提交那一个，写进 CHECKPOINT。
- `.tmp/` 里的 transcript、日志、`a6-dry/` 留在本地，**不进 git**。transcript 是对话原文。

`.tmp-canary-pytest-7220/` 和 `.tmp-a5-canary-real-20260924-v7/` 被已跟踪的脚本当作输入，留在本地，不动。

## 3. 面试准备文档：从 HEAD 移出

harness 的 `docs/AGENT-INTERVIEW-GUIDE.zh-CN.md` 和 `docs/INTERVIEW-DEMO.zh-CN.md` 是用户自己准备面试用的材料。面试官点简历链接进来看到这些不合适。用 `git rm --cached` 移出 HEAD，本地保留，加进 `.gitignore`。

指向它们的链接，在 `README*`、`docs/LEARNING.zh-CN.md`、`docs/PROJECT-OVERVIEW.zh-CN.md` 里删掉，或者改成纯文本。

`CONTAMINATION-NOTES`、`FAILURE-CASES`、`PROJECT-HISTORY` 留在 `docs/` 顶层，它们是技术内容。

agent 的 `docs/SESSION-HANDOFF.zh-CN.md` 移到 `docs/archive/`。

## 4. agent 的 `docs/memory-v2/`：只把研究内容放进 git

这个目录一直没有被跟踪。`HANDOFF-BRIEF.zh-CN.md` 写的是用户的求职背景和本机路径，`OPTIONS.zh-CN.md` 里有"对面试故事的影响""加分岗位"这类段落，两份都不适合公开。但 `MEMORY-FINAL-REPORT.zh-CN.md` 第 2、4 节引用了 OPTIONS 的第 1、2 节（A5 诊断和文献数字）。处理方式：

- 新建 `docs/memory-v2/DIAGNOSIS-AND-LITERATURE.zh-CN.md`，把 OPTIONS 的第 1 节（诊断）、第 2 节（文献表）、第 7 节（读过的文件、查过的文献、没有核实的说法）**原样**复制进去。文件开头加一行"摘自 2026-10-13 的方案调研，原文件未公开"，其余文字不改。
- `MEMORY-FINAL-REPORT.zh-CN.md` 里两处 `memory-v2/OPTIONS.zh-CN.md` 改成指向新文件，节号随之更新。这份报告不是冻结文件，可以改。
- `HANDOFF-BRIEF.zh-CN.md` 和 `OPTIONS.zh-CN.md` 不进 git，在 `.gitignore` 里加这两个文件名。

## 5. CHECKPOINT 里的其他事项

- 2.4 节两处超出合同字面的处理（`.claude/settings.local.json`、`PROJECT-PLAN-OpenHands-RepoSkillAgent`）：**都认可**。
- 删不掉的 ACL 目录：里面已经没有可读文件，又被 ignore 了，不影响 GitHub。Cursor agent **不要**提权处理。用户想删的话，自己用管理员 PowerShell 来做。
- `tmp/pdfs/resume-review/` 已经被删，这个删除没法恢复（用的是 `shutil.rmtree`，不经过回收站）。审计会把这件事告诉用户。以后的删除脚本，碰到名字像个人文件的目录（resume、简历、cv、id 之类）要先停下来问。
- agent `README.md` 第 20 行的 `C:\Users\Administrator\.conda\...` 路径，在 P-2 里改成通用写法，比如 `python`。
- `CHECKPOINT-P1.md`、附件、`PUBLISH-CONTRACT.zh-CN.md`、`PUBLISH-START-PROMPTS.zh-CN.md`、本审计文件，都提交到 harness 的 `docs/publish/`。合同和 prompt 两个文件从 `docs/` 移过去。

## 6. 合同第 5 节的修订

第 5 节原来写"仓库保持私有"。现在改为：P-3 先推到私有仓库，用户在 GitHub 上检查没问题以后，自己在网页上改成公开。改成公开不是 agent 的事。
