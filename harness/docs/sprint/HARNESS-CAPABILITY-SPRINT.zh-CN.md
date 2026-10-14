# coding-harness 能力冲刺计划书

日期：2026-09-24。执行者：挂在 `D:\crq\src\coding-harness` 的 Cursor agent。
配套：`D:\crq\src\coding-agent\docs\sprint\AGENT-MEMORY-REBUILD.zh-CN.md`（agent 侧计划，另一个对话执行）。

## 0. 背景：为什么改方向

A5 的 240 行矩阵（20 题 × B0–B3 × 3 次）暂停。原因来自 v7–v9 canary 的实测：

- B0（不加记忆）在 `pytest-7220` 上 24 轮都没有改出任何代码，改动文件数为 0。B0 解不出题，B1–B3 和 B0 就没有可比的差别，跑 240 次得到的是无信息结果。
- 解不出题的主要原因在 harness 的工具和上下文设计，不是轮次不够：
  - `src/tools/files.py` 的 `read_file` 只有 `limit`，不能从中间读；截断后也不提示总行数和怎么继续。v9 在这上面白费了 4 轮。
  - 没有搜索工具，只能靠 `run_command` 调 grep。
  - `src/runtime/window.py` 的 masking 调用 `micro_compact_openai_messages_with_stats(..., preserve_tools=set())`，旧结果被替换成 `[Previous: used read_file]`（见 `src/runtime/compact.py`），不保留路径、行数等任何信息；再加上 `keep_recent=4`，模型只记得最近 4 次观察，于是反复重读。
  - `src/runtime/loop.py` 的 `SYSTEM_PROMPT` 只有几行通用说明：没有 SWE 工作流，不告诉模型剩余轮次，不鼓励并行读取。
  - `configs/deepseek.yaml` 用的是 `deepseek-flash`，关闭了 thinking；`run_command` 超时 30 秒，对 pytest 可能偏短。
- `scripts/run_a5_real.py` 写死在 `pytest-7220` 一道题上，而且有明显问题：
  - `harness_fingerprint` 是对常量字符串取 sha。
  - `GRADER_IMAGE` 被赋值两次。
  - 历史账本是手写常量。
  - 同时存在 USD 的 `max_cost_usd` 和 CNY 的 ledger 两套预算。
- 9 月以来的全部工作都没有 git 提交；`docs/upgrade/evidence` 有约 42.7 万个文件、6.5 GB，大多是整仓副本。

新方向：**先让 harness 在 B0 下能真实解题，并用它做 harness 设计的对照实验；记忆实验等 B0 站稳后再缩小规模重做。**

## 1. 工作方式（放宽后的规则）

之前 A5 的合同、hash lock、双端复核、每次新建证据目录等流程**全部暂停**，不要再新增这类文件。放宽的前提是版本控制，所以第 0 步必须先完成。

保留的硬约束只有这些：

1. **不泄密**：`.env` 和 API key 不进 git、不进日志、不打印。
2. **答案隔离**：gold patch、test patch、FAIL_TO_PASS / PASS_TO_PASS 只能给 grader 用，不能出现在 agent 可见的 workspace、prompt 或工具输出里。现有 `RepositoryGrader` 的分离方式保留。
3. **Hold-out**：`coding-agent/reports/upgrade/a5-pilot20-preparation-20260921-v4/assignments.json` 里的 20 个 pilot 目标题**不能用来调参**。冲刺期间一律不跑它们。
4. **花钱上限**：本计划全部真实模型调用累计 **≤ 30 CNY**。单次运行 ≤ 1 CNY。接近上限时停下来问用户。每次运行结束后把实际花费追加到进度日志。
5. **git 纪律**：小步提交，提交前跑相关测试；不 force push，不改写已有历史，不删除旧证据（只能移出 git 跟踪范围）。
6. **不改 coding-agent 仓库**。需要 agent 侧配合时，在进度日志里写清楚，由用户转达。

日常记录只维护一个文件：`docs/sprint/PROGRESS.md`。每完成一步追加一小段：改了什么、测试结果、运行结果（题、是否解出、首次改代码的轮次、调用次数、花费）、下一步计划。运行产物放在 `runs/`（加入 `.gitignore`），不再放进 `docs/upgrade/evidence`。

## 2. 分步计划

### 第 0 步：版本控制和清理（先做，不花钱）

