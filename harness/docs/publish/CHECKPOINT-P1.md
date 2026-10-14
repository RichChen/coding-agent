# CHECKPOINT-P1：两个原仓库的发布前整理

日期：2026-10-14。执行方：本地 Cursor agent。依据：`docs/PUBLISH-CONTRACT.zh-CN.md` 第 6 节 P-1，遵守第 1、2、4、7 节。

本轮只在 `D:\crq\src\coding-harness` 和 `D:\crq\src\coding-agent` 两个原仓库里工作。没有建 monorepo，没有 push，没有调用任何模型或付费 API。没有改 `docs/sprint/`、`runs/`，也没有动任何 tag（见第 1 节）。没有重写历史。

## 0. 结论和等审计决定的事项

- 密钥扫描（两个仓库的全部历史）：**0 命中**。`.env` 在两边历史里从来没被跟踪过。
- 第 2.1 节的 36 个 private/gold 路径已列在第 4 节，**未移除，等审计决定**。
- 等审计决定的另外三件事：
  1. harness 的 `.tmp/`、`.tmp-canary-pytest-7220/`、`.tmp-a5-canary-real-20260924-v7/` 本轮**没有删**。原因见第 3.2 节：`docs/sprint/` 里的证据文档和被跟踪的脚本把它们当作输入。
  2. harness 有 20 个临时目录本身是“拒绝访问”（ACL 问题），另外 `tmp/` 下有 37 个、agent `.tmp/` 下有 3 个子目录也是这样。删除结果见第 3.3 节。我没有用 `takeown`/`icacls` 去改权限。
  3. 有两处超出合同字面的处理（第 2.4 节），请确认或回退。

## 1. 提交号

开工前 HEAD：harness `cde2ec2c40da3ecab457253dde37c52312b0ed61`，agent `b19cbc6c0387c6fb34c30ba515c81e6d296e4e54`。

| 仓库 | 提交 | 内容 |
| --- | --- | --- |
| harness | `fc29b0f5bf9fa6d5246726f8ba504d4536990840` | 2.1：`git rm --cached` 根目录 `tmp_requests_*.jsonl`、`swebench_candidates*.jsonl`，并加进 `.gitignore` |
| harness | `cbe1e466407dc5f039280d503eec2c7065eb01bc` | 2.1：`git rm --cached` `CLAUDE.md`、`AGENTS.md`、`CLAUDE-CODE-IMPROVEMENTS.md`、`CLAUDE-CODE-RESUME-POLISH.md`、`.claude/settings.local.json`，并加进 `.gitignore` |
| harness | `b1feab9bbf65606a760600907fb5839c2793fb0b` | 2.2：`git mv` 两份文档进 `docs/`、14 份过程文档进 `docs/archive/`，同时修正指向这些文件的相对链接 |
| harness | `e28ee354afae52653f72f40c8250a8d7ed91addf` | 2.4：`.gitignore` 补充 |
| agent | `fbe92b8f57161bc26cb576700370095f4795b90c` | 2.1：`git mv` 根目录 6 份计划/运行手册/简介进 `docs/archive/`，README 里两处路径同步 |
| agent | `ed58384a2b5c3e6cec643de67567ee4b555899e5` | 2.4：`.gitignore` 补充（`.ruff_cache/` 原来已有） |

本文件和附件 `CHECKPOINT-P1-LOCAL-INFO.md` 没有提交，和 `docs/PUBLISH-CONTRACT.zh-CN.md`、`docs/PUBLISH-START-PROMPTS.zh-CN.md` 一样留在工作区，由审计决定是否提交。agent 工作区里原有的未跟踪目录 `docs/memory-v2/` 不是本轮产生的，没有碰。

tag 核对（全部是轻量 tag；本轮没有执行任何 tag 命令，新提交也不会移动它们，下面是提交后的指向）：harness `a5-main-freeze 02c8671`、`a5-main-freeze-r1..r4`（`fb26dbd`、`2f28232`、`1707d23`、`074219c`）、`a5-main-closeout 2780b89`、`a6-retry-freeze 0cbc63d` 等 14 个；agent `a5-main-freeze a22e4ca`、`a6-retry-freeze e9aeddd`、`-r1 01db102`、`-r2 6c67739` 等 9 个。

## 2. 移出 git 和移动的文件

本地副本全部保留，开工后用 `Test-Path` 逐个确认过。

### 2.1 harness：`git rm --cached`

| 路径 | 提交 |
| --- | --- |
| `tmp_requests_2674.jsonl`、`tmp_requests_863.jsonl` | `fc29b0f` |
| `swebench_candidates.jsonl`、`swebench_candidates_short.jsonl` | `fc29b0f` |
| `CLAUDE.md`、`AGENTS.md` | `cbe1e46` |
| `CLAUDE-CODE-IMPROVEMENTS.md`、`CLAUDE-CODE-RESUME-POLISH.md` | `cbe1e46` |
| `.claude/settings.local.json` | `cbe1e46`（合同清单外，见 2.4） |

