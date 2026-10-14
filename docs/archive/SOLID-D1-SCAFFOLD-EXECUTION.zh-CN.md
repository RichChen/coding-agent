# Solid D-1 · 防作弊 + SCAFFOLD 扩张 + 重跑 A/B（Composer 自主执行）

> **执行模型**：Composer，**整夜无人值守**。严格按 Phase 顺序，每个 Phase 末尾的「验收闸门」不过就**停下并在报告记原因**，不要带病进入下一 Phase。
> **环境**：`C:\Users\Administrator\.conda\envs\coding-harness\python.exe`；pytest 加 `--basetemp $env:TEMP\coding-harness-pytest`。
> **requests 实例需要的环境**：`set SWEBENCH_REQUESTS_PY=D:\crq\src\coding-harness\.swebench_envs\requests-3362\python.exe`（若缺，先 `python scripts/setup_swebench_envs.py`）。
> **基线**：当前 **143 passed**；改动后须保持全绿再跑 eval。
> **上游**：`docs/changes/SOLID-D1-REWORK-CLOSEOUT.zh-CN.md`（旧干净 A/B：baseline 32.0% vs plan_act 24.0%，CI 重叠无显著）；`docs/CONTAMINATION-NOTES.zh-CN.md`（探针证明强污染，本次为"消除 step/timeout/工具 confound 后"的对照）。

---

## 0. 本任务要回答的问题 + 两条铁律

**问题**：消除 `step_limit / timeout / 缺自测工具` 三个 confound 后，**plan_act 相对 baseline 到底翻不翻盘**（污染已知会压缩区分度，所以这是"在污染天花板下还能否看出 planner 收益"的最后一次干净尝试）。

**铁律 1 — 单变量**：`baseline.yaml` 与 `plan_act_permissive.yaml` 的**工具集 + 预算 + 超时必须一字不差**，唯一差异仍是 `runtime.mode` + `planner.enabled`。
**铁律 2 — 防作弊先行**：Phase 1 给 agent 开了 `run_command`+`write_file`+`edit_file`，它就能篡改/删除测试文件让 FAIL_TO_PASS 假通过。**必须先完成 Phase 0 防作弊（判定前从只读 fixture 恢复受保护测试文件），否则整轮 eval 作废。**

---

## Phase 0 — 防作弊（代码，必须最先做）

当前 `write_file` 已启用，判定在 workspace 跑 pytest = 真实作弊面。修复思路（SWE-bench 标准做法）：**判定前，把受保护的测试文件从只读 fixture 覆盖回 workspace**，agent 对测试的任何改动都被还原。

### 0.1 数据集补 `protected_paths`（离线，不联网）

每个任务的断言 pytest 命令里已含测试文件路径（形如 `sympy/physics/units/tests/test_prefixes.py`）。在 `scripts/build_swebench_lite_subset.py` 加一个**离线 backfill**：

- 新增函数 `_protected_from_assertions(task: dict) -> list[str]`：遍历 `task["expected"]["assertions"]`（或单 assertion），对每条 `command` 用正则 `r"[\w./-]+\.py"` 抽取所有 `.py` token，去重、归一化 `\\`→`/`，返回列表。`-k`/`set ...` 不含 `.py`，不会误抓。
- 新增 CLI 模式 `--refresh-protected`：加载 `datasets/swebench_lite_tasks.json`，对每个 `id.startswith("swebench_")` 的任务写入 `task["protected_paths"] = _protected_from_assertions(task)`，回写文件并打印每任务抓到的数量。
- 同时在 `make_task_entry()` 的返回 dict 里加 `"protected_paths": _test_files_from_patch(row["test_patch"])`（保证未来新建实例也带此字段；`_test_files_from_patch` 已存在）。

运行：
```bash
python scripts/build_swebench_lite_subset.py --refresh-protected
```
自检：`datasets/swebench_lite_tasks.json` 每个 swebench 任务都有非空 `protected_paths`，且路径都以测试文件结尾。例如 24909 应含 `sympy/physics/units/tests/test_prefixes.py`。

### 0.2 runner 判定前恢复受保护文件

`src/eval/runner.py`：

- 新增静态方法：
```python
@staticmethod
def _restore_protected_paths(workspace: Path, fixture_dir, task: dict) -> None:
    protected = task.get("protected_paths") or []
    if not protected:
        return
    fixture = Path(fixture_dir)
    if not fixture.is_absolute():
        fixture = Path.cwd() / fixture
    for rel in protected:
        src = fixture / rel
        if not src.exists():
            continue
        dst = workspace / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
```
- 在 `_run_task()` 中，**在 `agent.run(...)` 之后、判定块（`_explain_expected` / `judge_fn`）之前**插入：
```python
if fixture_dir:
    self._restore_protected_paths(workspace, fixture_dir, task)
```
（`fixture_dir` 变量已在该函数上文取到。`shutil` 已 import。）

