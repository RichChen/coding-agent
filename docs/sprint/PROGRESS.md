# 记忆重建进度

## 第 0 步：版本控制（2026-09-24）

- `.git` 是 2026-07-02 留下的空目录，`git status` 报 not a git repository，没有可恢复历史。已改名为 `.git.broken-20260924`，并重新 `git init`。
- `.gitignore`：去掉全局 `*.jsonl`，改为忽略 `traces/`、`reports/`、`.tmp/`、`.pytest-run-final/` 下的 jsonl；`benchmarks/`、`configs/`、`docs/` 里小于 1MB 的数据文件可以跟踪。根目录 `/*.pdf` 直接忽略。补上 `.tmp/`、`.pytest-run-final/`。另外忽略 `reports/**/workspaces/` 和 `reports/**/graph_workspaces/`，与已有的 `traces/workspaces/` 一致，避免把实验沙箱副本提交进去。文件仍留在磁盘上。
- 测试：`python -m pytest -q`，269 passed，1 skipped，0 failed（169s）。
- 下一步：第 1 步，写 `docs/sprint/MEMORY-INVENTORY.md`。