`.gitignore` 新增 `/tmp_requests_*.jsonl`、`/swebench_candidates*.jsonl`、`/CLAUDE.md`、`/AGENTS.md`、`/CLAUDE-CODE-*.md`，避免它们在工作区里一直显示为未跟踪。`scripts/build_swebench_lite_subset.py` 会写 `swebench_candidates*.jsonl`，`reports/examples/tmp_requests_*_log.json` 引用了 tmp_requests 的文件名。这两处只是文本引用，不影响运行。

### 2.2 harness：`git mv`

- `LEARNING.zh-CN.md` → `docs/LEARNING.zh-CN.md`
- `PROJECT-OVERVIEW.zh-CN.md` → `docs/PROJECT-OVERVIEW.zh-CN.md`
- `docs/` → `docs/archive/`：`SOLID-ROADMAP`、`SOLID-A-BATCH-EXECUTION`、`SOLID-B-BATCH-EXECUTION`、`SOLID-C-BATCH-EXECUTION`、`SOLID-D1-CONTAMINATION-EXECUTION`、`SOLID-D1-POLISH-EXECUTION`、`SOLID-D1-REWORK-EXECUTION`、`SOLID-D1-SCAFFOLD-EXECUTION`、`SOLID-D1-SWEBENCH-EXECUTION`、`SOLID-D2-CLOSEOUT-EXECUTION`、`SOLID-D2-DEMO-EXECUTION`、`SOLID-D2-REMAINING-EXECUTION`、`IMPROVEMENT-PLAN`、`DEMO-SCRIPT`（均为 `.zh-CN.md`，共 14 个）

合同写的是“`SOLID-*`、`IMPROVEMENT-PLAN`、`DEMO-SCRIPT` 等”。我只移了点名的这三类。`docs/` 顶层还剩 `AGENT-INTERVIEW-GUIDE`、`INTERVIEW-DEMO`、`CONTAMINATION-NOTES`、`FAILURE-CASES`、`PROJECT-HISTORY`，是否也算过程文档请审计决定。`docs/changes/` 下的 `SOLID-*-CLOSEOUT` 没有动。

同一提交里改了 6 个文件中指向被移动文件的相对链接，只改链接路径，正文不变：`README.md`（1 处）、`README.zh-CN.md`（3 处）、`docs/LEARNING.zh-CN.md`（2 处）、`docs/PROJECT-OVERVIEW.zh-CN.md`（5 处）、`docs/AGENT-INTERVIEW-GUIDE.zh-CN.md`（2 处）、`docs/changes/INTERVIEW-FINAL-CLOSEOUT.zh-CN.md`（1 处）。

用脚本检查了所有被跟踪的 `.md` 里的相对链接：移动前后对比，没有新增断链；唯一的例外是 `docs/PROJECT-OVERVIEW.zh-CN.md` 里两条指向 `../CLAUDE-CODE-*.md` 的链接，因为这两个文件已经移出 git，在 git 里必然是断的。归档文件里的正文链接（例如 `docs/archive/SOLID-ROADMAP` 指向 `IMPROVEMENT-PLAN` 的文字）没有改。

### 2.3 agent：`git mv` → `docs/archive/`

- `LLM-DEEPSEEK-INTEGRATION-PLAN.zh-CN.md`
- `PHASE6-EVAL-STRENGTHENING-PLAN.zh-CN.md`
- `PHASE7_1-POSITIVE-GAIN-HARDENING-PLAN.zh-CN.md`
- `REAL-LLM-DEEPSEEK-EVAL-RUNBOOK.zh-CN.md`
- `NEW-PROJECT-BRIEF.zh-CN.md`
- `PROJECT-PLAN-OpenHands-RepoSkillAgent.zh-CN.md`（合同清单外，见 2.4）

`README.md` 末尾“参考”一节的两处反引号路径同步改成了 `docs/archive/...`。没有 markdown 链接因此断掉（移动前后断链集合相同）。`docs/codebase-structure-detailed.zh-CN.md`、`docs/project-chronology.zh-CN.md`、`docs/SESSION-HANDOFF.zh-CN.md`、`reports/phase6-eval-summary.md` 里还有这些文件名的纯文本提及，没有改。现在 agent 根目录只剩 `.gitignore`、`README.md`、`pyproject.toml`。

### 2.4 超出合同字面、请审计确认的两处

1. harness `.claude/settings.local.json`（8 行）是唯一一个被跟踪的 AI 工具目录文件。合同 2.1 没点名，但 2.4 要求忽略 `.claude/`，它的性质也和 `CLAUDE.md` 一样，所以一起做了 `git rm --cached`。如果要回退：`git add -f .claude/settings.local.json`。
2. agent `PROJECT-PLAN-OpenHands-RepoSkillAgent.zh-CN.md` 不匹配 `*-PLAN.zh-CN.md` 这个通配符（`PLAN` 在中间），但它是总计划文档；如果留着，就违背了“根目录只留入口文件”。所以一起移进了 `docs/archive/`。如果要回退：`git mv docs/archive/PROJECT-PLAN-OpenHands-RepoSkillAgent.zh-CN.md .`。

### 2.5 `.gitignore` 补充（2.4 节）