> 语义：fixture 内的测试文件是 build 时应用过 test_patch 的"权威版本"；恢复它即把 agent 对测试的任何篡改/删除还原，再判定。源码（被改文件）不动，仍由 agent 的修复决定通过与否。

### 0.3 单测

`tests/test_runner.py` 新增 `test_restore_protected_paths_overwrites_tampered_test`：
- 临时建 workspace 与 fixture；fixture 放 `pkg/tests/test_x.py` 内容 `assert_real_behavior`；workspace 同路径放被篡改内容 `def test_x():\n    assert True`。
- task = `{"protected_paths": ["pkg/tests/test_x.py"]}`，调 `EvalRunner._restore_protected_paths(workspace, fixture, task)`。
- 断言 workspace 文件内容已恢复为 fixture 版本。
- 再加一例：`protected_paths` 缺失/为空时是 no-op，不抛错。

### ✅ Phase 0 验收闸门
- [ ] `python scripts/build_swebench_lite_subset.py --refresh-protected` 成功，10 任务均有非空 `protected_paths`。
- [ ] `python -m pytest tests -q --basetemp $env:TEMP\coding-harness-pytest` → **全绿（≥145 passed**：143 + 新增 2 例）。
- [ ] oracle 仍过：`set SWEBENCH_REQUESTS_PY=...` 后 `python scripts/check_dataset_oracle.py --dataset datasets/swebench_lite_tasks.json` → All PASS。

### 0.4 代码快照（用户要求"做完保存一份代码"）
Phase 0 全绿后，提交一个 checkpoint commit（**仅此一次，在扩 scaffold 之前**）：
```bash
git add -A
git commit -m "feat(eval): anti-cheat — restore protected test files from fixture before judging"
```
（不 push。若 git 不可用则跳过并在报告注明，但务必保证 Phase 0 改动已落盘。）

---

## Phase 1 — SCAFFOLD 扩张（配置 + 接线，单变量）

### 1.1 `run_command` 超时 config 化（S2）
- `src/config/schema.py` 的 `CommandConfig` 增加字段：`timeout_seconds: int = 30`。
- `src/harness/factory.py` 构造 `RunCommandTool` 处（当前未传 timeout），改为：
```python
RunCommandTool(
    command_policy=cmd_policy,
    timeout_seconds=cmd_cfg.get("timeout_seconds", 30),
    env_whitelist=cmd_cfg.get("env_whitelist", []),
    prefer_argv=cmd_cfg.get("prefer_argv", False),
)
```

### 1.2 两个 config 同步改（S1+S2+S4，**改动必须完全一致**）

对 **`configs/baseline.yaml`** 与 **`configs/plan_act_permissive.yaml`** 施加**相同**改动：

| 位置 | 原值 | 新值 |
|------|------|------|
| `runtime.max_steps` | 30 | **40** |
| `runtime.step_timeout_seconds` | 120 | **240** |
| `runtime.total_timeout_seconds` | 600 | **1200** |
| `policy.command` 下 | （无 timeout 字段） | 新增 `timeout_seconds: 180` |
| `tools.enabled` | `[read_file, write_file, list_dir]` | 增加 `run_command`、`edit_file` |

> **成本说明（定稿口径）**：四个旋钮里**只有 `max_steps` 驱动 token 消耗**（≈线性）；两个 timeout 翻倍只放宽墙钟、几乎不增 LLM 调用，`command.timeout_seconds` 是子进程时长。REWORK 实测平均才 ~22 步（未撞 30 墙），故 `max_steps` 取 **40**（为自测循环留余量，token 最坏 +33%）而非 50。配合 Phase 2 的 `--runs 3`，整轮 token 相对上次 runs=5 大致持平或更省。

`plan_act_permissive.yaml` 保留其 `runtime.mode: plan_act` 与 `runtime.planner.enabled: true`；`baseline.yaml` 不加这两项。**除 mode/planner 外两文件其余必须逐字相同**（diff 校验：除 `mode:` 行与 `planner:` 块外无差异）。

### ✅ Phase 1 验收闸门
- [ ] `python -m pytest tests -q --basetemp $env:TEMP\coding-harness-pytest` → **全绿**（新增 schema 字段不应破坏现有测试；若 `tests/` 有 config 快照断言则同步更新并说明）。
- [ ] 烟测工具已注册：跑 1 个任务的单跑确认 `run_command`/`edit_file` 可用、agent 能在 workspace 跑 pytest：
```bash
set SWEBENCH_REQUESTS_PY=D:\crq\src\coding-harness\.swebench_envs\requests-3362\python.exe
python scripts/run_eval.py --dataset datasets/swebench_lite_tasks.json --configs baseline --runs 1
```
确认 trace 中出现 `command_executed` 事件且无"tool not found"。**若烟测崩在 harness 层（非 agent 解题失败），停下修复后再进 Phase 2。**

