# 审计：P-2（monorepo）

日期：2026-10-14。审计对象：`docs/publish/CHECKPOINT-P2.md`、附件 `CHECKPOINT-P2-LISTS.md`，以及 `D:\crq\src\coding-agent-mono\` 的 HEAD `f22a261`。

**结论：通过，可以进入 P-3。push 之前先做第 3 节的两件小事。**

## 1. 审计自己核对过的

- monorepo 有 243 个提交、23 个 tag，没有 remote，工作区是干净的。
- 抽查了 3 个冻结 tag，指向和原仓库一致：`harness/a6-retry-freeze` → `0cbc63d`，`agent/a6-retry-freeze-r2` → `6c67739`，`harness/a5-main-freeze` → `02c8671`。
- HEAD 里已经没有这些路径：`/private/`、`overlay.json`、两份面试准备文档、`HANDOFF-BRIEF`、`memory-v2/OPTIONS`、`CLAUDE.md`、`AGENTS.md`、`settings.local.json`。
- HEAD 里还有 74 个名字带 `known-good` 的文件，抽查了 2 个最大的和 1 个最小的，都是 preflight 的镜像审计元数据（文件权限对比、`docker build` 回执、sha），不含 patch 或正确答案。保留。
- `harness/docs/changes/INTERVIEW-FINAL-CLOSEOUT.zh-CN.md` 名字里带 INTERVIEW，但内容是技术收尾记录（`.env` 加载、pytest 收集等），保留。
- 根 README 两份：全文读过。数字和最终报告一致，零结果照实写，没有宣传性的词，也没有本机路径。

审计没有重跑密钥扫描、测试和链接检查，这几项以 CHECKPOINT 为准。

## 2. CHECKPOINT 第 5 节待决项

1. DIAGNOSIS 里那一行的改动：知悉，认可。
2. `docs/memory-v2/papers/` 里的 3 个 arXiv PDF：加进 agent 的 `.gitignore`，不提交。别人的论文 PDF 不适合放进公开仓库。
3. 根 README 的取舍：认可。p 值保留两位小数，和最终报告第 1 节一致。
4. 子 README 只在 monorepo 里改：认可。原仓库的 README 继续服务于原来的两仓库布局。
5. 本文件、`CHECKPOINT-P2.md`、附件：提交到 harness 的 `docs/publish/`，见第 3 节。
6. P-3 按第 4 节执行。

`docs/publish/` 下的文件里写了"读者是面试官"、求职相关的背景，还有 resume-review 目录被删的记录。用户在 P-2 中已经选择原样提交，这些会随仓库一起公开。用户如果改主意，可以在改成公开之前，从 HEAD 里移出 `docs/publish/`（历史里仍然会留着）。

## 3. push 之前要做的

1. 在原仓库提交：
   - agent：`.gitignore` 加上 `docs/memory-v2/papers/`；
   - harness：提交 `docs/publish/CHECKPOINT-P2.md`、`CHECKPOINT-P2-LISTS.md`、本文件。
2. 在 monorepo 里分别执行 `git subtree pull --prefix=harness <harness 原仓库> main` 和 `git subtree pull --prefix=agent <agent 原仓库> main`，不用 `--squash`，把上面两个提交同步进来。同步后核对：`HEAD:harness` 和 `HEAD:agent` 的树，除了第 2 节第 4 条说的子 README 头部和链接以外，要和两个原仓库的 HEAD 完全相同。合并时如果在子 README 上冲突，保留 monorepo 版本。临时加的 remote 用完删掉。

## 4. P-3 的要求

- `git remote add origin https://github.com/RichChen/coding-agent.git`，然后 `git push -u origin main`，再执行 `git push origin --tags`。
- 如果远端已经有提交，被拒绝了（比如建仓库时勾选了生成 README），**不要 force push，也不要 pull 合并**，停下来报告。
- 认证失败时停下来，说明需要用户在浏览器里完成登录，不要把 token 写进命令或配置文件。
- push 完成后核对：
  - `git ls-remote origin` 里 `main` 的提交号要等于本地 HEAD，tag 数为 23；
  - 在浏览器里打开仓库页面，根 README 能正常显示；
  - 抽查 2 个相对链接（最终报告、项目历程），能打开。
- 仓库保持私有。改成公开由用户自己在 GitHub 网页上操作。
