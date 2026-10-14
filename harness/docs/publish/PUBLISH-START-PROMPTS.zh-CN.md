# 发布 GitHub 的 Cursor 启动 prompt

只开一个 Cursor agent，它要同时动两个仓库。每一轮做完就停，等审计。

## P-1（先发这一段）

请执行 `D:\crq\src\coding-harness\docs\PUBLISH-CONTRACT.zh-CN.md` 第 6 节的 P-1，并遵守第 1、2、4、7 节。

开工前把合同完整读一遍，再读两个仓库的 `README.md` 和 `.gitignore`。本轮只在两个原仓库里工作：`D:\crq\src\coding-harness` 和 `D:\crq\src\coding-agent`。

- 不建 monorepo，不 push，不调用任何模型或付费 API。
- 按第 2 节整理，各自小步提交。被 git 跟踪的文件只能用 `git rm --cached` 或 `git mv` 处理，本地副本不删。
- 本地删除之前，先把要删的目录和每个目录的大小写进 CHECKPOINT。`runs/`、`traces/`、`.venv/`、`.env`、`.swebench_envs/`、`baseline/` 一律不碰。
- 2.1 节的 36 个 private/gold 路径：只列路径，每个文件只写前 3 行的摘要，不要贴 gold patch 或 test patch 的内容。列完停下，等审计决定。
- 第 4 节第 1–3 项先在两个原仓库的全部历史上预扫描。命中密钥时只写文件名、提交号和行号，不要打印密钥本身。
- 不改 `docs/sprint/`、`runs/` 和任何冻结 tag。

做完写 `D:\crq\src\coding-harness\docs\publish\CHECKPOINT-P1.md`，内容包括：
- 各步的提交号；
- 移除和移动了哪些文件；
- 本地删除的清单；
- private 清单；
- 三项预扫描的结果；
- 历史中出现过、但已从最新提交里移除的敏感路径。

写完停下。

## P-2（P-1 审计后发）

P-1 的审计意见在 `D:\crq\src\coding-harness\docs\publish\AUDIT-P1.zh-CN.md`，开工前完整读一遍。用户已经确认，仓库以后会**带完整历史公开**，所以不要改写历史。

分两部分做：

**A. 先在两个原仓库里，按审计第 1–5 节处理，小步提交：**
1. 36 个 private 路径执行 `git rm --cached`；写 `docs/upgrade/evidence/README.md` 的说明；列出还链接到这些文件的文档。
2. `.tmp/` 根目录的 20 个 `.py` 复制到 `scripts/audit/`，提交前先扫描，再写 `scripts/audit/README.md`。
3. 两份面试准备文档执行 `git rm --cached`，加进 `.gitignore`，删掉指向它们的链接。agent 的 `SESSION-HANDOFF` 移到 `docs/archive/`。
4. agent 侧新建 `docs/memory-v2/DIAGNOSIS-AND-LITERATURE.zh-CN.md`，内容是 OPTIONS 第 1、2、7 节的原文；把 `MEMORY-FINAL-REPORT` 里的两处引用改成指向它；在 `.gitignore` 里忽略 HANDOFF-BRIEF 和 OPTIONS。
5. agent `README.md` 里的本机解释器路径改成通用写法。
6. 把合同和 prompt 文件移到 `docs/publish/`，然后提交 `docs/publish/` 下的所有文件。

**B. 再执行合同第 6 节的 P-2：**
- 在 `D:\crq\src\coding-agent-mono\` 建 monorepo：两边的历史和 tag 都保留，tag 加前缀 `harness/`、`agent/`。
- 写合同第 3 节的文档。
- 跑合同第 4 节的全部检查。第 4 节第 2 项里，历史中的私有材料按审计第 0 节放行，只列出来，不阻断。

约束：
- 不改 `docs/sprint/`、`runs/`，不动任何冻结 tag。
- 删除或移动之前，如果碰到名字像个人文件的路径（resume、简历、cv 之类），先停下来问。
- 不要提权处理 ACL 目录。
- 不 push。

做完写 `docs/publish/CHECKPOINT-P2.md`，然后停下。CHECKPOINT 里要写清：A 部分每一步的提交号；monorepo 的提交数、tag 数和 `.git` 大小；第 4 节每一项检查的结果；根 README 全文。

## P-3（P-2 审计后发）

`P-2 审计通过。请在 D:\crq\src\coding-agent-mono\ 里添加远端 https://github.com/RichChen/coding-agent.git，执行 git push origin main --tags。不 force push。推完回复：GitHub 上 main 的最新提交号、推上去的 tag 数，以及仓库页面能否正常显示根 README。`