两边都加了 `.tmp*/`、`.pytest*/`、`*.broken-*/`、`.claude/`、`.agents/`、`.cursor/`；harness 另加 `.ruff_cache/`，agent 原来已有 `.ruff_cache/`。补充后两边 `git status` 都只剩上面提到的未跟踪文档。

## 3. 本地删除

### 3.1 计划删除的目录和大小（删除前测量）

大小是可读文件的字节数之和；“拒绝访问”表示目录本身打不开，测不出大小。

harness：

| 路径 | 大小 | 文件数 | 备注 |
| --- | ---: | ---: | --- |
| `.a5-test-basetemp/` | 0 | 0 | 空 |
| `.pytest-tmp/` | 0 | 0 | 空 |
| `.pytest_cache/` | 77,218 B | 6 | |
| `.pytest_tmp/` | ? | ? | 拒绝访问 |
| `.tmp-a5-calibrator-20/`、`-20b/`、`-fix-tests/` | 0 | 0 | 空 |
| `.tmp-a5-calibrator-20c/` | 13,445 B | 23 | |
| `.tmp-a5-calibrator-debug2/` | 6,629 B | 8 | |
| `.tmp-a5-calibrator-final/` | 11,217 B | 20 | |
| `.tmp-a5-calibrator-full2/`、`-full3/` | 各 10,543 B | 各 19 | |
| `.tmp-a5-canary-real-20260924/`、`-v2/` | 0 | 0 | 空 |
| `.tmp-a5-canary-real-20260924-v3/`、`-v4/`、`-v5/` | 0 | 0 | 各只有一个 `B0/` 子目录，里面没有可读文件 |
| `.tmp-a5-canary-real-20260924-v6/` | 770,736 B | 25 | |
| `.tmp-a5-canary-real-20260924-v8/` | 1,919,451 B | 44 | |
| `.tmp-a5-canary-real-20260924-v9/` | 6,638,083 B | 103 | |
| `.tmp-a5-current-tests/`、`.tmp-a5-host-tests-01/`、`.tmp-a5-infra-05/`、`.tmp-a5-test-final/`、`.tmp-a5-typed-tests/`、`.tmp-pytest-a5-final/`、`.tmp-r2-initial/`、`.tmp-v8-unit/` | 0 | 0 | 空 |
| `.tmp-a5-host-tests-02/`、`-03/`、`-04/`、`.tmp-a5-infra-03/`、`-04/` | ? | ? | 拒绝访问 |
| `.tmp-r2-final/`、`.tmp-r2-initial-fullhost/`、`.tmp-r2-pilot-final-01/`、`.tmp-r2-pilot-tests-01/`、`.tmp-r2-regression-01/`、`.tmp-r2-summary-01/`、`.tmp-r2-summary-02/`、`.tmp-r2-wrapper-final-01/`、`.tmp-r2-wrapper-tests-01/`、`.tmp-r2-wrapper-tests-02/` | ? | ? | 拒绝访问 |
| `.tmp-repo-grader-tests-02/`、`-03/`、`-04/` | ? | ? | 拒绝访问 |
| `tmp/` | 112,939,388 B（约 108 MiB） | 5,882 | 另有 37 个子目录拒绝访问 |
| `tmp1317ghm0/` | ? | ? | 拒绝访问 |
| `__pycache__/`（根目录） | 7,194 B | 6 | |
| `scripts/__pycache__/` | 1,117,152 B | 68 | |
| `src/**/__pycache__/`（10 个目录） | 1,227,274 B | 149 | `src/`、`config`、`eval`、`execution`、`harness`、`llm`、`policy`、`runtime`、`tools`、`tracing` |
| `tests/__pycache__/`、`tests/fixtures/__pycache__/` | 5,076,226 B | 202 | |
| `cursor-a602-latest.txt` | 48,760 B | 1 | `docs/sprint/HARNESS-SPRINT-4.zh-CN.md` 第 19 行本来就要求删掉它 |

`__pycache__` 只删 `src/`、`scripts/`、`tests/` 和根目录下的；`.venv/`、`runs/`、`traces/`、`.swebench_envs/`、`docs/upgrade/evidence/`、`tests/fixtures/repos/` 里的不碰。

agent：

| 路径 | 大小 | 文件数 | 备注 |
| --- | ---: | ---: | --- |
| `.tmp/` | 4,216,541 B | 6,500 | 另有 3 个子目录拒绝访问。`docs/sprint/A6-R-SYNTHETIC-REPORT.md` 提到 `.tmp/a6-synthetic-r1`，但写明可以用 `scripts/make_a6_synthetic.py` 重新生成，且不进 git |
| `.pytest-run-final/` | 0 | 0 | 空 |
| `.ruff_cache/` | 3,427,581 B | 15,080 | |
| `.git.broken-20260924/` | 0 | 0 | 已确认是空目录 |

### 3.2 合同要求删除、但本轮保留等审计的目录

