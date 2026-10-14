# Solid B 批次 · 执行清单（Composer 2.5 用）

> **定位**：A 批次（5 项）已完成（见 `docs/changes/SOLID-A-BATCH-CLOSEOUT.zh-CN.md`，112 passed）。本文是 B 批次的可直接落地清单，决策已锁定，按顺序做即可。  
> **上游**：`docs/SOLID-ROADMAP.zh-CN.md`（方向与 ABC 分层）。  
> **环境**：`C:\Users\Administrator\.conda\envs\coding-harness\python.exe`；测试加 `--basetemp $env:TEMP\coding-harness-pytest`。  
> **基线**：当前全量 **112 passed**；每项改动后必须保持全绿，再跑相关真实 eval。

---

## 0. 已锁定决策（不要再改）

| 决策点 | 选定方案 | 说明 |
|--------|----------|------|
| P2-2 argv runner 形态 | **A：`run_command` 双模式** | 同一工具新增可选 `argv` 参数；不新建独立工具。`command`（字符串）与 `argv`（数组）二选一 |
| argv 是否默认替代 shell | **A：默认仍 shell，argv 为 opt-in** | 向后兼容；新增配置项 `command.prefer_argv`（默认 `false`）。`argv` 传入时走 argv 执行路径 |
| P0-1 任务扩充规模 | **A：9 → 12** | 新增 3 个：1 纯 read+answer、1 subagent 专用、1 多文件。不一次铺到 15 |

---

## 1. 执行顺序（5 项）

1. P2-2 阶段A — argv 命令执行 + 环境变量白名单
2. P0-1 A — 评测集扩到 12 + tag 分组报告 + oracle 校验
3. P0-2 B — AST 结构化裁判 + flaky 检测
4. P1-1 B — step 显式 `suggested_tools` + 结构化 replan（顺带修 `schema_ok` 弱校验）
5. P0-3 A — 实验元数据 + 显著性结论

每完成 1 项：跑全量 pytest → 绿 → 在 `docs/SOLID-ROADMAP.zh-CN.md` 对应行标完成日期 + 证据路径。

---

## 2. P2-2 阶段A：argv 命令执行 + 环境变量白名单

**改 `src/policy/rules.py`（`CommandPolicy`）**

- 新增 `check_argv(argv: list[str]) -> PolicyDecision`：
  - 空数组 → 拒绝。
  - 黑名单：对 `" ".join(argv)` 仍套用 `blocked_patterns`（防 `rm -rf /` 等）。
  - `allow_all=True` → 放行。
  - 否则：`argv[0]`（或 `argv[0]` 的 basename）匹配 `allowed_prefixes` 才放行。argv 模式 **不做** 字符串 prefix 模糊匹配，只比首元素，安全性更高。
- 保留原 `check(command)` 不变。

**改 `src/tools/command.py`（`RunCommandTool`）**

- `parameters` 增加可选 `argv`（array of string）；`command` 改为「`command` 或 `argv` 二选一」，描述里写清。
- `execute`：
  - 若提供 `argv`（非空）→ 走 argv 路径：`CommandPolicy.check_argv(argv)` → `asyncio.create_subprocess_exec(*argv, ...)`（**非 shell**）。
  - 否则走原 `command` shell 路径不变。
  - 两路径统一返回结构化字段（见下）。
- 结构化结果：`ToolResult.output` 仍是合并文本；但在 output 末尾或 `error` 中确保可读出 `exit_code` / `timed_out`。**新增**：把 `exit_code`、`duration_ms`、`timed_out` 通过 `event_bus`（若存在）发一条 `command_executed` 事件（含 `mode: shell|argv`）。

**环境变量白名单**

- `CommandConfig`（`src/config/schema.py`）增 `env_whitelist: list[str] = []`（默认空=继承全部，保持兼容）。
- 当 `env_whitelist` 非空：子进程 env 仅保留白名单内变量（+ 必要的 `PATH`/`SYSTEMROOT` 等系统最小集，Windows 注意 `SYSTEMROOT`）。
- `RunCommandTool` 接收并应用该白名单（两路径都生效）。

**配置**

- 新建 `configs/hardened_argv.yaml`：以 `hardened.yaml` 为base，`command.prefer_argv: true`、给一个合理 `env_whitelist`（如 `["PATH", "SYSTEMROOT", "PYTHONPATH"]`）。

**Schema**

- `src/config/schema.py` `CommandConfig` 增 `prefer_argv: bool = False`、`env_whitelist: list[str] = []`。`factory.py` 透传到 `RunCommandTool` 与 `CommandPolicy`。

