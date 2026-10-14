# Solid D-1 · SWE-bench 子集打磨（Codex 5.3 用）

> **执行模型**：Codex 5.3，**high reasoning**（环境钉扎 + 多实例可行性验证，调试密集，建议人工盯进度）。
> **前置**：D-1 已接入 3 个 sympy 实例（见 `docs/changes/SOLID-D1-SWEBENCH-CLOSEOUT.zh-CN.md`）。本文是对 D-1 的**打磨**，不是重做。
> **上游**：`docs/SOLID-D1-SWEBENCH-EXECUTION.zh-CN.md`、`docs/SOLID-ROADMAP.zh-CN.md`。
> **环境**：构建用 `C:\Users\Administrator\.conda\envs\coding-harness\python.exe`；测试加 `--basetemp $env:TEMP\coding-harness-pytest`。
> **基线**：当前 **139 passed**；改动后保持全绿，再跑 SWE-bench eval。
> **现有脚本**：`scripts/select_swebench_instances.py`、`scripts/build_swebench_lite_subset.py`、`scripts/check_dataset_oracle.py` 已存在，**优先在其上改，不要另起炉灶**。

---

## 0. 为什么要打磨（已核实的弱点）

当前 D-1 产物虽真实，但作为「能跑可信 A/B 的基准」还差一口气。基于对脚本与验证日志的复核，确认以下弱点：

| 编号 | 弱点 | 证据 | 影响 |
|------|------|------|------|
| **A1** | repo 多样性=0，3 个实例全是 sympy | `swebench_lite_validation_log.json`：flask/requests 全弃用 | 难度/结构高度相关，区分度结论偏窄 |
| **A1 根因** | 环境构建不忠实，只做 `pip install -e .` | flask-4992 `url_quote` ImportError、requests-3362 `urllib3` 缺失 = **依赖版本漂移**，非任务不可用 | 本可纳入的实例被误弃 |
| **A2** | n=3、runs=3，噪声淹没信号 | 报告 `11.1% / std 19.2`，24213 为 `P/F/F` | A/B 的 CI 必然重叠，**planner 提升判不出来** |
| **B1** | PASS_TO_PASS 只取 5 个子集 | `build_swebench_lite_subset.py` `pass_subset_limit=5` | 回归判定偏松 |
| **B2** | problem_statement 截断到 320 字符 | `make_task_entry` `problem[:320]` | 丢复现关键信息，**人为拔高难度** |
| **B3** | fixture 各 26~34MB，3 个共 ~95MB 进 git | 实测目录大小 | 扩到 8~10 实例仓库会膨胀到数百 MB |

**打磨目标**：让这套基准能支撑可信的 `baseline vs plan_act_permissive` A/B —— 即 **repo 多样性 ≥3、n ≥8、runs ≥5、有 bootstrap CI 和显著性结论**。

---

## 1. 任务分层与优先级

按"是否阻塞后续可信 A/B"排序。**A 层必做，B 层顺手做，按时间盒推进。**

### A1 —— 环境忠实度：用官方环境规格救回 flask/requests（最高优先）

弃用的 flask/requests 不是任务坏，是 `build_swebench_lite_subset.py` 装环境太朴素。SWE-bench 官方为每个 `repo + version` 提供了精确环境规格（python 版本、pre-install、依赖版本、install 命令），必须用它。

**实现要点**（在 `build_swebench_lite_subset.py` 上改）：

1. `pip install swebench`（一次性），从 `swebench.harness.constants` 取 `MAP_REPO_VERSION_TO_SPECS`（或等价常量），按实例的 `repo` + `version` 拿到：
   - 目标 Python 版本（如 3.9 / 3.11）
   - `pre_install` 命令
   - 钉扎依赖列表（`packages` / `pip_packages` / specified versions）
   - `install` 命令（可能是 `pip install -e .` 或 `pip install -r requirements.txt` 等）