| 路径 | 大小 | 保留原因 |
| --- | ---: | --- |
| harness `.tmp/` | 809,467,388 B（约 772 MiB），33,790 个文件 | `docs/sprint/A5-CASE-DATA.md` 第 9 行写“核对脚本：`.tmp/case_mem.py`”，`docs/sprint/CHECKPOINT-7.md` 第 35 行、`docs/sprint/HARNESS-SPRINT-7-CLOSEOUT.zh-CN.md` 第 70 行都要求用它复跑 A5 案例数据。这个脚本不在 git 里，删了无法恢复。目录里还有其他审计脚本（`audit_leak.py`、`audit_pilot.py`、`audit_r4*.py`、`audit_r5_*.py`、`audit_round2*.py` 等）、两份对话 transcript、`a6-dry/`，以及旧的 Python 3.9 环境 `swebench_oracle_py39/`（`scripts/setup_swebench_envs.py` 会从它迁移） |
| harness `.tmp-canary-pytest-7220/` | 4,981,982 B，1,099 个文件 | `scripts/run_a5_real.py` 第 108、183 行把 `.tmp-canary-pytest-7220/workspace` 当输入，`docs/upgrade/evidence/A5-agent-canary-authorization-20260924-harness-attempt3/workspace-binding.json` 也绑定了这个路径 |
| harness `.tmp-a5-canary-real-20260924-v7/` | 2,982,373 B，109 个文件 | `scripts/regrade_a5.py` 第 15 行读这个目录 |

建议的选项：一是只把 `.tmp/` 里的 `case_mem.py` 等审计脚本挪进 git（例如 `scripts/audit/`），再删其余部分；二是整体保留，只靠 ignore。由审计决定。

### 3.3 删除结果

删除用的是 Python 的 `shutil.rmtree`，遇到只读文件会先去掉只读属性再重试；没有改 ACL，也没有用管理员接管所有权。脚本对 `runs/`、`traces/`、`.venv/`、`.env`、`.swebench_envs/`、`baseline/`、`.git/`、`docs/`、`tests/fixtures/repos/` 做了硬性排除。删完后检查：两边 `git status` 只有删除前就有的未跟踪文档，没有被跟踪的文件受影响；harness 的 `runs/`、`traces/`、`.venv/`、`.env`、`.swebench_envs/`、`tests/fixtures/repos/`，agent 的 `traces/`、`.env`、`baseline/`、7 个根目录 PDF 都还在。

已删除：
- harness：`.a5-test-basetemp/`、`.pytest-tmp/`、`.pytest_cache/`；24 个 `.tmp-*` 目录（3.1 表中所有非“拒绝访问”的 `.tmp-*`，`-v7` 和 `.tmp-canary-pytest-7220` 除外）；根目录、`scripts/`、`src/**`、`tests/`、`tests/fixtures/` 下共 14 个 `__pycache__/`；`cursor-a602-latest.txt`。`tmp/` 里所有可读内容都删了，包括 `tmp/pdfs/resume-review/`。这个目录名看起来像简历相关，删除前我只看到它是个目录，没有记录里面有什么；它的大小算在 `tmp/` 的 112,939,388 B 里。
- agent：`.pytest-run-final/`、`.ruff_cache/`、`.git.broken-20260924/`；`.tmp/` 里所有可读内容。

删不掉、留在本地的（都是 ACL“拒绝访问”，里面已经没有可读文件）：
- harness 根目录 20 个：`.pytest_tmp/`、`.tmp-a5-host-tests-02/`、`-03/`、`-04/`、`.tmp-a5-infra-03/`、`-04/`、`.tmp-r2-final/`、`.tmp-r2-initial-fullhost/`、`.tmp-r2-pilot-final-01/`、`.tmp-r2-pilot-tests-01/`、`.tmp-r2-regression-01/`、`.tmp-r2-summary-01/`、`.tmp-r2-summary-02/`、`.tmp-r2-wrapper-final-01/`、`.tmp-r2-wrapper-tests-01/`、`.tmp-r2-wrapper-tests-02/`、`.tmp-repo-grader-tests-02/`、`-03/`、`-04/`、`tmp1317ghm0/`。
- harness `tmp/` 下 37 个子目录：`a5-repo-baseline-regression-02..04`、`accept-hp02-*`（4 个）、`accept-hp03-*`（4 个）、`accept-hp04-*`（6 个）、`accept-session-regression`、`deepseek-fix-01`、`deepseek-unit-03`、`h3-*`（6 个）、`h4-*`（4 个）、`h5-*`（4 个）、`plugin-registry-02`、`pytest-docker-venv`、`pytest-h5-targeted`。这些目录里剩下的可读字节数是 0。
- agent `.tmp/` 下 3 个子目录：`pytest/`、`pytest_cache/`、`pytest_check/`。可读字节数是 0。

这些目录都已经被 `.gitignore` 覆盖，不会进 git，也不会进 monorepo。如果要彻底删掉，需要用管理员权限执行 `takeown /f <dir> /r /d y` 和 `icacls <dir> /grant Administrators:F /t`，再删除。本轮没有执行，等用户决定。

按合同保留、本轮没有动：`runs/`、`traces/`、`.venv/`、`.swebench_envs/`、`baseline/`、`.env`、根目录 PDF。agent 的 `.pytest_cache/` 不在合同的删除清单里，也没有动。3.2 节那 3 个等审计的目录也原样保留。