**测试**（`tests/test_command.py` 或新建）

- argv 放行：`["python", "-c", "print(1)"]` 在白名单 `python` 下 PASS。
- argv 拦截：`allow_all=False` 且 `argv[0]` 不在白名单 → blocked。
- argv 黑名单：`["sh", "-c", "rm -rf /"]` 被 `blocked_patterns` 拦。
- env 白名单：设置白名单后，子进程读不到白名单外的变量。

**验收**
```bash
python -m pytest tests/test_command.py -q --basetemp $env:TEMP\coding-harness-pytest
python scripts/run_eval.py --dataset datasets/repo_tasks.json --configs hardened_argv --runs 1
```
**面试价值**：从「shell + prefix 白名单」升级到「argv 级 + 非 shell 执行 + env 隔离」的安全边界。

---

## 3. P0-1 A：评测集扩到 12 + tag 分组 + oracle

**新增 3 个任务 + fixture**（`datasets/repo_tasks.json`、`tests/fixtures/repos/`）

1. `easy_read_answer`（纯 read+answer）：给定文件，要求 Agent 在 final answer 中回答某事实；裁判 `keywords_in_answer`。
2. `medium_subagent_locate`（subagent 专用）：必须先 `subagent_task` 定位某函数所在文件，再修复；裁判 `multi_assert`（含 `command_success`）。
3. `medium_multi_file_sync`（多文件）：改 2 个文件保持一致（如常量在两处同步）；裁判跨文件 `file_contains` + `command_success`。

**约束**：每个 fixture 小型、纯本地、无网络/第三方依赖；难度配比保持 easy/medium/hard ≥ 各 2。

**report 按 tag 分组**（`src/eval/report.py`）

- 新增「Success Rate by Tag」段：对每个 tag 聚合该 tag 任务的通过率（单 run 即可）。
- 数据来源：`TaskResult.task_id` → 回查数据集 tags；或在 `TaskResult` 增 `tags: list[str]`（runner 填充）更干净。**选后者**：`TaskResult` 加 `tags`，runner 从 task dict 透传。

**oracle 校验脚本（仅 CI，不喂 Agent）**

- 新建 `scripts/check_dataset_oracle.py`：对每个有 `fixture_dir` 的任务，复制 fixture → 应用「参考解」→ 跑该任务 expected 裁判，断言 PASS。
- 参考解放在 `tests/fixtures/repos/<id>/.oracle/`（不复制进 Agent workspace；runner 复制时跳过 `.oracle`）。
- 注意：`EvalRunner._copy_fixture_dir` 需排除 `.oracle` 目录。

**测试**

- `tests/test_runner.py`：tag 分组聚合正确。
- oracle 脚本可作为单独 pytest（`tests/test_dataset_oracle.py`）对 3 个新任务跑通。

**验收**
```bash
python scripts/check_dataset_oracle.py
python scripts/run_eval.py --dataset datasets/repo_tasks.json --configs baseline --runs 1
```
报告含 by-tag 成功率；数据集 12 任务。

---

## 4. P0-2 B：AST 结构化裁判 + flaky 检测

**AST 裁判**（`src/eval/runner.py`）

- 新增 expected 类型 `python_ast_valid`：对目标文件 `ast.parse`，语法错误判 FAIL，返回行号/原因。
- 新增 `python_defines`：检查文件 AST 中定义了某 `function`/`class` 名（比 `file_contains` 关键词更鲁棒）。
- 二者都提供 `_explain_*` 版本（返回 `(bool, list[str])`），并接入 `_explain_expected` 分发。

**flaky 检测**（`src/eval/report.py` 或 `metrics.py`）

- 重复 run 模式下：对每个 task 统计跨 run 的 pass 次数；若 `0 < passes < runs` → 标 `unstable`。
- 报告新增「Unstable Tasks」段，列出 task_id + `passes/runs`。

**测试**

- `tests/test_runner.py`：`python_ast_valid` 正反例、`python_defines` 正反例。
- `tests/test_runner.py`：repeated metrics 下 unstable 标记正确（构造一个 2/3 pass 的假数据）。

**验收**
```bash
python -m pytest tests/test_runner.py -q --basetemp $env:TEMP\coding-harness-pytest
```

---

## 5. P1-1 B：step 显式 tool 绑定 + 结构化 replan（+ 修 schema_ok）

**改 `src/runtime/planner.py`**