---

## Phase 2 — 重跑干净 A/B（核心产出）

```bash
set SWEBENCH_REQUESTS_PY=D:\crq\src\coding-harness\.swebench_envs\requests-3362\python.exe
python scripts/run_eval.py ^
  --dataset datasets/swebench_lite_tasks.json ^
  --configs baseline plan_act_permissive ^
  --runs 3
```
（如脚本支持 `--cost-per-1k <rate>`，带上以记录成本；rate 未知则省略。）

**runs 与时长**：定稿用 **`--runs 3`**（省 token + 大概率整夜跑完；对"成功率是否抬升 / 失败结构是否变 / planner 翻不翻盘"三个定性问题足够，CI 略宽于 runs=5 但可与 REWORK 的 runs=5 做均值对比）。预算 600→1200s + 自测会让单轮比上次 6.8h 略久，runs=3 预计整轮约 5–8h。

**监控/容错**：
- 若日志出现连续 `HTTP 402 / Insufficient Balance`：这是计费余额事件，**记录发生在第几轮**，让报告的异常轮检测把坏轮剔除（`src/eval/metrics.py` 已有 `is_degenerate_run`）。不要把 402 坏轮当能力结论。
- 报告路径形如 `reports/report_<时间戳>.md`（+ `.csv`），自动生成。

### ✅ Phase 2 验收闸门
- [ ] 产出新报告，含 mean/std、bootstrap 95% CI、paired delta、显著性一句话、Per-Task Pass Matrix。
- [ ] 若有 402/degenerate 轮，报告的 `Anomalous Runs` 段已剔除且统计仅基于有效轮。

---

## Phase 3 — 收尾文档

新增 `docs/changes/SOLID-D1-SCAFFOLD-CLOSEOUT.zh-CN.md`，写清：

1. **Phase 0 防作弊**：改了哪些文件、protected_paths 如何生成、新增测试、是否做了 checkpoint commit。
2. **Phase 1 scaffold**：两 config 的最终预算/工具/超时（贴关键值），确认单变量（除 mode/planner 外逐字一致）。
3. **Phase 2 结果**（对照三连，这是用户最关心的）：
   - 新 baseline vs plan_act_permissive：成功率 mean/std、CI、显著性。
   - **与历史对比**：① 绝对成功率是否随预算+自测明显抬升（vs REWORK baseline 32% / plan_act 24%）；② 失败结构是否从"撞预算墙/step_limit"转为"真·能力失败"（看 failure_reason 分布）；③ **消除 confound 后 planner 到底翻不翻盘**。
   - 若仍无显著差异，结合 `CONTAMINATION-NOTES` 解释（区分度被污染压缩）。
4. **成本**：token 总量 / 估算 $（若记了）。
5. 更新 `docs/SOLID-ROADMAP.zh-CN.md`：D-1 行补"scaffold 扩张 + 防作弊 + 重跑"标记 + 新报告路径。

---

## 边界 / 不做
- 不接 Docker / SWE-bench-Live（仍属未来工作）。
- 不改 judge/runner 的核心契约（除 Phase 0 的 restore 钩子）；不改数据集实例集合（仅加 `protected_paths` 字段）。
- 不为"好看的数字"再加任务或放宽判定；单变量纪律高于一切。
- gold `patch` 绝不进 agent 可见 workspace（仍只在 `.oracle/`，runner 已跳过复制）。

## 给 Composer 的一句话起点
> 按本文件四个 Phase 顺序执行，**不可跳过 Phase 0 防作弊**（先在 `build_swebench_lite_subset.py` 加 `--refresh-protected` 离线回填 `protected_paths`、在 `src/eval/runner.py` 判定前加 `_restore_protected_paths` 从只读 fixture 恢复测试文件、加单测，pytest 全绿后 git commit 一个 checkpoint）。再做 Phase 1：`CommandConfig` 加 `timeout_seconds` 并经 factory 透传，两个 config 同步把 max_steps→40/step_timeout→240/total_timeout→1200/command.timeout_seconds→180、`tools.enabled` 加 `run_command`+`edit_file`，**除 mode/planner 外两文件逐字一致**；pytest 全绿 + 单任务烟测确认工具可用。再做 Phase 2：`set SWEBENCH_REQUESTS_PY=...` 后 `run_eval --configs baseline plan_act_permissive --runs 3`，遇 402 记录坏轮。最后 Phase 3 写 `SOLID-D1-SCAFFOLD-CLOSEOUT.zh-CN.md` + 更新 ROADMAP，重点回答"消除 confound 后 planner 翻不翻盘"。每个 Phase 验收闸门不过就停下记原因。
