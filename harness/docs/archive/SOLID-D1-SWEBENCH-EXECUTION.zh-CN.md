# Solid D-1 · SWE-bench Lite 子集接入（Codex 5.3 用）

> **执行模型**：Codex 5.3（探索性 + 环境调试密集，建议人工盯进度）。  
> **与 D-2 的关系**：本文只做 SWE-bench 接入；其余收尾项（失败 taxonomy / 多模型矩阵 / 演示脚本 / 文档收口）见 `docs/SOLID-D2-CLOSEOUT-EXECUTION.zh-CN.md`（Composer 执行）。两者**可并行**：D-2 用现有 eval 数据即可开工，不必等 D-1。  
> **上游**：`docs/SOLID-ROADMAP.zh-CN.md`、各批次 CLOSEOUT。  
> **环境**：`C:\Users\Administrator\.conda\envs\coding-harness\python.exe`；测试加 `--basetemp $env:TEMP\coding-harness-pytest`。  
> **基线**：当前 **139 passed**；改动后保持全绿，再跑 SWE-bench eval。

---

## 0. 目标与动机

C 批次硬约束：**自造 hard 任务对 deepseek-v4-pro 偏易（16 任务 baseline 仍 93.8%），区分度撑不开**。本任务引入 **5 个左右真实难度的 SWE-bench Lite 实例**，让 baseline 成功率明显低于天花板（期望 30–70%），**根治区分度** + 拿到「接入业界标准 benchmark」的面试亮点。

**不做完整 SWE-bench 复现**（那依赖 Docker + 大仓 + 庞大环境）。只做**轻量本地子集**：复用现有 `fixture_dir` + `command_success` 框架，离线缓存 fixture。

---

## 1. 已核实的背景事实（官方来源）

- SWE-bench Lite：**300 test + 23 dev** 实例，来自 **11 个 Python 仓库**；HF 数据集 `princeton-nlp/SWE-bench_Lite`。
- Lite 已预筛：**单文件编辑、gold patch ≤3 处 hunk、无新建/删除文件、无错误信息检查测试**——天然适配本 harness。
- 实例字段：
  - `instance_id`（`owner__repo-PR号`）、`repo`、`base_commit`
  - `problem_statement`（喂给 Agent 的问题描述）
  - `patch`（gold 解，**绝不喂 Agent**，仅用于 oracle）
  - `test_patch`（测试补丁，需应用后才有 FAIL_TO_PASS 测试）
  - `FAIL_TO_PASS`（JSON 字符串：修复后应由失败转通过的测试）
  - `PASS_TO_PASS`（JSON 字符串：修复前后都应通过的回归测试）
  - `version`、`environment_setup_commit`
- 官方验证示例实例：`sympy__sympy-20590`。

---

## 2. 仓库选型分级（本地可跑性，无 Docker）

| 级别 | 仓库 | 依赖 | 评估 |
|------|------|------|------|
| **T1 首选** | `pallets/flask` | werkzeug/jinja2/click（纯 Python） | 测试小、无编译，**最佳** |
| **T1 首选** | `psf/requests` | urllib3/certifi/idna（纯 Python） | 多数测试离线可跑 |
| **T1** | `pytest-dev/pytest` | 纯 Python 自举 | 轻，但测试偏 meta |
| **T2 可用** | `sympy/sympy` | 仅 mpmath | 仓库大但无编译，锁定小测试文件即可 |
| **T2 可用** | `pylint-dev/pylint` | astroid | 可跑，稍重 |
| **T2** | `django/django` | 大但纯 Python | 部分测试需 settings，中等 |
| **T3 避开** | scikit-learn / matplotlib / astropy / xarray / sphinx | C/Cython、numpy 编译、多 deps | **本地很可能跑不动** |

**选型策略**：优先 `flask` ×2 + `requests` ×2 + `sympy` ×1，凑 **5 个**。每个**必须先过 oracle**（gold patch 应用后 FAIL_TO_PASS 由失败转通过）才纳入。**跑不通立即换，宁少勿多——能稳定跑的 3 个 > 凑数的 10 个。**

---

## 3. 实现步骤

### 步骤 1：筛选脚本（实拉数据集，不靠记忆 ID）

新建 `scripts/select_swebench_instances.py`：

- `pip install datasets`（一次性）。
- `load_dataset("princeton-nlp/SWE-bench_Lite", split="test")`。
- 过滤：`repo in {pallets/flask, psf/requests, sympy/sympy}`；按 `created_at` 取较新的（依赖版本更接近当下，env 更易装）。
- 对每个候选打印：`instance_id`、`repo`、`base_commit`、`version`、`FAIL_TO_PASS`、`PASS_TO_PASS`、`problem_statement` 前 200 字。
- 输出 10–15 个候选供人工/Codex 挑选，**不直接定稿**。

### 步骤 2：逐实例可行性验证（核心，最易踩坑）

对每个候选，在临时目录走一遍：

