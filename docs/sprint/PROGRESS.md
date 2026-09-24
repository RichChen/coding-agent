# 能力冲刺进度

## 第 0 步：版本控制和清理

日期：2026-09-24。花费：0 CNY。

- `.gitignore` 忽略 `.tmp-*/`、`.a5-test-basetemp/`、`.pytest-tmp/`、`runs/`、`traces/`，以及 evidence 里的 `staging/`、`workspace/`、`original/`、`known-good/`、`baseline/`、`build/`、`full-repo/`、`private*` 和大于等于 200KB 的 json。磁盘上的文件没有删除。`git check-ignore` 抽查：临时目录、`runs/`、`staging/`、`build/` 下的副本被忽略；小的 `*.md` / `*.json` 仍可跟踪。
- 测试基线：`python -m pytest -q` → **433 passed, 22 skipped, 0 failed**（62.87s）。失败项无，跳过的 22 个留到后续按需看。
- 9 月以来的改动已按模块提交（模型网关、工具与执行、会话恢复、上下文、agent loop、评测、A5 脚本、文档）。提交前抽查：配置里的 api key 是环境变量占位，没有大于 5MB 的暂存文件。误进索引的整仓副本和 `private*` 已用 `git rm --cached` 移出跟踪。
- `AGENTS.md` / `CLAUDE.md` 的参考路径改为 `D:\crq\src\learn-claude-code-main`。
- tag：`pre-capability-sprint`（打在本步收尾提交上）。

下一步：第 1 步，通用单题运行器和 dev 集。

## 第 1 步：通用单题运行器和 dev 集

日期：2026-09-24。花费：0 CNY（mock，没有真实模型调用）。

- 新增 `scripts/run_swe_task.py`。一条命令可以在 dev 清单里的任意题上跑 B0：`python scripts/run_swe_task.py --task <id> --profile configs/sprint/b0.yaml`。预算只走 CNY ledger，单次上限 1 CNY；没有再设 `max_cost_usd`。
- dev 集 9 题写在 `configs/sprint/dev-tasks.yaml`：pytest 5103/5221/5227，sympy 11400/11870/12171，scikit-learn 10297/10949/11281。20 个 pilot 目标已排除。Django 三道记忆源树超过 grader 的 2048 文件上限，没有放进 dev 集。
- `RepositoryGrader.execute` 增加 `selectors`，按 FAIL_TO_PASS + PASS_TO_PASS 的 nodeid 跑测试，测试补丁仍只在 grader 侧 overlay。
- mock 端到端（`pytest-dev__pytest-5103`，Docker grader）：未改代码，`solved=false`，grader `partial`，F2P 0/1，P2P 20/64，模型调用 1，费用 0。产物在 `runs/step1-mock3/`（已忽略）。
- 11 条记忆源历史 delta 的打分在 `docs/sprint/memory-source-verification.json`。只有 `pytest-dev__pytest-5103` 得到 `partial`（F2P 0/1，P2P 20/64）。Django 3 条因文件数上限、sympy/sklearn 6 条因 8MB 传输上限，记为 `grader_unavailable`。`pytest-dev__pytest-5221` 的 grader 没有给出 pass/partial/fail。

下一步：第 2 步，改 read_file、搜索和 masking，再在 dev 集上跑 B0。