## 4. 2.1 节的 36 个 private/gold 路径（等审计决定，本轮未移除）

这些路径都匹配 `.gitignore` 里的 `docs/upgrade/evidence/**/private*`，但在规则加进去之前就已经被跟踪了，所以仍在 git 里。下面每个文件只写前 3 行的摘要，不贴内容；“行数”指文件总行数。没有一个文件含真实 SWE-bench 任务的 gold patch 或 test patch 的 diff 正文。

### 4.1 H5-interop 单任务交接包，16 个

任务都是合成的 `public-settings-001`，可编辑文件是 `settings.py`。

| 路径 | 字节 / 行数 | 前 3 行摘要 |
| --- | --- | --- |
| `docs/upgrade/evidence/H5-interop/offline-01/handoff/private/agent-evaluation-index.json` | 185 / 1 | 单行 JSON，键为 `expected_files`（空）、`future_trajectory_refs`（空）、`gold_patch: null`、`hidden_test_refs`（1 项）、`schema_version`、`tags`、`task_id` |
| `docs/upgrade/evidence/H5-interop/offline-01/handoff/private/evaluation-spec.json` | 827 / 1 | 单行 JSON，键为 `base_hash`、`cases`（4 个函数级用例，字段 `args`/`case_id`/`expected`/`function`/`module_path`）、`editable_paths`、`image`、`task_id`、`timeout_seconds` |
| `.../offline-02/handoff/private/agent-evaluation-index.json` | 185 / 1 | 同 offline-01 |
| `.../offline-02/handoff/private/evaluation-spec.json` | 827 / 1 | 同 offline-01 |
| `.../offline-03/handoff/private/agent-evaluation-index.json` | 185 / 1 | 同上 |
| `.../offline-03/handoff/private/evaluation-spec.json` | 827 / 1 | 同上 |
| `.../offline-04/handoff/private/agent-evaluation-index.json` | 185 / 1 | 同上 |
| `.../offline-04/handoff/private/evaluation-spec.json` | 827 / 1 | 同上 |
| `.../real-01/handoff/private/agent-evaluation-index.json` | 185 / 1 | 同上 |
| `.../real-01/handoff/private/evaluation-spec.json` | 827 / 1 | 同上 |
| `.../real-02/handoff/private/agent-evaluation-index.json` | 185 / 1 | 同上 |
| `.../real-02/handoff/private/evaluation-spec.json` | 827 / 1 | 同上 |
| `.../real-03/handoff/private/agent-evaluation-index.json` | 185 / 1 | 同上 |
| `.../real-03/handoff/private/evaluation-spec.json` | 827 / 1 | 同上 |
| `.../real-04/handoff/private/agent-evaluation-index.json` | 185 / 1 | 同上 |
| `.../real-04/handoff/private/evaluation-spec.json` | 827 / 1 | 同上 |

（`...` = `docs/upgrade/evidence/H5-interop`）

### 4.2 R2-real 合成配置的期望事实，15 个

每个文件都是 6 行 JSON，4 个键：`endpoint`、`timeout_ms`、`retry_limit`、`idempotency_header`。前 3 行是 `{`、`endpoint`、`timeout_ms`，内容是合成服务配置（例如 `/v3/batch-events` 这类端点和毫秒数），不涉及任何真实仓库。

| 路径（前缀 `docs/upgrade/evidence/R2-real/`） | 字节 | `endpoint` 值的类别 |
| --- | ---: | --- |
| `pilot-01/private/assistant-pressure.json` | 117 | v3 batch-events |
| `pilot-01/private/old-facts.json` | 114 | v2 telemetry |
| `pilot-01/private/short-control.json` | 119 | v1 health-events |
| `wrapper-01/private/missing-fact.json` | 122 | v4 public-events，`timeout_ms` 为 null |
| `wrapper-01/private/quoted-instruction.json` | 122 | v4 public-events |
| `wrapper-01/private/short-control.json` | 119 | v1 health-events |
| `wrapper-01/private/trace-assistant-pressure-r1-mask-then-summary.json` | 117 | v3 batch-events |
| `wrapper-01/private/trace-assistant-pressure-r1-summary.json` | 117 | 同上 |
| `wrapper-01/private/trace-assistant-pressure-r2-mask-then-summary.json` | 117 | 同上 |
| `wrapper-01/private/trace-assistant-pressure-r2-summary.json` | 117 | 同上 |
| `wrapper-01/private/trace-assistant-pressure-r3-mask-then-summary.json` | 117 | 同上 |
| `wrapper-01/private/trace-assistant-pressure-r3-summary.json` | 117 | 同上 |
| `wrapper-01/private/trace-old-facts-r1-summary.json` | 114 | v2 telemetry |
| `wrapper-01/private/trace-old-facts-r2-summary.json` | 114 | 同上 |
| `wrapper-01/private/trace-old-facts-r3-summary.json` | 114 | 同上 |

（上表 15 行，加上下面 full-repo-grader 的 4 个和 `scripts/` 的 1 个，再加 4.1 的 16 个，共 36 个。）

