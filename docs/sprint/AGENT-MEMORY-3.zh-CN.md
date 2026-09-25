# coding-agent 第三轮计划书：用新环境的轨迹重建记忆（v4）

日期：2026-09-25。执行者：挂在 `D:\crq\src\coding-agent` 的 Cursor agent。
前置：`AGENT-MEMORY-2.zh-CN.md` 和 `CHECKPOINT-2.md`。第一轮的硬约束继续有效，除非本文另有说明。
配套：`D:\crq\src\coding-harness\docs\sprint\HARNESS-SPRINT-3.zh-CN.md`。两边通过第 3 节的两个交接文件协作。

## 0. 审计结论

第二轮有效：v3 卡片从 `run/events.jsonl` 里提取出了读取范围、测试命令、诊断原话和改动的符号，过滤掉了旧 transport 镜像的噪声（pip、缺 six、`git: not found` 等）。B3 改为对着目标题的真实源码检查，并新增了 `relocated` 规则。没有花钱。

剩下的问题：

1. **记忆的来源已经过时。** 11 张卡全部来自旧的坏环境轨迹（没有依赖、跑不了测试），其中 5 张是 `failed_attempt`。harness 第二轮已经在新环境下对其中 9 道源题跑了 B0：django 10914、10924、11039，sympy-11400，pytest-5227 都已被 grader 确认解出。sympy-11400 在旧记忆里是失败的尝试，这次新环境里解出了。第三轮 harness 还会在 14 道 dev 题上各跑 3 次，产出更多经过验证的轨迹。这些是现成的、质量更高的记忆来源。
2. **提取器读不了 harness 新运行目录的格式**（已对照代码核实）：
   - `extract_source()` 固定读 `source_dir / "run" / "events.jsonl"` 和 `run/session/artifacts`；harness 的 sprint 运行目录是 `<run_dir>/events.jsonl` 和 `<run_dir>/session/artifacts/`，没有 `run/` 这一层。
   - `_changed_symbols()` 只认 `changed[path] = {"content": ...}`；`BaselineImageBackend` 导出的是 `changed[path] = "<base64 字符串>"`，按现在的写法会提取出空的符号列表。
3. **B2 会把失败尝试的修法当作建议注入。** 比如 pytest 的 3 道目标题，排第一的都是 5103，而 5103 是一次失败的修法。
4. **测试命令里还有环境探测和非测试命令**，比如 `python -c "import pytest; print(pytest.__version__, pytest.__file__)"`、`python -c "import sklearn; print(sklearn.__file__)"`、`python -m py_compile ...`。原因是 `_keep_command()` 把所有 `python -c` 和 `python -m` 都保留了。
5. **覆盖面窄。** sympy 目标题在 B3 下全部被拒；sphinx 四题和 sympy-20154 一条记忆都选不到。sphinx 需要 harness 先补源题（harness 第 9 步），本轮 agent 这边不处理。

本轮目标：**提取器兼容新格式；用 harness 新环境下的轨迹重建 v4 卡片，记忆源从 11 道扩到 15 道；失败尝试只保留导航信息；只用 dev 留一法调整检索，不在 pilot 目标题上调参。**

## 1. 本轮规则补充

- 本轮预计不花模型钱。如果确实需要 LLM 提炼，上限 3 CNY，并先在 PROGRESS 里写明理由：规则版在哪些卡上明显不够用，举出具体例子。
- 继续往 `docs/sprint/PROGRESS.md` 追加记录，标题用"第三轮 第 N 步"。开工前先提交本计划书和第二轮计划书（两份目前都未跟踪），再打 tag `mem3-start`。
- **只读** coding-harness 的运行目录和交接文件，不修改 coding-harness 的任何文件。
- **不在 pilot 目标题上调参。** 检索或渲染规则只能依据 dev 留一法的结果来调整（第 5 步）；20 道 pilot 题的离线选择表只用来报告，不能看着它改规则。
- **记忆标签的来源要声明。** v4 的 `validated_fix` / `failed_attempt` 标签来自源题自身的 SWE-bench 测试（由 harness 的 grader 给出）；源题和 20 道目标题不相交。按总合同 §5 的要求，这是一种需要单列声明的协议，写进 `docs/sprint/MEMORY-PROTOCOL-V4.md`。

## 2. 分步计划

### 第 1 步：提取器兼容两种目录格式（不花钱）

