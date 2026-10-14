# Solid D-1 · 返工与重跑（Composer 2.5 用）

> **执行模型**：Composer 2.5（机械实现 + 重跑，与 A/B/C 同性质）。
> **缘由**：D-1 打磨（`SOLID-D1-POLISH-CLOSEOUT.zh-CN.md`）落地了 10 任务/3 repo，但复核发现三个必须修的问题（详见下），且 A/B 因 402 余额耗尽被污染。**余额已恢复，可重跑。**
> **上游**：`docs/SOLID-D1-POLISH-EXECUTION.zh-CN.md`、`docs/SOLID-ROADMAP.zh-CN.md`。
> **环境**：`C:\Users\Administrator\.conda\envs\coding-harness\python.exe`；测试加 `--basetemp $env:TEMP\coding-harness-pytest`。
> **基线**：当前 **139 passed**；每项改动后保持全绿。
> **强依赖**：本文 §3 重跑**必须在 `SOLID-D2-CLOSEOUT-EXECUTION.zh-CN.md` §5「异常轮检测」完成之后**进行，否则若再遇 provider 故障会再次污染结论。

---

## 0. 三个待修问题（复核确认）

| 编号 | 问题 | 证据 | 处理 |
|------|------|------|------|
| **R1** | A/B 结论被 402 污染、方向错误 | `report_20260625T180202.md`：plan_act run3~5 = `1 步/440ms/0%`，却算出“倾向显著” | 先上异常轮检测（D-2 §5）→ 重跑 |
| **R2** | requests-3362 断言硬编码绝对路径 | 数据集第 254/259 行 `"D:\crq\...\.tmp\swebench_oracle_py39\python.exe"` | **不弃用，改可移植**（§1） |
| **R3** | sympy 题面泄露 gold 解法 | 24152 description 含 “I thus propose the following code fix” + 四行 diff；baseline 5/5 全过 | **数据清洗**：description 去解法（§2） |

> 真实可用结论（仅 run1+run2）：baseline 与 plan_act **都是 30%**，无差异。当前报告“倾向显著”须作废。

---

## 1. R2：requests-3362 改可移植（不弃用）

### 1.1 根因

- 断言用 `subprocess.run(cmd, shell=True, cwd=workspace)`，命令里裸 `python` = 当前 conda env（现代 Python）。
- requests-3362（2016 年 PR，requests 2.10 + 旧 urllib3）在现代 env 跑不通，所以 D-1 把解释器**写死**成 `.tmp\swebench_oracle_py39\python.exe`。
- `.tmp` 是临时目录（随时被清理/`git clean`），且绝对路径不可移植 → 定时炸弹。

### 1.2 方案：环境变量占位 + 可重建脚本（数据集零绝对路径）

**核心**：把“需要哪个解释器”从数据集 JSON 移到**环境变量**，并提供脚本在任意机器一键重建该解释器环境。

