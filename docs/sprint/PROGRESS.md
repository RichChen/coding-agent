# 记忆重建进度

## 第 0 步：版本控制（2026-09-24）

- `.git` 是 2026-07-02 留下的空目录，`git status` 报 not a git repository，没有可恢复历史。已改名为 `.git.broken-20260924`，并重新 `git init`。
- `.gitignore`：去掉全局 `*.jsonl`，改为忽略 `traces/`、`reports/`、`.tmp/`、`.pytest-run-final/` 下的 jsonl；`benchmarks/`、`configs/`、`docs/` 里小于 1MB 的数据文件可以跟踪。根目录 `/*.pdf` 直接忽略。补上 `.tmp/`、`.pytest-run-final/`。另外忽略 `reports/**/workspaces/` 和 `reports/**/graph_workspaces/`，与已有的 `traces/workspaces/` 一致，避免把实验沙箱副本提交进去。文件仍留在磁盘上。
- 测试：`python -m pytest -q`，269 passed，1 skipped，0 failed（169s）。
- 下一步：第 1 步，写 `docs/sprint/MEMORY-INVENTORY.md`。

## 第 1 步：如实盘点（2026-09-24）

- 新增 `docs/sprint/MEMORY-INVENTORY.md`。运行时入口是 `public_runtime_view.py`（11 条快照，不走 `MemoryRecord`）和 `harness_h4.py`（走 `gate`/`validity`，但不读这 11 条）。`records.py`、`builder.py`、`gate.py`、`validity.py`、`record_store.py`、`dependency_index.py` 停在离线 demo 和单测。
- 11 条源记忆的仓库、短版本、源目录和轨迹字段已列入盘点。轨迹没有 `run_command` 参数，`failure_notes` 全空。
- 这一步只加文档，没有相关测试可跑。
- 下一步：第 2 步，读 harness 的 `memory-source-verification.json`；没有就先标 `unverified`。

## 第 2 步：接入源题验证结果（2026-09-24）

- `D:\crq\src\coding-harness\docs\sprint\memory-source-verification.json` 还不存在。11 条先全部按 `unverified` 处理，文件出现后同一函数会补上映射。
- 新增 `reposkill_agent/memory/source_verification.py`：`pass`→`validated_fix`，`partial`→`partial_attempt`，`fail`→`failed_attempt`，其余（含 `grader_unavailable`、缺文件、未知 source）→`unverified`。
- 测试：`python -m pytest -q tests/test_source_verification.py`，3 passed。
- 下一步：第 3 步，用规则从 11 条轨迹和 `candidate-delta.json` 提炼记忆卡，不调模型。
