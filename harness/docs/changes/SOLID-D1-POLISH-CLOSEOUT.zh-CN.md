# SOLID D1 打磨收尾（SWE-bench Lite 子集）

> **作废注记（2026-06-26）**：§4.2 的「倾向显著」结论因 `plan_act_permissive` run3~5 遭遇 HTTP 402 余额耗尽被污染，**已作废**。请以 `docs/changes/SOLID-D1-REWORK-CLOSEOUT.zh-CN.md` 与返工后新报告为准。

日期：2026-06-26  
执行文档：`docs/SOLID-D1-POLISH-EXECUTION.zh-CN.md`

---

## 1) 本次打磨目标与结果

- A1（官方环境规格）: 已在 `scripts/build_swebench_lite_subset.py` 接入 SWE-bench 官方 per-instance specs（`swebench.harness.constants`），按 `repo+version` 读取 Python 版本、依赖与安装命令进行环境构建与验证。
- A2（扩样本 + 多 run）: `datasets/swebench_lite_tasks.json` 当前为 10 任务，覆盖 3 个 repo（sympy/flask/requests）；`baseline vs plan_act_permissive` 已完成 `runs=5`。
- B1（PASS_TO_PASS）: `--pass-subset-limit` 默认已提升到 10。
- B2（problem 截断）: 已去掉 320 截断，任务描述保留完整问题信息。
- B3（体积评估）: 已完成当前数据集的 fixture 体积统计（见第 5 节）。

---

## 2) 关键实现变更

### 2.1 官方 specs 环境安装链路（A1）

文件：`scripts/build_swebench_lite_subset.py`

- 新增 `SwebenchPyConstants`，从已安装的 SWE-bench 常量模块加载：
  - `MAP_REPO_VERSION_TO_SPECS_PY`
  - `MAP_REPO_TO_REQS_PATHS`
  - `MAP_REPO_TO_INSTALL_PY`
- 新增 `_create_python_env()`：
  - 优先复用 base python（版本一致）
  - 支持 `py -<version>` launcher
  - 兜底 `conda create -p <env> python=<X.Y>`
- 新增 `_install_from_specs()`：
  - 按 specs 安装 `packages` / `pip_packages` / `pre_install` / `install`
  - 处理 requirements 链式 `-r` 展开（`_fetch_flattened_requirements`）
- 验证流程保持 SWE-bench 标准序列：
  1. `test_patch` 后 FAIL_TO_PASS 先失败  
  2. 应用 gold patch  
  3. FAIL_TO_PASS 转通过  
  4. PASS_TO_PASS 子集通过  

### 2.2 任务生成策略（B1/B2）

- `make_task_entry()` 中不再 `problem[:320]`，改为完整 `problem_statement`。
- 断言命令继续通过 `_pytest_command_str()` 生成，默认注入 `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`。
- `--pass-subset-limit` 默认值提升到 10。

---

## 3) 最终数据集（A2）

文件：`datasets/swebench_lite_tasks.json`

- 任务数：10（满足 `>=8`）
- repo 覆盖：3（满足 `>=3`）
  - sympy: 8
  - flask: 1
  - requests: 1
- 最终实例 ID：
  - `swebench_sympy__sympy-24909`
  - `swebench_pallets__flask-4992`
  - `swebench_sympy__sympy-24213`
  - `swebench_sympy__sympy-24152`
  - `swebench_sympy__sympy-24102`
  - `swebench_sympy__sympy-24066`
  - `swebench_sympy__sympy-23262`
  - `swebench_sympy__sympy-23191`
  - `swebench_sympy__sympy-23117`
  - `swebench_psf__requests-3362`

---

## 4) 验证与评测结果

### 4.1 Oracle / 测试

- Oracle：
  - 命令：`python scripts/check_dataset_oracle.py --dataset datasets/swebench_lite_tasks.json`
  - 结果：`Checked 10 oracle task(s). All oracle solutions PASS.`
- 全量 pytest：
  - 命令：`python -m pytest tests -q --basetemp $env:TEMP\coding-harness-pytest`
  - 结果：`139 passed in 7.80s`

### 4.2 runs>=5 A/B（baseline vs plan_act_permissive）

- 报告：`reports/report_20260625T180202.md`
- 数据集：`datasets/swebench_lite_tasks.json`
- runs: 5

核心统计（来自报告）：

- baseline
  - Success Rate mean/std: `30.0% / 0.0`
  - Avg Steps mean/std: `20.6 / 3.2`
  - Avg Time mean/std: `204104ms / 47228`
- plan_act_permissive
  - Success Rate mean/std: `12.0% / 16.4`
  - Avg Steps mean/std: `7.3 / 8.6`
  - Avg Time mean/std: `55431ms / 79721`
- Bootstrap 95% CI
  - baseline success rate: `[30.0%, 30.0%]`
  - plan_act_permissive success rate: `[0.0%, 24.0%]`
  - delta（plan_act_permissive - baseline，首轮配对）: `[+0.0%, +0.0%]`
  - 报告结论：`Significance: 差异在 95% bootstrap CI 下不重叠，倾向显著。`

重要说明（实验边界）：

- 在 `plan_act_permissive` 的 run3~run5 期间，日志出现连续 `HTTP 402 Payment Required / Insufficient Balance`，导致后 3 轮几乎全失败（0/10）。
- 因此本轮 A/B 结论受到外部计费余额事件影响；若用于对外宣讲，建议在余额恢复后复跑同命令以获得无该 confound 的对照结果。

---

## 5) Fixture 体积评估（B3）

按当前 10 任务数据集统计：

- 总体积：`278,971,973 bytes`（约 `266.05 MB`）
- 体积分布：
  - sympy 8 个 fixture 合计约 262MB（主要体积来源）
  - requests 1 个约 2.65MB
  - flask 1 个约 0.70MB

结论：

- 扩样本后体积已明显增长（>250MB），后续若继续扩容，优先考虑对 sympy 类 fixture 做更细粒度裁剪策略，并保持 oracle 全过后再落库。