1. **数据集**：`swebench_psf__requests-3362` 两条断言命令把硬编码路径替换为环境变量引用：
   - 改为：`set PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 && %SWEBENCH_REQUESTS_PY% -m pytest -q tests/test_requests.py::...`
   - JSON 中**不得**再出现任何 `D:\`、`C:\Users`、`.tmp` 字样（修完用 grep 自检）。
   - 若 `%SWEBENCH_REQUESTS_PY%` 未设置，命令会因变量为空而失败——这是预期的“未初始化”信号（见 §1.3 校验）。

2. **重建脚本** `scripts/setup_swebench_envs.py`（新建）：
   - 为 requests-3362 在**项目内固定、git-ignored 的目录** `.swebench_envs/requests-3362/` 建 py39 环境并按官方 specs 装好依赖（复用 `build_swebench_lite_subset.py` 的 `_create_python_env` / `_install_from_specs`，**非 editable** 安装，源用该 fixture 或重新下载 base_commit）。
   - **已核实**：现有 `.tmp\swebench_oracle_py39` 是一个 **160.9 MB 的独立 Python 3.9.25 安装**（有 `conda-meta`、无 `pyvenv.cfg`），不是普通 venv。因此重建走 **`conda create -p .swebench_envs/requests-3362 python=3.9`**（即 `_create_python_env` 的 conda 兜底分支），**不要**用 `python -m venv`；160MB 量级也是必须 git-ignore 的硬理由。
   - 可选优化：若 `.tmp\swebench_oracle_py39` 仍存在且可用，脚本可一次性把它迁移/复制到 `.swebench_envs/`（省一次重装），但**默认路径必须能从零 conda 重建**，不得依赖 `.tmp` 存在。
   - 打印一行可直接执行的设置命令，例如：
     `set SWEBENCH_REQUESTS_PY=D:\crq\src\coding-harness\.swebench_envs\requests-3362\Scripts\python.exe`
   - 脚本幂等：已存在且可用则跳过重建。
   - 解释器须能 import requests（指向 fixture 源或自带安装），保证 `cwd=workspace` 下 `pytest tests/...` 能跑。

3. **`.gitignore`**：加入 `.swebench_envs/`（venv 不进 git，避免体积/不可重定位问题）。

4. **fixture `SETUP.md`** 与 **CLOSEOUT**：注明跑 requests 任务前需先 `python scripts/setup_swebench_envs.py` 并 set 环境变量。

> 选型理由：venv 不可跨机重定位、editable install 的 `.pth` 绑定构建路径，所以**不把 venv 塞进 fixture/git**；改用“数据集只存变量名 + 本机可重建 env”，这是 CI 里 toolchain-via-env 的标准做法，数据集本身彻底可移植。

### 1.3 校验

- `python scripts/setup_swebench_envs.py` → 打印 set 命令；执行该 set 后：
- `python scripts/check_dataset_oracle.py --dataset datasets/swebench_lite_tasks.json` → requests-3362 仍 PASS（oracle 用环境变量解释器跑通）。
- grep 数据集确认无绝对路径：

```bash
rg "D:\\\\|C:\\\\Users|\.tmp|swebench_oracle_py39" datasets/swebench_lite_tasks.json
```
期望**零命中**。

---

## 2. R3：sympy 题面泄露 gold 解法 → 数据清洗

### 2.1 问题

部分 SWE-bench 原始 `problem_statement` 由 issue 作者**自带修复方案**（最典型 `sympy__sympy-24152`：正文 “### Code Fix / I thus propose the following code fix …” + 待改四行）。B2 保留完整描述时把解法一并喂给 Agent → baseline 在这些任务上 5/5（泄题），**区分度作废**。这不是 SWE-bench 选错实例，而是**任务描述清洗没做**。

### 2.2 方案：在生成期清洗（可复现，非手改 JSON）

在 `scripts/build_swebench_lite_subset.py` 的 `make_task_entry()` 增加 `_sanitize_problem(text) -> str`，对 `problem_statement` 做**解法截断**后再写入 description：

1. **解法信号词**（大小写不敏感）出现则**从该处截断**，只保留之前的“现象 + 复现 + 期望/traceback”：
   - `the following code fix`、`I propose`、`I thus propose`、`proposed fix`、`here is the fix`、`the fix is`、`### Code Fix`、`# Fix`、`I have marked the` … （维护成一个 `PATCH_HINT_MARKERS` 列表，便于扩展）。
2. **保留**问题标题、复现代码块、错误 traceback、期望行为（这些在信号词之前，不动）。
3. 截断后若描述 < 80 字符（说明信号词出现太早、误伤），则**回退为不截断**并在 build 日志打印 `WARN: sanitize too aggressive for <id>`，交人工复核。
4. 仍保留 `Do not use .oracle files and do not modify tests.` 收尾句。

> 不做“删代码块”式清洗：复现代码也在代码块里，无法可靠区分，只做“信号词截断”这种保守、可解释的规则。

### 2.3 重建与影响

- 用清洗后的逻辑**重新生成 `datasets/swebench_lite_tasks.json` 的 description**（实例集合、fixture、断言不变；若顺带重建整套子集，须保持现有 10 实例 ID 不丢）。
- 重新过 oracle（oracle 只验 gold patch，不受 description 影响，应仍 10/10 PASS）。
- **预期**：24152/24213 等泄题任务 baseline 成功率应**下降**（答案没了，难度恢复）——这正是目的。重跑后在 CLOSEOUT 对比清洗前后 baseline。
- 抽查：`sympy__sympy-24152` 的 description 不再包含 `propose` / `code fix` / 待改 diff。