2. 用该规格建 venv 并装依赖，**替换现有"裸 `pip install -e .`"**：
   - 若该规格要求的 Python 版本与 conda base 不一致：优先用 `conda create -n <tmp> python=<X.Y>` 或 `py -<X.Y>`（Windows launcher）建对应版本解释器；**装不出对应 Python 版本才弃用**。
   - 关键：把官方钉扎的依赖版本（尤其 werkzeug / urllib3 / click 等）**先于** `pip install -e .` 装好，避免被新版顶替。
3. 验证流程不变（test_patch → FAIL 先失败 → gold patch → 转通过 → PASS_TO_PASS 子集通过）。

> **若 `swebench` 包接口取规格不顺手**：退而求其次，从实例的 `environment_setup_commit` 对应的 `requirements*.txt` / `setup.py` extras 钉扎依赖；再不行就手动钉扎该 repo 该 version 的关键依赖版本（在脚本里维护一个小 map）。**目标是让至少 flask 或 requests 进来 ≥2 个**，恢复 repo 多样性。

**验收**：纳入实例覆盖 **≥3 个不同 repo**（sympy 之外至少 +2）。

### A2 —— 扩样本到 n≥8、runs≥5（与 A1 同批）

- `select_swebench_instances.py`：`--limit-per-repo` 提到 8~10，多拉候选。
- `build_swebench_lite_subset.py`：`--target-count` 提到 **8**（保留现有 3 个 sympy，新增至 8）。
- **保留现有 3 个 sympy fixture**，不要删了重建（除非 B2/B1 改动要求重生成 description/assertions —— 那就重生成，但实例集合至少含这 3 个）。
- eval 跑 **runs≥5**，且 `baseline` 与 `plan_act_permissive` 都跑，产出含 **bootstrap 95% CI** 与显著性结论的报告。

**验收**：`datasets/swebench_lite_tasks.json` ≥8 任务；eval 报告有 CI 行与显著性结论。

### B2 —— 去 problem_statement 截断（低成本，建议顺手）

`make_task_entry` 把 `problem[:320]` 改为**保留完整 problem_statement**（可去掉外链/图片 markdown，但保留 code-to-reproduce 块与期望输出）。重生成现有 3 个 sympy 任务的 description。

> 注意：description 进 messages 会增加 token。若完整 problem 过长（>4000 字符），保留前 2000 + code block，但**不要**粗暴截到 320。

**验收**：抽查 1 个任务，description 含完整复现信息（不再 `...` 截断在句中）。

### B1 —— PASS_TO_PASS 子集放宽（顺手）

`--pass-subset-limit` 对 hard 任务从 5 提到 **10**（或按 gold patch 改动文件所在测试模块优先抽样）。避免子集太小漏判回归。

**验收**：新建任务的回归断言覆盖 ≥ 现状。

### B3 —— fixture 体积策略（扩样本前先定）

扩到 8 实例前先决定，避免仓库膨胀：

- **首选**：现有 trim 基础上，进一步只保留**被改文件所在子包 + 相关测试 + 包根 `setup/pyproject`**，删其余顶层子包。前提是裁剪后 `pip install -e .` 与目标测试仍可跑（裁剪后必须重过 oracle）。
- **次选**：若裁剪风险高，保持完整 fixture 但在 CLOSEOUT 记录总体积，并评估是否需要 `.gitattributes` / git-lfs（**不强制引 lfs，先记录**）。

**验收**：8 实例总体积有记录；若做了裁剪，裁剪后 oracle 全过。

---

## 2. 不做 / 边界

- 不引 Docker、不追 SWE-bench 300 全集（仍是本地轻量子集）。
- 不把 gold `patch` 放进 Agent 可见 workspace（只进 `.oracle/`）。
- 不为凑数纳入跑不稳的实例：**稳定可复现 > 数量**。若 A1 救援后仍只能凑到 6 个稳定实例，**6 个也可接受**，但必须 ≥3 个 repo。
- 不改 eval/judge/runner 的核心契约；只动数据集与构建脚本。

