# scripts/audit

这里的 20 个 `.py` 是审计侧写的一次性脚本，原件在本地的 `.tmp/` 根目录（不进 git），这里是逐字节相同的副本。它们不维护，不保证在当前代码上还能运行。

- `case_mem.py` 就是 `docs/sprint/A5-CASE-DATA.md`、`docs/sprint/CHECKPOINT-7.md` 里引用的 `.tmp/case_mem.py`（`table` / `follow` / `task` 三个子命令）。复跑时把它复制回 `.tmp/`，或者直接从这里运行。它需要把 coding-agent 仓库加进 `sys.path`，用本仓库的 `.venv`。
- 脚本里写死了本机绝对路径（`D:\crq\src\...`，`extract_codex.py` 和 `user_msgs.py` 还有本机用户目录），按原两仓库布局检出才能运行。
- `audit_b0_deltas.py`、`audit_v6.py` 会读取本地的 `runs/sprint5-main-private/`，只在内存里比对，不输出私有内容；这个目录不在 git 里。
- `extract_codex.py`、`user_msgs.py` 读本机的 AI 对话记录，生成的 transcript 留在本地，不进 git。