1. 更新 `.gitignore`，加入：
   - `.tmp-*/`、`.a5-test-basetemp/`、`.pytest-tmp/`、`tmp*/`、`runs/`、`traces/`；
   - `docs/upgrade/evidence/` 下的大文件和整仓副本。规则是：只跟踪 evidence 里的 `*.md` 和小于 200KB 的 `*.json`，`staging/`、`workspace/`、`original/`、`known-good/`、`baseline/`、`tasks/**/private*` 这类子目录全部忽略。用 `git check-ignore` 抽查规则是否生效。
   - 磁盘上的文件不删，只是不再跟踪。
2. 跑一次完整测试：`.\.venv\Scripts\python.exe -m pytest -q`。把通过和失败的数量记进 PROGRESS.md。失败的测试先记下来，不用在这一步全修好。
3. 按模块分几次提交 9 月以来的工作。建议分组如下，可按实际 diff 调整：
   - 模型网关：`src/llm/*`、`tests/test_llm_*`
   - 工具和执行：`src/tools/*`、`src/execution/*`、`src/policy/*`
   - 会话和恢复：`src/runtime/session.py`、`recovery.py`、`deadline.py`、`awaitctl.py`、`src/tracing/*`
   - 上下文：`src/runtime/window.py`、`summary.py`、`context.py`、`compact.py`
   - 评测和 grader：`src/eval/*`
   - A5 相关脚本和配置：`scripts/*a5*`、`configs/a5/`、`docker/`
   - 文档：`docs/upgrade/*.md`、README
   - 提交前检查 staged 内容里没有 `.env`、API key，也没有大于 5MB 的文件。
4. 打 tag：`pre-capability-sprint`。
5. `AGENTS.md` 和 `CLAUDE.md` 里的参考项目路径是失效的（`C:\Users\23500\...`）。本机实际路径是 `D:\crq\src\learn-claude-code-main`，改过来。

完成标准：`git status` 基本干净（只剩被 ignore 的内容），tag 已打，PROGRESS.md 记录了测试基线。

### 第 1 步：通用单题运行器 + dev 集（基本不花钱）

1. 新建 `scripts/run_swe_task.py`（或者放在 `src/eval/` 下，再配一个薄 CLI）。输入包括：
   - 任务 ID 列表
   - profile yaml（模型、轮次、上下文策略、工具开关）
   - variant（先只支持 B0）
   - 输出目录
   
   复用 `run_a5_real.py` 里已经能用的部分：`A5ImageBackend`、`RepositoryGrader`、`RunSession`、`build_agent`、CNY ledger。去掉所有写死的常量，每道题的镜像、workspace 来源、测试 spec 都从任务清单读取。
2. 每次运行的输出放在 `runs/<run_id>/<task_id>/`：`events.jsonl`、`candidate-delta.json`、`grader-result.json`，外加一个小的 `summary.json`。summary 包括：
   - 是否解出（以 grader 的 FAIL_TO_PASS 全通过、且 PASS_TO_PASS 无回归为准）
   - 改动文件、首次调用编辑工具的轮次、模型调用次数、工具调用次数、峰值上下文、费用、终止原因
   - 两个仓库的 `git rev-parse HEAD` 和是否有未提交修改
   
   不再计算 `harness_fingerprint` 这类伪指纹。
3. 预算只保留 CNY ledger 一套。`max_cost_usd` 和 price_table 不再在 runner 里另外设置；如果底层 `ModelBudgetLedger` 必须要，就设成不起约束的大值，并在代码注释里写明 CNY ledger 才是权威。
4. **选 dev 集**：盘点本机已有 grader 镜像、能展开 workspace 的 SWE-bench 任务（`docs/upgrade/evidence` 里 preflight 和校准过的任务、11 条记忆源题所在的那批），**排除 20 个 pilot 目标**，选 8–10 道。尽量覆盖 django、sympy、scikit-learn、pytest，难度有高有低。把清单写进 `configs/sprint/dev-tasks.yaml`，一起提交。镜像或 workspace 缺失的题，能用现有脚本（`prepare_repo_grader.py` 等）补就补，补不了就换一道。
5. **给 11 条记忆源题的历史改动打分**（agent 侧会用到，不花模型钱）：用 grader 对记忆池里这 11 条的 `candidate-delta.json` 跑一次，结果写到 `docs/sprint/memory-source-verification.json`（提交进 git）。每条记录包括：`source_id`、`status`（`pass` / `partial` / `fail` / `grader_unavailable`）、F2P 和 P2P 的通过数。记忆源的目录位置见 `docs/upgrade/evidence/A5-real240-77-harness-preflight/memory-snapshot.jsonl` 里的 `source_dir` 字段。
6. 用 zero-model fixture 或 mock LLM，把 runner 在 1 道 dev 题上端到端跑通，包括 workspace 准备、Docker、grader、summary。