---

## 3. R1：重跑干净 A/B（依赖 D-2 §5 异常轮检测）

**前置**（全部满足才重跑）：

- [ ] D-2 §5 异常轮检测已合入并测试通过（402 轮会被自动剔除、显著性可 withheld）。
- [ ] R2 完成：`setup_swebench_envs.py` 跑过、`SWEBENCH_REQUESTS_PY` 已 set、数据集无绝对路径。
- [ ] R3 完成：description 已清洗、oracle 10/10 PASS。
- [ ] 全量 `pytest tests -q` 绿（基线 139 + 新增异常轮测试）。

**重跑命令**（与上次同口径，runs=5）：

```bash
# 先确保 requests 解释器环境变量已设置（见 §1.2）
python scripts/run_eval.py --dataset datasets/swebench_lite_tasks.json --configs baseline plan_act_permissive --runs 5
```

**验收**：

- 新报告**无异常轮污染**：若仍出现整轮坍塌，应进「Anomalous Runs」段并从显著性剔除；否则 5 轮全有效。
- 报告给出**有效轮**下的 baseline vs plan_act_permissive：成功率 mean/std、bootstrap CI、显著性结论（重叠则如实写“无显著差异”，不再误报“倾向显著”）。
- pass matrix 反映清洗后的真实难度（泄题任务 baseline 不再恒过）。

---

## 4. 完成后

- 更新 `docs/SOLID-ROADMAP.zh-CN.md`：D-1 行补「返工完成」+ 新报告路径。
- 新增 `docs/changes/SOLID-D1-REWORK-CLOSEOUT.zh-CN.md`：
  - R2：requests 可移植方案、`setup_swebench_envs.py`、数据集无绝对路径自检结果。
  - R3：清洗规则、受影响任务、清洗前后 baseline 对比。
  - R1：干净 A/B 结果（有效轮、CI、显著性结论），与被污染旧报告的差异说明。
- 修正/作废旧结论：在 `SOLID-D1-POLISH-CLOSEOUT.zh-CN.md` 顶部加注「§4.2 的‘倾向显著’因 402 污染作废，以 REWORK 报告为准」。
- 把干净的区分度 + A/B 数字同步给 D-2（演示脚本 / INTERVIEW-DEMO 回填）。

## 5. 不做 / 边界

- 不弃用 requests-3362（按用户要求改可移植）。
- 不改 eval/judge 核心契约；R2 只动数据集 command 与新增 setup 脚本，R3 只动 description 生成。
- 不把 venv / gold patch 放进 git 或 Agent 可见 workspace。
- 实例集合维持现有 10 个（3 repo）；如清洗导致某任务无效再个案讨论，不在本文擅自增删。

## 6. 给 Composer 的一句话起点

> 按 `docs/SOLID-D1-REWORK-EXECUTION.zh-CN.md` 返工 D-1。顺序：①先确认 `SOLID-D2-CLOSEOUT-EXECUTION.zh-CN.md` §5 异常轮检测已完成；②R2 把 requests-3362 断言里的 `.tmp` 绝对路径改成 `%SWEBENCH_REQUESTS_PY%` 环境变量，新增 `scripts/setup_swebench_envs.py` 可重建该 py39 env，`.gitignore` 加 `.swebench_envs/`，数据集 grep 零绝对路径；③R3 在 `build_swebench_lite_subset.py` 的 `make_task_entry` 加 `_sanitize_problem` 按解法信号词截断 description（保守、<80 字符回退），重生成 description 并保持 10 实例不丢，oracle 仍 10/10；④保持 139+ 全绿后，set 好 `SWEBENCH_REQUESTS_PY`，重跑 `run_eval ... --configs baseline plan_act_permissive --runs 5`，出**无 402 污染**的干净 A/B（重叠就如实写无显著差异）。完成后更新 ROADMAP、写 `SOLID-D1-REWORK-CLOSEOUT.zh-CN.md`，并给旧 POLISH-CLOSEOUT 的“倾向显著”加作废注记。conda 解释器见抬头。
