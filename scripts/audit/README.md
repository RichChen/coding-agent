# scripts/audit

`case_mem.py` 是审计侧写的一次性脚本，`docs/sprint/A5-CASE-DATA.md`、`docs/sprint/CHECKPOINT-7.md` 里引用的 `.tmp/case_mem.py` 就是它（`table` / `follow` / `task` 三个子命令）。复跑时把它复制回 `.tmp/`，或者直接从这里运行。

- 它不维护，不保证在当前代码上还能运行。
- 它需要把 coding-agent 仓库加进 `sys.path`，用本仓库的 `.venv`，并按原两仓库布局检出。
- 审计时写的其他一次性脚本只留在本地，不发布。
