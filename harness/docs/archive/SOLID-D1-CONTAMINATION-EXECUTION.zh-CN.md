# Solid D-1 · 污染方法论落地（Composer 执行）

> **执行模型**：Composer（确定性脚本 + 文档，少量探索）。
> **定位**：D-1 SWE-bench 子集线的**方法论收口**，不是刷分。把「污染」从风险点做成**可量化、可讲的方法论亮点**。
> **上游**：`docs/changes/SOLID-D1-REWORK-CLOSEOUT.zh-CN.md`（干净 A/B：baseline 32.0% vs plan_act 24.0%，CI 重叠**无显著差异**）。
> **环境**：`C:\Users\Administrator\.conda\envs\coding-harness\python.exe`；pytest 加 `--basetemp $env:TEMP\coding-harness-pytest`。
> **基线**：当前 **143 passed**；本任务结束后须保持全绿。
>
> **⚠ 实测修订（2026-06-26，已执行完毕，本节为最终口径）**：探针已实跑，过程暴露并修复了两个测量陷阱，本文档下方部分原始建议（尤其 `max_tokens≈256`、单次调用）**已作废**，以此处为准：
> - **修订①｜非确定性**：`deepseek-v4-pro` 即便 `temperature=0` 也**非确定**（同 prompt 两次答案不同），单次探针在 50%–78% 间晃。→ 必须**每实例重复采样 `--repeats`（用 5）**，按命中频率聚合并报告逐轮波动。
> - **修订②｜推理模型截断**：该模型先消耗 reasoning 预算再吐 `content`，`max_tokens=256` 会截断 6/10 答案并误记为"定位失败"。→ `--max-tokens` 至少 **2048**；空答+`finish_reason=length`/预算耗尽标 **`truncated`**（**不计入分母**），不可记为 `wrong`。
> - **附**：脚本已加 `--from-json`，可从缓存原始数据**零成本重渲染**报告。
> - **稳健结果**：5 次重复下池化 exact **54.2%**、basename-or-better **68.8%**、**7/10** 实例多数票定位 → 强 instance-level 记忆污染。详见 `reports/contamination_probe.md`、`docs/CONTAMINATION-NOTES.zh-CN.md`、`docs/changes/SOLID-D1-CONTAMINATION-CLOSEOUT.zh-CN.md`。

---

## 0. 为什么做这个（动机，必须读）

干净返工后的 A/B（`reports/report_20260626T101113.md`）给出一个**尴尬但真实**的结果：plan_act 相对 baseline **无显著差异**，且任务层面呈现**双峰**——`sympy-24213`、`flask-4992` 恒 5/5，一批 sympy 恒 0/5，中间几乎没有梯度。

这个双峰正是**数据污染的指纹**（"记得的就过、没记的就不会"），强烈暗示：**A/B 区分度可能在数据层就被污染压死了，而不是 harness 没做好。**

因此本任务**不再为污染数据堆 scaffold/预算**（那是亏本买卖），而是用一个**近零成本**的实验把污染**量化**出来，并诚实归档。产出有三：

1. **污染探针实验**（核心）：复刻 *The SWE-Bench Illusion*（arXiv 2506.12286）的文件定位探针，量化本项目这 10 个实例的 instance-level 记忆程度。
2. **`docs/CONTAMINATION-NOTES.zh-CN.md`**：方法论存档 + 诚实标注 + 未来工作（治本路径）。
3. **ROADMAP/报告标注**：声明绝对成功率不作能力指标。

---

## 1. 已核实的背景事实（实现前提，勿改）

- 数据集：`datasets/swebench_lite_tasks.json`，**10 个任务**，3 repo（sympy×8 / flask×1 / requests×1）。任务 `id` 形如 `swebench_<owner>__<repo>-<pr>`。
- 每个任务有 `fixture_dir`（如 `tests/fixtures/repos/swebench_sympy__sympy-24909`）。
- **gold 改动文件 = 该 fixture 下 `.oracle/` 子树里唯一的 `.py`**（SWE-bench Lite 单文件编辑，已逐一核实 10 个都成立）。例：
  - `swebench_sympy__sympy-24909` → `.oracle/sympy/physics/units/prefixes.py` → gold = `sympy/physics/units/prefixes.py`
  - `swebench_pallets__flask-4992` → `.oracle/src/flask/config.py` → gold = `src/flask/config.py`
  - `swebench_psf__requests-3362` → `.oracle/requests/utils.py` → gold = `requests/utils.py`