1. `extract_source()` 新增参数 `layout`，取值为 `"memory_pool"`（旧格式：`<source_dir>/run/events.jsonl`）或 `"sprint"`（新格式：`<run_dir>/events.jsonl`，artifacts 在 `<run_dir>/session/artifacts/`）。不传时按目录里实际存在的文件自动判断，判断不出来就报错，不要猜。
2. `_changed_symbols()` 同时支持 `{"content": ...}` 和 base64 字符串两种 `changed` 值。解码失败时记进 `skipped`，不静默跳过。
3. 用 harness 的真实运行目录做回归，只读：
   - `D:\crq\src\coding-harness\runs\sprint2-b0\django__django-11039`（解出，改了 `sqlmigrate.py`）；
   - `D:\crq\src\coding-harness\runs\sprint2-b0\sympy__sympy-11400`（解出，改了 `ccode.py` 和 `codeprinter.py`）。
   断言能提取出读取范围、测试命令和非空的改动符号（比如 `_print_sinc`）。旧格式的已有测试必须继续通过。
4. 单元测试放两份最小夹具，每种格式一份。不要把真实运行目录复制进仓库。

### 第 2 步：命令过滤（不花钱）

`_keep_command()` 改为只保留"真正在运行测试或复现问题"的命令：

- **保留**：`pytest`、`python -m pytest`、`tests/runtests.py`；以及调用了仓库代码（不只是 import）的 `python -c` 片段。
- **丢弃**：
  - 只做 import，或只打印 `__file__`、`__version__`、`sys.path` 的 `python -c`；
  - `python -m py_compile`、`python -m pip`、`pip list`、`which`、`ls`；
  - 旧环境噪声（第二轮已有的规则继续保留）。
- 被丢弃的命令记进 `skipped`，并附上原因类别。

用第二轮 CHECKPOINT-2 里列出的几条命令写测试：pytest-5221 的 `import pytest; print(...)`、sklearn-10949 的 `print(sklearn.__file__)` 和 `py_compile` 应当被丢弃；django-10914 的 `runtests.py ...` 应当保留。

### 第 3 步：按验证状态渲染（不花钱）

`render_card()` 按状态区分：

- `validated_fix`：完整渲染 approach、files、tests、pitfalls。
- `failed_attempt`：**不渲染 approach**。头部写"这是一次没有通过测试的尝试，只供定位参考"，只保留 files、tests 和 pitfalls。如果轨迹里能看出失败原因（比如改错了位置），写一句。
- `unverified`：渲染 approach，但头部标明"未验证"。

B1（原始轨迹）也使用同样的状态头部。补测试：失败尝试的渲染结果里不能出现 approach 的文本。

### 第 4 步：v4 卡片（不花钱）

**输入：**

- 旧的 11 条记忆源（`A5-real240-77-harness-preflight/memory-snapshot.jsonl` 所指的运行目录，格式为 `memory_pool`）。
- harness 的交接文件 `D:\crq\src\coding-harness\docs\sprint\memory-source-runs.json`（格式见第 3 节，格式为 `sprint`）。
- **harness 第三轮第 5 步完成之前**，这个文件还不存在。可以先用 `runs/sprint2-b0/` 里的 12 次运行做一版临时的 v4（标注为 `interim`），把构建脚本和测试写好。等交接文件出现后，重新构建正式版。

**每道源题选一条轨迹，规则固定，不看卡片内容来挑：**

1. 如果有新环境下解出的运行，取 `repeat` 编号最小的那一次，标记为 `validated_fix`。
2. 如果新环境下都没解出，取新环境下 `repeat` 编号最小的那一次，标记为 `failed_attempt`。
3. 如果新环境下没有运行，就用旧的记忆池轨迹，沿用 harness `docs/sprint/memory-source-verification.json` 里的标签；grader 不可用时标记为 `unverified`。

**记忆源集合：** 旧的 11 道，加上 harness dev 集里另外 4 道，共 15 道：sympy-11870、sympy-11897、pytest-5227、sklearn-10508。

- 这些源题和 20 道 pilot 目标题不相交。构建脚本里写一条断言：源题 id 与 `configs/a5/canonical-handoff.json` 里的目标题 id 不能有交集。
- pytest-5221 在新环境下没有运行（gold 校准没通过），继续使用旧轨迹，标记为 `unverified`。

**卡片新增字段：** `label_origin`（取值 `source_task_swebench_tests` 或 `legacy_verification`）、`source_run`（运行目录和 repeat 编号）、`layout`。

**产出：**

- `benchmarks/a5/memory-cards-v4.jsonl`；
- `benchmarks/a5/memory-cards-v4.manifest.json`（格式见第 3 节）；
- `docs/sprint/MEMORY-PROTOCOL-V4.md`：说明选轨迹规则、标签来源、源题和目标题不相交，以及和 v3 的差异。

另外，把 15 张卡各渲染一遍，放进 `docs/sprint/V4-CARDS.md`，便于人工审阅。人工审阅时如果发现某张卡明显不对（比如 approach 和改动对不上），修的是**生成规则**，不能手改单张卡。

### 第 5 步：dev 留一法检索评估（不花钱）

目的：在不接触 pilot 目标题的情况下，判断检索和 B3 规则是否合理。