### 4.3 full-repo-grader 的整仓 known-good 和隐藏测试 overlay，4 个（最敏感）

| 路径 | 字节 / 行数 | 前 3 行摘要 |
| --- | --- | --- |
| `docs/upgrade/evidence/full-repo-grader/attempt-01/private/known-good.json` | 2,113,685 / 252 | `{`，然后每行一个键值对：键是 Flask 仓库的文件路径（共 250 个，从 `.editorconfig`、`.flake8` 开始），值是该文件内容的 base64。也就是一份**已修好的整仓快照**，等于把正确答案编码在里面 |
| `docs/upgrade/evidence/full-repo-grader/attempt-01/private/overlay.json` | 10,512 / 3 | `{`、`"tests/test_config.py": <base64>`、`}`。这是 grader 侧叠加的**隐藏测试文件**全文（base64），相当于 test patch |
| `docs/upgrade/evidence/full-repo-grader/attempt-02/private/known-good.json` | 2,113,685 / 252 | 同 attempt-01 |
| `docs/upgrade/evidence/full-repo-grader/attempt-02/private/overlay.json` | 10,594 / 4 | `{`、`"tests/test_config.py": <base64>`、`"tests/static/config.toml": <base64>`（第 4 行是 `}`） |

从键名看，这 4 个文件对应的是 Flask 仓库上一个和 `tests/test_config.py` 有关的任务（full-repo-grader 的早期验证），不像是 A5/A6 用的 SWE-bench Verified 任务。但它们确实是“答案 + 隐藏测试”，请审计重点决定。两个 `known-good.json` 各约 2 MB。

### 4.4 `scripts/sprint2_debug_gold.py`，1 个

1,030 字节 / 35 行。前 3 行是 `import asyncio`、`import json`、`import sys`。这是 sprint 2 的调试脚本：用 `scripts/sprint2_calibrate.py` 的 `gold_delta` 把 gold patch 路径对应的改动交给 `ImageGrader` 跑一遍，打印 F2P/P2P 结果。脚本本身不含 patch 内容，只引用私有输入的路径（`private_source_binding.gold_patch_paths`）。

## 5. 第 4 节第 1–3 项的预扫描（两个原仓库的全部历史）

方法：`git rev-list --objects --all` 取出所有可达 blob（harness 7,207 个，agent 1,163 个），逐个用 `git cat-file --batch` 读出内容做正则扫描；命中时只记录 blob、路径、提交号、行号和分类。没有找到 gitleaks，也没有装 detect-secrets，用的是合同允许的正则方案。脚本不输出匹配到的值。

### 5.1 密钥

| 规则 | harness | agent |
| --- | --- | --- |
| `sk-[A-Za-z0-9]{20,}` | 0 | 0 |
| `Authorization: Bearer`（不区分大小写） | 0 | 0 |
| `api_key\s*[:=]`（不区分大小写） | 72 处：29 处引用环境变量或变量、20 处占位符、14 处表达式、8 处短字面量、1 处空值；**疑似真实密钥 0 处** | 17 处：2 处环境变量、6 处占位符、7 处表达式、1 处短字面量、1 处空值；**疑似真实密钥 0 处** |

`api_key` 的非环境变量命中我逐行人工复核过（复核时把引号里的值替换成长度，不看原值）：都是 `your-...` 占位符、`<secret>`、函数参数，或者测试里由小写单词和连字符拼成、不含数字的假值，例如 `tests/test_summary_pilot.py:61`、`tests/test_summary_wrapper.py:93`、`tests/test_true_summary.py:310`。没有疑似密钥，所以也没有需要报告的文件名、提交号和行号。

`.env`：两个仓库全部历史里，没有任何路径的文件名是 `.env` 或 `.env.*`（`.env.example` 除外）。也就是说 `.env` 从来没被跟踪过。

### 5.2 私有评测字段（`FAIL_TO_PASS`、`test_patch`、`"patch":`）

在全部历史中出现过这三个字段之一的路径：harness 89 个，agent 17 个。我把每个路径的所有历史版本又分了一次类：
- `field-name-only`：只出现了字段名，比如代码里读字段、文档里描述隔离规则；
- `f2p_list`：有非空的 FAIL_TO_PASS 列表；
- `diff_payload` / `diff_text`：有 patch 字段带 diff 正文，或者有 diff 文本。

带负载的只有下面 8 个：

| 仓库 | 路径 | 是否还在 HEAD | 类别 | 说明 |
| --- | --- | --- | --- | --- |
| harness | `swebench_candidates.jsonl` | 否（`fc29b0f` 移出） | f2p_list | 真实 SWE-bench Lite 候选，带 FAIL_TO_PASS 测试 id；没有 `test_patch`/`patch` 字段 |
| harness | `swebench_candidates_short.jsonl` | 否（`fc29b0f` 移出） | f2p_list | 同上 |
| harness | `tmp_requests_2674.jsonl` | 否（`fc29b0f` 移出） | f2p_list | 同上 |
| harness | `tmp_requests_863.jsonl` | 否（`fc29b0f` 移出） | f2p_list | 同上 |
| harness | `tests/test_build_a6_attempts.py` | 是 | diff_payload | 合成 fixture（`pkg/widget.py`、`tests/test_widget.py`、`SECRET_GOLD` 常量），用来测试泄漏检测 |
| harness | `tests/test_a5_repo_baseline.py` | 是 | diff_text | 合成 fixture（`module.py`、`test_new.py`） |
| harness | `tests/test_run_a5_main.py` | 是 | f2p_list | 合成常量 `{"patch": "GOLD", "test_patch": "TESTS", "FAIL_TO_PASS": '["t::a"]'}` |
| agent | `tests/test_a5_preparation.py` | 是 | f2p_list | 合成值 `'["private_test"]'` |