- LLM 调用接口（复用，勿造轮子）：
  - `src/harness/factory.py::load_config(path)` 加载 + 校验 config（含 `${VAR}` 与 `.env` 解析）。
  - `src/llm/client.py::LLMClient(base_url, api_key, model, temperature, max_tokens)`；`await client.chat(messages)` → `LLMResponse`，取 `.text`（字符串）与 `.usage`（`{"prompt_tokens","completion_tokens","total_tokens"}`，用于算成本）。
- 题面来源：直接用 `task["description"]`（已是 R3 清洗过的 problem statement），**剥掉**前缀 `[SWE-bench Lite <id>] ` 与尾部 `Do not use .oracle files and do not modify tests.`，得到干净 issue 文本。用清洗后的题面更**保守**（泄露更少，得到的定位准确率是下界）。

---

## 2. 探针实验设计（核心）

### 2.1 原理

一个**没见过任务**的模型，在**只给 issue 描述、不给任何 repo 结构/文件树/代码**的情况下，几乎不可能准确说出"该改哪个文件"。论文实测：SOTA 模型在 SWE-bench 收录的 repo 上能 **76%** 命中文件，在**未收录的外部 repo**上只有 **53%**——高准确率就是 instance-level 记忆的铁证。

我们在本项目 10 个实例上复刻"无上下文文件定位"这一探针，得到本数据集的定位准确率。

### 2.2 新建脚本：`scripts/contamination_probe.py`

**输入**：`--dataset datasets/swebench_lite_tasks.json`、`--config configs/baseline.yaml`（仅借它取 LLM 凭据/模型）、`--out reports/contamination_probe.md`、可选 `--cost-per-1k <float>`（与 `run_eval` 一致，用于算成本）、可选 `--limit N`（调试用）。

**每个实例流程**：

1. 从 `fixture_dir/.oracle/` 递归找唯一 `.py`，相对 `.oracle/` 的路径即 **gold 文件**（找到 0 个或 >1 个 → 该实例标 `skipped` 并在报告注明，不计入分母）。
2. 取干净 issue 文本（按 §1 剥前后缀）。
3. 从 `instance_id` 推 `repo` 全名（`<owner>/<repo>`，由 `id` 去掉 `swebench_` 前缀、把第一个 `__` 还原为 `/`、去掉末尾 `-<pr>`；或直接读 task 里已有信息）。**只给 repo 名，绝不给文件树。**
4. 构造 prompt（见 2.3），`temperature=0` 单轮 `chat`，拿 `.text`。
5. 解析模型答案为一个仓库相对路径（见 2.4）。
6. 三级判定（归一化路径分隔符为 `/`，小写化比较）：
   - `exact`：预测路径 == gold 路径 → 最强记忆信号。
   - `basename`：仅文件名相同（任意目录）→ 模块级记忆。
   - `wrong`：都不匹配。
7. 记录 `instance_id / repo / gold / predicted / match_level / tokens`。

### 2.3 Prompt（固定，写进脚本常量）

System：
```
You are a senior engineer doing bug triage. You will be given only a bug
report (issue) and the repository name. You do NOT have access to the
repository's file tree or source code. Based solely on the issue text and
your prior knowledge of the codebase, name the single SOURCE file most
likely to need modification to fix this bug.

Rules:
- Output ONLY the repository-relative file path, nothing else.
- It must be a source file, NOT a test file.
- Do not output explanations, markdown, or multiple paths.
```

User：
```
Repository: {repo}

Issue:
{issue_text}

Which single source file should be modified? Output only the path.
```

### 2.4 答案解析（鲁棒性）

- 取 `.text` 首个非空行；剥反引号、引号、行首 `-`/`*`、`path:` 之类前缀。
- 若模型仍输出多行/多路径，取第一个看起来像路径（含 `/` 或以 `.py` 结尾）的 token。
- 归一化 `\\`→`/`、去首尾空白与首部 `./`。
- 解析失败（拿不到任何路径）→ 记 `match_level=wrong`、`predicted="(unparseable)"`，仍计入分母。