1. `git clone <repo>` → `git checkout <base_commit>`（或浅克隆指定 commit）。
2. 在 conda env 内 `pip install -e .`（或按 `version` 装依赖）；**装不上 → 弃用换下一个**。
3. 应用 `test_patch`（带来 FAIL_TO_PASS 的测试）。
4. 跑 FAIL_TO_PASS 测试 → 应**失败**（确认 bug 存在）。
5. 应用 `patch`（gold）→ 再跑 FAIL_TO_PASS → 应**通过**；跑 PASS_TO_PASS → 仍通过。
6. 步骤 4–5 都符合 → 该实例**可纳入**；否则弃用。

> 这一步是真正的工作量所在。**每个实例预算有限时间，卡住就跳过**，不要在单个实例上空转。

### 步骤 3：固化为离线 fixture

对通过验证的实例：

- 裁剪仓库为**最小可跑快照**（保留被改文件 + 相关测试 + 必要包结构 + `pyproject/setup`），落到 `tests/fixtures/repos/swebench_<instance_id>/`。
  - 体积控制：单个尽量 < 几 MB；删无关子目录、`.git`、文档、示例。
- **已应用 `test_patch`**（让 FAIL_TO_PASS 测试存在且当前失败），但**不应用 gold patch**（留给 Agent 修）。
- 配 `.oracle/`：放 gold patch 应用后的文件状态（runner 已配置跳过 `.oracle` 复制；`check_dataset_oracle.py` 会用它校验）。
- fixture 内含一份 `SETUP.md`：记录 repo、base_commit、需要的 `pip install` 命令（供 eval 前置）。

### 步骤 4：数据集条目

新建 `datasets/swebench_lite_tasks.json`，每条用现有 schema：

```json
{
  "id": "swebench_flask_<pr>",
  "description": "<problem_statement 精简版，去掉外链/图片>",
  "fixture_dir": "tests/fixtures/repos/swebench_<instance_id>",
  "expected": {
    "type": "multi_assert",
    "assertions": [
      {"type": "command_success", "command": "python -m pytest <FAIL_TO_PASS 测试路径> -q", "timeout": 120},
      {"type": "command_success", "command": "python -m pytest <关键 PASS_TO_PASS 子集> -q", "timeout": 120}
    ]
  },
  "difficulty": "hard",
  "tags": ["swebench", "<repo名>"]
}
```

- FAIL_TO_PASS / PASS_TO_PASS 是 JSON 字符串，解析后取测试 node id 拼成 pytest 命令。
- PASS_TO_PASS 可能很多，只取**有代表性的子集**避免超时。

### 步骤 5：依赖前置说明

- 若某实例需特定依赖版本：在 fixture `SETUP.md` 与任务 `description` 注明。
- eval 前一次性 `pip install`（记录在报告）。**优先选 base_commit 依赖与当前环境兼容的实例**，减少版本地狱。

---

## 4. 测试 / 验收

```bash
# 1. 筛选候选（人工/Codex 挑 5 个）
python scripts/select_swebench_instances.py

# 2. fixture 固化后，gold patch 必过 oracle
python scripts/check_dataset_oracle.py

# 3. 真实 eval（区分度证据）
python scripts/run_eval.py --dataset datasets/swebench_lite_tasks.json \
  --configs baseline plan_act_permissive --runs 3
```

- **目标**：baseline 成功率明显 **< 90%**（恢复区分度）；plan_act 是否更优写入报告。
- 产出 `reports/examples/swebench_lite_real.md`，注明这是**真实难度区分度证据**，并说明纳入了几个实例、各自来源 repo。
- 全量 `pytest tests -q` 仍绿（新 fixture 不被 pytest 收集，`norecursedirs` 已含 `tests/fixtures/repos`）。

---

## 5. 完成后

- 更新 `docs/SOLID-ROADMAP.zh-CN.md`：P0-1 C「外部 benchmark」行从 ⏳ 改 ✅ + 证据路径；§4 第 16 项标完成。
- 新增 `docs/changes/SOLID-D1-SWEBENCH-CLOSEOUT.zh-CN.md`：纳入哪些实例、各自 baseline 表现、弃用了哪些及原因、区分度结论。
- 把最终 baseline 区分度数字同步给 D-2（演示脚本 / INTERVIEW-DEMO 会引用）。

## 6. 边界 / 不做

- 不做完整 SWE-bench 复现、不引 Docker、不追求 300 全集。
- 实例数 **5 个左右即可**；稳定可跑优先于数量。
- 不把 gold `patch` 放进 Agent 可见的 workspace（只进 `.oracle/`）。

## 7. 给 Codex 的一句话起点

> 按 `docs/SOLID-D1-SWEBENCH-EXECUTION.zh-CN.md` 接入 SWE-bench Lite 轻量子集。先跑 `select_swebench_instances.py` 从 `princeton-nlp/SWE-bench_Lite` 实拉候选（限 flask/requests/sympy），逐个做步骤 2 的可行性验证（装不上或 gold patch 跑不通就弃用换下一个，宁少勿多），通过的固化为离线 fixture + `.oracle`，写进 `datasets/swebench_lite_tasks.json`，过 oracle 后跑 baseline×3 区分度 eval。不编造 instance_id/测试名，全部从数据集实取。conda 解释器见抬头；完成后更新 ROADMAP 并写 CLOSEOUT。