（上表 8 行：harness 7 个、agent 1 个。）

其余路径只出现了字段名，全部还在 HEAD 里。

harness（82 个）：
- `docs/sprint/` 10 个：`A5-MAIN-FREEZE.md`、`AUDIT-3-CORRECTION.zh-CN.md`、`CHECKPOINT-6.md`、`CHECKPOINT-A6-1.md`、`HARNESS-CAPABILITY-SPRINT.zh-CN.md`、`HARNESS-SPRINT-6C-FIX.zh-CN.md`、`MEMORY-SOURCE-EXPANSION.md`、`PROGRESS.md`、`a6-attempts.json`、`memory-source-runs.json`
- `docs/archive/` 3 个：`SOLID-D1-POLISH-EXECUTION`、`SOLID-D1-SCAFFOLD-EXECUTION`、`SOLID-D1-SWEBENCH-EXECUTION`
- `docs/changes/` 2 个：`SOLID-D1-POLISH-CLOSEOUT`、`SOLID-D1-SWEBENCH-CLOSEOUT`
- `docs/upgrade/evidence/` 39 个，都是 preflight 的 `receipt(s).json`（`test_patch` 只以哈希或路径字段出现）、`A5-harness-preflight-10-input-gate/inputs.json`、`A5-harness-preflight-48-django-contract-resolution/contract-resolution.json`、`A5-real240-77-harness-preflight/memory-consumption-contract.json`、`.../public-boundary-audit.json`。涉及的目录：preflight-25g、25k、25l、27、33、34、35、36、38、40、57、62
- `reports/examples/` 3 个：`swebench_lite_real.md`、`tmp_requests_2674_log.json`、`tmp_requests_863_log.json`
- `scripts/` 22 个：`a5_memory_provenance_review.py`、`a5_memory_source_smoke.py`、`audit_a5_host_preflight.py`、`audit_a5_repo_baseline.py`、`build_a6_attempts.py`、`build_clean_baseline.py`、`build_swebench_lite_subset.py`、`calibrate_pilot_image_grader.py`、`diagnose_pytest7432_ids.py`、`preflight_a5_pytest.py`、`preflight_a5_repo_baseline.py`、`recheck_a5_repo_baseline.py`、`run_a5_main.py`、`run_a5_real.py`、`run_swe_task.py`、`select_main_targets.py`、`select_swebench_instances.py`、`sprint2_calibrate.py`、`sprint4_write_b0_results.py`、`sprint5_prepare_main.py`、`sprint5_scan_official.py`、`sprint6_void_r2.py`
- `src/eval/a5_memory_snapshot.py`
- `tests/`：`test_no_silent_fallback.py`、`test_sprint6_predict_injection.py`

agent（16 个）：`benchmarks/a5/pilot20-source-v1/README.upstream.md`、`configs/a5/canonical-handoff.json`、`configs/a5/lightweight-memory-import.schema.json`、`docs/upgrade/A5-PILOT20-PREPARATION.md`、`docs/upgrade/A5-PILOT20-STATUS.md`、`reposkill_agent/core/context_expansion.py`、`reposkill_agent/eval/graph_runner.py`、`reposkill_agent/experiments/funding.py`、`reposkill_agent/experiments/preparation.py`、`reposkill_agent/memory/lightweight_snapshot.py`、`scripts/build_memory_cards.py`、`tests/test_a5_funding.py`、`tests/test_event_extract.py`、`tests/test_memory_cards.py`、`tests/test_memory_cards_v3.py`、`tests/test_memory_cards_v5.py`

注意：这项扫描只认这三个字段名。第 4.3 节的 `known-good.json`/`overlay.json` 是 base64 编码，扫不到；第 6 节那些历史 `private-spec*.json` 里的 `test_overlay`、`expected_nodeids` 字段也扫不到。这两类要靠路径名单来管。

### 5.3 本机信息（P-1 提交后的 HEAD，被跟踪文件）