### 2.5 输出报告：`reports/contamination_probe.md`（+ 同名 `.json` 原始数据）

必须包含：

- **聚合**：`exact_rate`、`basename_or_better_rate`、`wrong_rate`（分母 = 未 skipped 实例数）；总 token、总成本（若给了 `--cost-per-1k`）。
- **逐实例表**：`instance_id | repo | gold | predicted | match`。
- **交叉印证段**：把探针命中情况与 REWORK A/B 的 per-task 通过率并列——**恒过的任务（`sympy-24213`、`flask-4992`）是否也被 `exact` 命中？** 若是，则"恒过 ≈ 被记住"的污染叙事自洽，明确写出这一关联。
- **解读段**（2~4 句）：在无外部对照的前提下，给出"本数据集定位准确率 = X%，显著高于一个未见过任务的模型应有的水平 → instance-level 记忆证据"的结论；并提示绝对成功率因此不可作能力指标。

### 2.6 成本与纪律

- 规模：10 实例 × N 次重复（见下方实测修订）。`max_tokens` **不可调小**（见修订②）。单实例 prompt 仅 issue 文本（数百~约 2k token）。**总量约 5 万 token（5 次重复），相对一次全量 A/B（~59 万/任务、7h）可视为零成本。**
- **本任务允许运行探针脚本**（这是产出本身）。**严禁运行全量 A/B / `run_eval`**，不改 `configs/`、不改 scaffold、不开 `run_command`。
- 若运行时遇 LLM 余额/`HTTP 402`：停止运行，**仍交付脚本 + 文档**，在报告里标注"待余额恢复后由人工跑 `python scripts/contamination_probe.py ...`"，并把命令写清楚。

### 2.7 可选拉伸项（外部对照，**默认不做**，仅在文档"未来工作"提及）

复刻论文 76% vs 53% 的差值需要"未被 SWE-bench 收录的 repo"的 issue 作对照。本轮**不实现**（需外部取数据），只在 `CONTAMINATION-NOTES` 里写明这是把绝对差值坐实的下一步。

---

## 3. 文档：`docs/CONTAMINATION-NOTES.zh-CN.md`

新建，结构：

1. **什么是污染、为什么 SWE-bench 尤其严重**：双层污染（① HF 数据集公开；② 底层 repo 的 issue+修复 PR 全在 GitHub，是更根本的污染源）；区分 **instance-specific 记忆** vs **repository-bias 记忆**。
2. **对本项目的精确影响**（两层表，勿混淆）：

   | 你测什么 | 污染影响 |
   |---|---|
   | agent 解决真实 bug 的**绝对能力** | 被毁，数字虚高，**不可宣称** |
   | planner vs baseline 等**相对 A/B** | 基本仍有效（污染对两边对称），**但区分度被压缩** |

3. **本项目的证据**：
   - 双峰 pass 模式（引用 `SOLID-D1-REWORK-CLOSEOUT` 的 per-task：24213/flask-4992 恒 5/5，多数 sympy 恒 0/5）。
   - 探针结果（引用 `reports/contamination_probe.md` 的定位准确率与交叉印证）。
   - 结论：A/B 的"无显著差异"**至少部分由污染压缩区分度导致**，并非单纯 harness 问题。
4. **已采取的应对**：干净相对 A/B（单变量、防 402、题面清洗）+ 诚实标注 + 探针量化。
5. **未来工作（治本路径，展示"知道怎么做"）**：
   - **SWE-bench-Live**（微软，NeurIPS 2025）：post-2024 issue、月度刷新、**有 Windows split**、**leaderboard 已含 deepseek-v4-pro**——与本项目高度契合；代价是 Docker/RepoLaunch。
   - SWE-bench Pro（GPL copyleft + 私有库 + held-out）、自建 post-cutoff held-out。
   - §2.7 的外部对照探针（坐实 76% vs 53% 差值）。
6. **结论**：绝对成功率不作能力指标；相对 A/B 在"污染对称"假设下仍有参考价值，但区分度受限——这是本项目对"评估有效性"的方法论判断。

> 语气：陈述 + 取舍判断，不堆形容词。这份文档本身就是"我懂评估有效性"的面试谈资。