---

## 3. 测试 / 验收命令

```bash
# 1. 扩候选（多 repo、每 repo 多拉）
C:\Users\Administrator\.conda\envs\coding-harness\python.exe scripts/select_swebench_instances.py --limit-per-repo 8 --output swebench_candidates.jsonl

# 2. 用官方环境规格重建子集（target-count 8）
C:\Users\Administrator\.conda\envs\coding-harness\python.exe scripts/build_swebench_lite_subset.py --target-count 8 --pass-subset-limit 10

# 3. gold patch 必过 oracle（全部实例）
C:\Users\Administrator\.conda\envs\coding-harness\python.exe scripts/check_dataset_oracle.py --dataset datasets/swebench_lite_tasks.json

# 4. 全量测试仍绿
C:\Users\Administrator\.conda\envs\coding-harness\python.exe -m pytest tests -q --basetemp $env:TEMP\coding-harness-pytest

# 5. 可信 A/B：baseline vs plan_act_permissive，runs>=5
C:\Users\Administrator\.conda\envs\coding-harness\python.exe scripts/run_eval.py --dataset datasets/swebench_lite_tasks.json --configs baseline plan_act_permissive --runs 5
```

**通过标准（全部满足才算打磨完成）：**

- [ ] 纳入实例覆盖 **≥3 个不同 repo**（sympy + flask/requests 至少各 1，或其一 ≥2）。
- [ ] `datasets/swebench_lite_tasks.json` **≥8 任务**（如 A1 救援不足则 ≥6 且 ≥3 repo，并在 CLOSEOUT 说明原因）。
- [ ] `check_dataset_oracle.py` 全部 PASS。
- [ ] 全量 `pytest` 仍 **全绿**。
- [ ] eval 报告含 **bootstrap 95% CI** 与 baseline vs plan_act 的**显著性结论**（无论是否显著，都要写明）。
- [ ] description **不再被截到 320**（B2 生效）。

---

## 4. 完成后

- 更新 `docs/SOLID-ROADMAP.zh-CN.md`：D-1 相关行补「打磨完成」标记 + 新证据路径。
- 新增 `docs/changes/SOLID-D1-POLISH-CLOSEOUT.zh-CN.md`：
  - A1 用了什么环境规格方案、救回了哪些 repo/实例、仍弃用哪些及原因。
  - 最终实例清单（repo 分布、n）。
  - baseline vs plan_act_permissive 的 runs≥5 结果（成功率 mean/std、CI、显著性结论、pass matrix）。
  - fixture 总体积与是否裁剪。
- 把新的区分度 + A/B 数字同步给 D-2（演示脚本会引用）。

## 5. 给 Codex 的一句话起点

> 按 `docs/SOLID-D1-POLISH-EXECUTION.zh-CN.md` 打磨现有 SWE-bench 子集。核心是 **A1**：在 `build_swebench_lite_subset.py` 里改用 SWE-bench 官方 per-instance 环境规格（`swebench.harness.constants` 的 `MAP_REPO_VERSION_TO_SPECS`：Python 版本 + 钉扎依赖 + install 命令）来建 venv，把之前因依赖漂移误弃的 flask/requests 救回来，恢复 repo 多样性（≥3 repo）。同时 **A2** 扩到 ≥8 实例、eval 跑 runs≥5 并输出 bootstrap CI 与 baseline vs plan_act 显著性结论；顺手 **B2** 去掉 problem 的 320 截断、**B1** 把 PASS_TO_PASS 子集提到 10、**B3** 评估 fixture 体积。保留现有 3 个 sympy 实例。不编造 instance_id/测试名，全部从数据集实取；装不出对应 Python 版本或 gold 跑不通才弃用（稳定 >数量，但必须 ≥3 repo）。conda 解释器见抬头；完成后过 oracle、保持 139+ 全绿，更新 ROADMAP 并写 POLISH-CLOSEOUT。
