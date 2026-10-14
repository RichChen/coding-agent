# evidence 目录说明

本目录存放各轮实验的证据：报告、收据、清单和小于 200KB 的 JSON。规则见仓库根目录 `.gitignore` 中 `docs/upgrade/evidence/**` 一段。

## 评测侧的 private 材料

评测侧的 private 材料只放在本地，最新提交里不跟踪。这类材料包括 `private/`、`private-spec*.json`、整仓 known-good 快照和隐藏测试 overlay。`.gitignore` 里的 `docs/upgrade/evidence/**/private*` 规则就是为此写的。

这条规则加得比部分文件晚，所以历史提交里还能看到一部分 private 文件：

- `7bb4395` 里有 7 个 `private-spec*.json`，下一个提交 `b5cb425` 就把它们移出了；
- 35 个 `private/` 下的文件，在发布整理时用 `git rm --cached` 移出了最新提交，本地副本保留。它们来自 `H5-interop/*/handoff/private/`（16 个）、`R2-real/pilot-01/private/` 和 `R2-real/wrapper-01/private/`（15 个）、`full-repo-grader/attempt-0{1,2}/private/`（4 个）。

被跟踪的 manifest 和 experiment 文件仍然记录了这些文件的 sha256，例如 `H5-interop/*/handoff/manifest.json`、`R2-real/*/experiment.json`、`R2-real/wrapper-01/pilot-01-hashes.json`。有本地副本时，可以用这些 sha256 核对。