---

## 4. 测试 / 验收

```bash
# 1. 探针（核心产出；repeats=5 消除非确定性，max_tokens 默认 2048 防截断）
python scripts/contamination_probe.py \
  --dataset datasets/swebench_lite_tasks.json \
  --config configs/baseline.yaml \
  --out reports/contamination_probe.md \
  --repeats 5

# 1b. 改了渲染逻辑后零成本重渲染（不再调 LLM）
python scripts/contamination_probe.py \
  --from-json reports/contamination_probe.json \
  --out reports/contamination_probe.md

# 2. 全量回归仍绿
python -m pytest tests -q --basetemp $env:TEMP\coding-harness-pytest
```

验收清单：

- [ ] `scripts/contamination_probe.py` 存在，离线（除 LLM 调用外）、`temperature=0`、`--repeats`/`--max-tokens`/`--from-json`、三级判定、`truncated` 单列不计入分母、解析鲁棒不崩。
- [ ] gold 文件**全部从 `.oracle/` 实取**，不编造；找不到唯一 `.py` 的实例标 `skipped`。
- [ ] `reports/contamination_probe.md`（+ `.json`）产出：池化/逐实例命中频率 + 逐轮波动 + 与 A/B 双峰的交叉印证 + 解读段。（余额不足时此项可由人工补跑，但脚本须就绪。）
- [ ] `docs/CONTAMINATION-NOTES.zh-CN.md` 六段齐全，证据引用真实路径与真实数字。
- [ ] 全量 `pytest` 仍 **143 passed**（探针脚本不被 pytest 收集；若加单测则相应增加并说明）。
- [ ] **未触碰** `configs/`、scaffold、`run_eval` 全量；未开 `run_command`。

---

## 5. 完成后

- 更新 `docs/SOLID-ROADMAP.zh-CN.md`：在 D-1 相关行补"污染方法论：探针 + NOTES 完成"+ 证据路径（`reports/contamination_probe.md`、`docs/CONTAMINATION-NOTES.zh-CN.md`）。
- 新增 `docs/changes/SOLID-D1-CONTAMINATION-CLOSEOUT.zh-CN.md`：探针定位准确率、与双峰的交叉印证结论、token/成本、未跑项（若有）及原因。
- 不更新对外能力数字（绝对成功率已声明不可作能力指标）。

## 6. 边界 / 不做（重要）

- **不跑全量 A/B**、不改 `configs/`、不放预算、不开 `run_command`/`edit_file`、不接 Docker/SWE-bench-Live（仅写入"未来工作"）。
- 探针只做**无上下文文件定位**这一个指标；不做 guided prompting / Min-K% / n-gram（闭源 API 取不到 logits 或性价比低，仅在 NOTES 顺带提及）。
- 外部对照探针（§2.7）本轮不实现。
- **另行追踪、本轮不做**：判定前从 fixture 恢复受保护测试文件的「防作弊」改动（当前 `write_file` 已构成真实作弊面），属代码改动，待用户单独放行。

## 7. 给 Composer 的一句话起点

> 按 `docs/SOLID-D1-CONTAMINATION-EXECUTION.zh-CN.md` 落地污染方法论。核心是新建 `scripts/contamination_probe.py`：对 `datasets/swebench_lite_tasks.json` 的 10 个实例，gold 文件从各 `fixture_dir/.oracle/` 唯一 `.py` 实取；只喂清洗后的 issue 文本 + repo 名（**绝不给文件树/代码**），用 `LLMClient`（`temperature=0`）问"该改哪个源文件"，三级判定（exact/basename/wrong）算定位准确率，产出 `reports/contamination_probe.md` 并与 REWORK 的双峰通过率交叉印证。再写 `docs/CONTAMINATION-NOTES.zh-CN.md`（六段：定义/双层污染→对本项目两层影响→证据(双峰+探针)→已做应对→未来工作(SWE-bench-Live/Windows/deepseek 在榜)→结论)。允许跑探针(≈零成本)，**严禁跑全量 A/B / 改 configs / 开 run_command**；遇 402 则仅交付脚本+文档并标注待人工补跑。完成后更新 ROADMAP、写 CONTAMINATION-CLOSEOUT，保持 143 全绿。