| 仓库 | 模式 | 文件数 | 出现次数 | 主要分布 |
| --- | --- | ---: | ---: | --- |
| harness | `C:\Users\` | 53 | 83 | `docs/upgrade/evidence` 14、`docs/changes` 13、`docs/archive` 12、`docs/sprint` 2、`reports/examples` 2 |
| harness | `23500` | 48 | 73 | `tests/fixtures` 32（大多是 fixture 数据里的数字，不一定是本机信息）、`docs/upgrade/evidence` 6 |
| harness | `Administrator` | 45 | 73 | `docs/changes` 13、`docs/upgrade/evidence` 13、`docs/archive` 12、`reports/examples` 2、`scripts/build_swebench_lite_subset.py` |
| harness | `D:\crq` | 678 | 4,225 | `docs/upgrade/evidence` 636、`docs/sprint` 12、`docs/archive` 5、`configs/a5` 2、`configs/sprint` 2、`src/eval` 2 |
| agent | `C:\Users\` | 13 | 49 | `docs/upgrade/tasks` 4、**`README.md`**、`benchmarks/a5`、`docs/upgrade/*` |
| agent | `23500` | 2 | 2 | `docs/upgrade/01_coding-harness_总修改目标_v1.0.md`、`reports/phase6/` 下 1 个文件 |
| agent | `Administrator` | 11 | 44 | `docs/upgrade/tasks` 4、**`README.md`**、`docs/upgrade/*` |
| agent | `D:\crq` | 44 | 222 | `docs/sprint` 13、`docs/upgrade/tasks` 4、`reports/external_baselines` 4、`benchmarks/a5` 3、`configs/a5` 2 |

逐文件的名称和计数在附件 [`CHECKPOINT-P1-LOCAL-INFO.md`](CHECKPOINT-P1-LOCAL-INFO.md)。按合同，这一项不阻断发布。需要留意的是：agent 的 `README.md` 第 20 行有 `C:\Users\Administrator\.conda\...` 解释器路径；P-2 给子目录 README 加抬头时，可以考虑一并处理。两边的根 `README` 里都没有 `D:\crq`，harness 根 `README` 里也没有 `C:\Users\`。

合同第 1 节要求列出的跨仓库路径引用（`ROOT.parent / "coding-agent"`、`D:\crq\src\coding-harness` 等）属于 P-2 第 4 节的检查，本轮没有单独列；上表中 `src/eval`、`configs/*`、`scripts/*` 的 `D:\crq` 命中就是这一类的主要来源。

## 6. 历史中出现过、但最新提交里已移除的敏感路径

`git rm --cached` 只影响之后的提交。下面这些文件**仍然能从旧提交里取出来**。仓库保持私有的话，影响不大；如果以后要改成公开，就要另做决定：要么接受历史里有这些文件，要么另建一个不带历史的公开仓库。第 4 节的 36 个文件如果经审计移除，也会加入这份名单。

harness（16 个；agent 0 个）：

| 路径 | 引入提交 | 移除提交 | 内容类别 |
| --- | --- | --- | --- |
| `docs/upgrade/evidence/H3/final/private-spec.json` | `7bb4395` | `b5cb425` | 私有评测规格（348 B；`cases` 为合成函数用例） |
| `docs/upgrade/evidence/H5/deepseek-flash-attempt-01/private-spec.json` | `7bb4395` | `b5cb425` | 同上（4,116 B） |
| `docs/upgrade/evidence/R2-real/pilot-01/repair-data/public-settings-001/private-spec.json` | `7bb4395` | `b5cb425` | 同上（1,197 B） |
| `docs/upgrade/evidence/full-repo-grader/validation-01/private-spec-initial.json` | `7bb4395` | `b5cb425` | 整仓 grader 规格，含 `expected_nodeids` 和 `test_overlay`（隐藏测试，41,483 B） |
| `docs/upgrade/evidence/full-repo-grader/validation-01/private-spec.json` | `7bb4395` | `b5cb425` | 同上（71,363 B） |
| `docs/upgrade/evidence/full-repo-grader/validation-03/private-spec-initial.json` | `7bb4395` | `b5cb425` | 同上（41,567 B） |
| `docs/upgrade/evidence/full-repo-grader/validation-03/private-spec.json` | `7bb4395` | `b5cb425` | 同上（71,933 B） |
| `swebench_candidates.jsonl`、`swebench_candidates_short.jsonl` | `b4e14f2` | `fc29b0f`（本轮） | SWE-bench Lite 候选，含 FAIL_TO_PASS |
| `tmp_requests_2674.jsonl`、`tmp_requests_863.jsonl` | `b4e14f2` | `fc29b0f`（本轮） | 同上 |
| `CLAUDE.md`、`AGENTS.md`、`CLAUDE-CODE-IMPROVEMENTS.md`、`CLAUDE-CODE-RESUME-POLISH.md` | `b4e14f2` | `cbe1e46`（本轮） | AI 工具指令文件，含本机绝对路径 |
| `.claude/settings.local.json` | `b4e14f2` | `cbe1e46`（本轮） | AI 工具本地设置 |

筛选规则：历史路径名匹配 `private|gold|secret|credential|.env|hidden|known-good|overlay|CLAUDE|AGENTS.md|settings.local|tmp_requests|swebench_candidates|.claude/|.cursor/|.agents/`，并且不在 HEAD 里。那 7 个 `private-spec*.json` 只存在于提交 `7bb4395`（2026-09-24），下一个提交 `b5cb425` 就删掉了（`pre-capability-sprint` tag 指向 `b5cb425`）。我逐个 tag 用 `git cat-file -e` 检查过，14 个 tag 都不包含它们，但从 `main` 的历史里仍能检出。