- `PlanStep` 增 `suggested_tools: list[str] = []`。
- `SimplePlanner.create_plan`：为每步填 `suggested_tools`（inspect 步→`read_file`/`list_dir`/`subagent_task`；apply 步→`write_file`/`search_replace`/`edit_file`；verify 步→`run_command`）。
- `advance_after_tools`：改为 **优先用 `suggested_tools` 交集** 判断推进，title 关键词匹配作为回退（保留兼容）。
- `maybe_replan`：从「标题加后缀」升级为「改写当前 step 的 title 为更具体的下一步」（仍限一次、不增删步数、不调 LLM）。例如 verify 步失败 → title 改为 `Re-run verification after fixing the previous error`。
- `to_dict()` / `to_prompt_text()` 包含 `suggested_tools`（prompt 里可简短列出）。

**修 `schema_ok` 弱校验**（`src/tools/subagent.py`，A 批次遗留瑕疵）

- `_parse_final_answer` 的「findings 为空时用 summary 回填」改为：回填前先记录 `findings_provided: bool`；`_validate_child_schema` 用 `findings_provided`（真实是否提供）而非回填后的值判定。
- 即：summary 非空但模型没给 findings → `schema_ok=False`。

**测试**

- `tests/test_planner.py`：step 含 `suggested_tools`；`advance_after_tools` 用 suggested_tools 推进。
- `tests/test_planner_loop_sync.py`：replan 后 title 被实质改写（不只是后缀）。
- `tests/test_subagent.py`：模型只给 summary、无 findings → `schema_ok=False`。

**验收 eval**（API，可选但建议）
```bash
python scripts/run_eval.py --dataset datasets/repo_tasks.json --configs baseline plan_act_permissive --runs 3
```
- 对比 A 批次的 `baseline_vs_plan_act_permissive_real.md`，看 step 绑定后是否更稳；写入 `reports/examples/`（新文件名注明 v2）。

---

## 6. P0-3 A：实验元数据 + 显著性结论

**实验元数据**（`scripts/run_eval.py` + `src/eval/report.py`）

- 报告头部新增「Run Metadata」段：
  - `git rev-parse --short HEAD`（若非 git 仓库则标 `n/a`，不报错）。
  - 每个 config 的 `model`（从 config 读）。
  - config 文件内容的 hash（如 `sha256` 前 8 位），便于复现。
  - 时间戳、`--runs` 值。

**显著性一句话**（`src/eval/report.py`）

- 在 Bootstrap 段后追加一句自动结论：
  - 若 baseline 与对照的 success rate CI **不重叠** → 「差异在 95% bootstrap CI 下不重叠，倾向显著」。
  - 若重叠 → 「CI 重叠，差异可能由方差导致，需更多 run」。
- paired delta CI 行追加注明：「基于首轮配对任务，受单轮方差影响，仅供参考」（修正 A 批次发现的 delta CI=[0,0] 误读风险）。

**测试**

- `tests/test_runner.py`：report 含 Run Metadata 段；CI 重叠/不重叠两种情况各产出对应结论句（构造假 metrics）。

**验收**
```bash
python -m pytest tests/test_runner.py -q --basetemp $env:TEMP\coding-harness-pytest
python scripts/run_eval.py --dataset datasets/repo_tasks.json --compare --runs 3
```
报告含 commit/model/config-hash 与显著性结论句。

---

## 7. 收尾

- 全部完成后：全量 `pytest tests -q` 绿；更新 `docs/SOLID-ROADMAP.zh-CN.md` 各行状态（标 B 层完成）。
- 新增 `docs/changes/SOLID-B-BATCH-CLOSEOUT.zh-CN.md`：实际改动、测试数、eval 报告路径、未做项。
- eval 数字一律 `--runs 3` 并在报告声明 confound 与显著性。

## 8. 不在本批次（保持 defer）

- P1-2 L2 LLM 摘要（CODEX 缺口 2）
- P1-3 多 worker / 递归 / 可写子 Agent（CODEX 缺口 3–4）
- P2-1 真 SSE + cancel token（P2-1 C 层）
- 外部 benchmark 接入（P0-1 C 层）

## 9. 给 Composer 的一句话起点

> 按 `docs/SOLID-B-BATCH-EXECUTION.zh-CN.md` 顺序执行 B 批次 5 项。决策已锁定（run_command 双模式 argv opt-in、env 白名单、数据集扩到 12）。每项做完跑全量 pytest 保持绿（基线 112），再跑标注的真实 eval；conda 解释器见文档抬头。注意顺带修复 A 批次遗留的 `schema_ok` 弱校验（见 §5）。