1. 对 15 道源题中的每一道，把它当作"目标题"：用它的公开 issue 文本和它自己的原始源码树（harness receipt 旁边的 `staging/original`，只读；只用 original，不用 known-good 或 baseline），在**去掉它自己**的另外 14 张卡上运行 B1、B2、B3 的选择逻辑。
2. 产出 `docs/sprint/DEV-LOO-SELECTION.md`：每道题选中了哪些卡、分数多少、B3 接受或拒绝了哪些、原因是什么。
3. 人工看一遍：选中的卡是否真的和这道题的问题相关，仅凭 issue 和卡片内容判断。如果需要调整检索（比如文件路径或符号在目标树里存在时加分）或调整 `min_score`，就在这一步调，并把调整前后的表都保留。
4. 这张表同时是 harness 第 8 步（dev 记忆冒烟对照）的离线预期。

### 第 6 步：pilot 目标题的离线选择表（只报告）

用第 5 步定下来的规则，对 20 道 pilot 目标题重跑 B1、B2、B3 的离线选择（目标源码只从 `D:\crq\tmp\a5-targets` 的 `source.tar.gz` 解压结果读取）。产出 `docs/sprint/PILOT-SELECTION-V4.md`，和 CHECKPOINT-2 里的 v3 表并排对比。**看完这张表不能再回头改规则。** 如果发现明显问题，写进 CHECKPOINT-3，等审计再定。

### 第 7 步：CHECKPOINT-3

写 `docs/sprint/CHECKPOINT-3.md`，内容包括：

- 第 1–3 步的改动和测试结果。
- v4 与 v3 的对比：每张卡的状态变化（比如 sympy-11400 从 `failed_attempt` 变成 `validated_fix`），tests 字段是否干净，approach 是否能点到具体函数。
- 抽 3 张 v4 卡片的完整渲染原文：一张 `validated_fix`、一张 `failed_attempt`、一张 `unverified`。
- dev 留一法的结论，以及做过的规则调整。
- pilot 离线选择表，以及覆盖情况：多少道题在 B3 下至少能注入 1 张卡。
- 交接文件的 sha256，以及它引用的 harness 交接文件的 sha256。
- 花费。

然后停下，等审计。

## 3. 与 coding-harness 的交接文件

两边都不修改对方的仓库。

**harness → agent：`D:\crq\src\coding-harness\docs\sprint\memory-source-runs.json`**（harness 第三轮第 5 步产出）

```json
{
  "schema": "sprint3.memory-source-runs.v1",
  "profile_tag": "b0-v1",
  "harness_commit": "<git sha>",
  "label_origin": "source_task_swebench_tests",
  "runs": [
    {
      "source_id": "django__django-10914",
      "repeat": 1,
      "run_dir": "D:/crq/src/coding-harness/runs/sprint3-b0/django__django-10914/r1",
      "layout": "sprint",
      "solved": true,
      "grader_status": "pass",
      "f2p_passed": 1, "f2p_total": 1, "p2p_passed": 0, "p2p_total": 0
    }
  ]
}
```

- 如果 `runs` 里出现了不在第 4 步 15 道源题范围内的 id，一律忽略，并写进 PROGRESS。
- 如果出现了 pilot 目标题的 id，**立即停止**，写进 PROGRESS 并报告。
- F2P / P2P 的计数只用来打标签，**不写进卡片正文**。

**agent → harness：`benchmarks/a5/memory-cards-v4.jsonl` 和 `benchmarks/a5/memory-cards-v4.manifest.json`**

```json
{
  "schema": "memory-cards.v4.manifest",
  "cards_sha256": "<sha256 of memory-cards-v4.jsonl>",
  "status": "interim | final",
  "coding_agent_commit": "<git sha>",
  "sources": [
    {"source_id": "django__django-10914", "status": "validated_fix", "label_origin": "source_task_swebench_tests", "source_run": "r1"}
  ],
  "build_inputs": {
    "memory_source_runs_sha256": "<sha256 of harness memory-source-runs.json, or null for interim>",
    "legacy_snapshot_sha256": "<sha256 of memory-snapshot.jsonl>"
  }
}
```

harness 只有在 `status == "final"`、并且 `memory_source_runs_sha256` 和它自己产出的文件一致时，才会用 v4 跑第 8 步。

插件接口保持和当前 `reposkill_agent/memory/card_plugin.py` 一致：`MemoryCardPlugin(variant, cards, repo, issue, target_root, max_bytes=4096, min_score=1.0)`，以及 `load_memory_cards(path)`。留一法的过滤由 harness 在传入卡片之前完成，本轮不需要改构造参数。如果确实必须改接口，在 PROGRESS 里写明新旧签名，并在 CHECKPOINT-3 里重点标出。

## 4. 本轮不做的事

- 为 sphinx 或 sympy-20154 手写或编造记忆卡。
- 根据 pilot 目标题的离线表调整检索或渲染规则。
- 修改 coding-harness 的任何文件。
- 手工编辑单张卡片的内容。
