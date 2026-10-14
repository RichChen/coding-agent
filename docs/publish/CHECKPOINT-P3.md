# CHECKPOINT-P3：push 到 GitHub

日期：2026-10-15。执行方：本地 Cursor agent。依据：`docs/publish/AUDIT-P2.zh-CN.md` 第 3、4 节，合同第 5 节。

**结论：monorepo 的 `main` 和 23 个 tag 已推到 `https://github.com/RichChen/coding-agent.git`。远端 `main` 是 `6b4e93ef0246a4808195074b748d8f2feede5abf`，等于本地 HEAD；23 个 tag 的提交号和本地逐一相同。没有 force push，没有 pull 合并，没有把 token 写进命令或配置。仓库保持私有。浏览器里的 README 显示和链接抽查待用户核对（见第 3 节）。**

## 1. push 之前（审计第 3 节）

| 仓库 | 提交 | 内容 |
| --- | --- | --- |
| agent | `0b4ea4b` | `.gitignore` 加 `docs/memory-v2/papers/`，3 个 arXiv PDF 不提交 |
| harness | `a20f91c` | 提交 `docs/publish/` 下的 `CHECKPOINT-P2.md`、`CHECKPOINT-P2-LISTS.md`、`AUDIT-P2.zh-CN.md`，以及 `PUBLISH-START-PROMPTS.zh-CN.md` 的改动（加了 P-3 的 prompt） |

两份新文件提交前扫过：没有密钥；只有 `D:\crq` 这类本机路径（`AUDIT-P2` 第 3 行，prompt 文件 7 处），不阻断。

同步进 monorepo：

- `git subtree pull --prefix=harness D:/crq/src/coding-harness main`，得到 `f1cce10`；
- `git subtree pull --prefix=agent D:/crq/src/coding-agent main`，得到 `6b4e93e`。

都没有用 `--squash`，也没有冲突。直接用的本地路径，没有加临时 remote。拉取时没有带进不带前缀的 tag，tag 仍是 23 个。

同步后核对（`git diff --name-only <原仓库 HEAD>^{tree} HEAD:<前缀>`）：

- `HEAD:harness` 和 harness `a20f91c` 只差 `README.md`、`README.zh-CN.md`。两份文件各有 3 行头部和 2 个 `../agent/` 链接，改动共 8 行加、2 行减。
- `HEAD:agent` 和 agent `0b4ea4b` 只差 `README.md`，是 3 行头部。
- 其余文件完全相同。

monorepo 现在有 247 个提交（P-2 时 243 个，加上 2 个原仓库提交和 2 个合并提交）。

## 2. push（审计第 4 节）

### 2.1 网络

第一次 `git ls-remote` 失败：`RPC failed; curl 28 Recv failure: Connection was reset`。直连 github.com:443 也不通。系统开着代理 `127.0.0.1:7890`，但 git 没有配置代理。

之后每条联网命令都用单次参数 `git -c http.proxy=http://127.0.0.1:7890 ...`，没有写进任何 git 配置。认证用的是系统里已有的 Git Credential Manager（`credential.helper=manager`），没有弹窗，没有用到 token。

### 2.2 步骤

1. `git ls-remote https://github.com/RichChen/coding-agent.git`：退出码 0，没有任何 ref，远端是空仓库，认证正常。
2. `git remote add origin https://github.com/RichChen/coding-agent.git`。
3. `git push -u origin main`：`* [new branch] main -> main`。
4. `git push origin --tags`：23 个 `[new tag]`，`agent/` 9 个，`harness/` 14 个。

### 2.3 核对

| 项 | 结果 |
| --- | --- |
| `git ls-remote origin` 里的 `refs/heads/main` | `6b4e93ef0246a4808195074b748d8f2feede5abf`，等于本地 `git rev-parse HEAD` |
| 远端 tag 数 | 23 |
| 远端 tag 和本地对比 | 23 个逐一比较提交号，0 个不一致 |
| `remote.origin.url` | `https://github.com/RichChen/coding-agent.git`，没有内嵌凭据 |
| `http.proxy` | 没有写进配置 |

## 3. 浏览器核对：待用户完成

在 Cursor 内置浏览器里打开 `https://github.com/RichChen/coding-agent`，显示的是 GitHub 404 页。原因是这个浏览器没有登录 GitHub，而仓库是私有的。未登录时访问返回 404，也说明仓库目前不是公开的。

需要登录才能继续。这一步我问过用户，用户选择跳过，自己在网页上核对。所以下面三项**还没有做**：

- 根 README 能正常显示；
- 链接“Final report on both memory experiments”能打开（`agent/docs/MEMORY-FINAL-REPORT.zh-CN.md`）；
- 链接“Project history”能打开（`harness/docs/PROJECT-HISTORY.zh-CN.md`）。

已经用 git 做过的替代核对：`git ls-tree origin/main` 里有 `README.md`、`README.zh-CN.md` 和这两个链接的目标文件。P-2 的链接脚本也确认过，根 README 的 24 个相对链接在这个树里都指向存在的文件。

## 4. 当前状态

- 远端：`main` = `6b4e93e`，23 个 tag，私有。改成公开由用户在 GitHub 网页上自己操作。
- monorepo：`origin` 已设置，`main` 跟踪 `origin/main`，工作区干净。
- 原仓库：harness HEAD 是本文件的提交（在 `a20f91c` 之后），agent HEAD 是 `0b4ea4b`。**本文件的提交没有同步进 monorepo，也没有推到远端。** 如果想让远端也包含它，需要再做一次 `git subtree pull --prefix=harness` 和 `git push origin main`。普通 push 就够，不需要 force。
- 审计第 2 节提醒过：`docs/publish/` 里有求职相关的背景，已经随 `main` 推上去了。用户如果改主意，可以在改成公开之前从 HEAD 移出这个目录，但历史里仍然会留着。