完成标准：一条命令能在任意 dev 题上跑 B0；`memory-source-verification.json` 已生成；PROGRESS.md 已记录。

### 第 2 步：B0 能力冲刺（主要花钱的阶段，≤ 25 CNY）

每一项改动都要满足三点：补零模型单元测试；单独提交；在 dev 集上跑一轮 B0（或抽 3–4 道代表题），把结果记进 PROGRESS.md 并和上一版比较。建议顺序如下，前 3 项收益最大，可以先合并在一起跑一轮：

1. **`read_file` 改造**（`src/tools/files.py`，以及 Docker 路径下的 `src/tools/container_files.py`，两条路径都要改）：
   - 新增 `offset`（起始行，从 1 开始）和 `limit` 参数；输出带行号。
   - 截断时提示：`[showing lines A-B of N; call read_file with offset=B+1 to continue]`。
   - 字符截断也按整行截断，并给出同样的提示。
2. **搜索工具**：新增 `search_code`（grep 风格），参数包括 `pattern`、`path`、`glob`、`max_results`，输出格式为 `path:line: text`，结果数有上限。容器里有 `rg` 就用 `rg`，否则用 `grep -rn`。标记为只读，并加入 Docker profile 的工具白名单（`src/harness/factory.py` 里的 `docker_linux` 分支）。
3. **masking 占位符**：把 `[Previous: used {tool_name}]` 改成保留关键信息的形式，例如 `[Elided result of read_file(path=src/_pytest/nodes.py, offset=400) — 300 lines; re-read if needed]`、`[Elided result of run_command(pytest ...) — exit 1, 240 lines]`。参数从对应 assistant 消息的 tool_call 里取。`keep_recent` 改成 profile 里可配置，试一下 4 和 8。
4. **system prompt 和预算提示**：
   - 写一份 SWE 工作流 prompt，放在 `prompts/swe_b0.md`，通过 `system_prompt_path` 加载：先定位，尽早复现，找到原因后尽早修改，修改后跑相关测试，最后给出简短总结。
   - 明确说"互不依赖的读取和搜索请放在同一轮并行调用"。
   - 每轮在上下文末尾注入一行 `remaining model calls: N/M`（由 loop 或 hook 生成，不写死在 prompt 里）。
5. **命令超时**：`run_command` 默认超时改为 profile 可配，dev profile 用 120 秒。
6. **模型配置**：在固定上述改动后，对比 `thinking: disabled` 和开启 thinking（或者 DeepSeek 的非 flash 模型）在 3–4 道题上的解题率和单题费用，结果记下来，由用户决定最终用哪个。
7. 轮次上限先用 40 次模型调用、60 步；上下文窗口 96k。之后看数据再调。

完成标准（二选一，满足任意一条就进入审计节点）：

- dev 集上 B0 至少解出 3 道，而且 PROGRESS.md 能说明每项改动的贡献；或者
- 花费接近 25 CNY，或所有改动都做完后仍然解不出 3 道。这时写清楚卡在哪里，停下。

### 第 3 步（可选，≤ 5 CNY）：外部锚点

如果能在本机装上 `mini-swe-agent`（或 SWE-agent），就用同一个模型在同一批 dev 题上跑一次，比较解题率和单题费用。装不上或者要大改环境，就跳过，并在 PROGRESS.md 里注明原因。它的作用是回答"这个 harness 和公开 baseline 比，处在什么水平"。

## 3. 审计节点（完成第 2 步或第 3 步后停下）

写 `docs/sprint/CHECKPOINT-1.md`，内容一页以内：

- `pre-capability-sprint..HEAD` 的提交列表（`git log --oneline`）
- dev 集的结果表：每道题每个版本是否解出、首次改代码的轮次、调用次数、费用
- 每项改动的效果判断，没有效果或反而变差的也要写
- 累计花费
- 遗留问题和下一步建议（例如 harness 设计消融实验怎么做，什么时候接回记忆实验）

然后停下，等用户找审计者看过再继续。

## 4. 本阶段不做的事

- 不跑 20 个 pilot 目标题，不跑 B1–B3，不进 240 矩阵。
- 不新增 A5 合同、lock 或 receipt 文件。旧的 A5 脚本保留原样，不再扩展。等新 runner 稳定后，在审计节点讨论要不要清理。
- 不改 `coding-agent` 仓库。
- 不做 FastAPI、前端，也不做多 agent 或 subagent 扩展。
