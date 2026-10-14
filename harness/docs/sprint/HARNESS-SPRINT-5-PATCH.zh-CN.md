# HARNESS R5 补丁（R5-patch）

日期：2026-09-28。依据：R5 审计。本轮不调用真实模型，只允许 mock。做完停在 CHECKPOINT-5 补记，等审计后再打 `a5-main-freeze`。

## 背景

R5 主体和补做都已提交，不需要回滚。审计发现 3 个会污染 R6 数据的问题（P1–P3），外加 2 个小项。

## P1 mock 输出和正式输出分开（阻塞）

现状：第 7 步 mock 写进了 `runs/a5-main/`（django-16527、sympy-11618、sklearn-14053 的 b0/r1 和 b2/r1）。`run_phase` 看到 `summary.json` 就跳过，R6 会把这 6 个 mock 结果当成真实结果。

要做：

1. 把 `runs/a5-main/` 整个移到 `runs/a5-main-mock-step7/`。只移动，不删除。
2. 把 `docs/sprint/main-b0-runs.json` 改名为 `docs/sprint/main-b0-runs.step7-mock.json`。R6 的正式交接文件由 R6 重新生成。
3. `run_a5_main.py`：
   - `--mock` 时输出根目录用 `runs/a5-main-mock/`，交接文件写 `main-b0-runs.mock.json`。正式运行用 `runs/a5-main/` 和 `main-b0-runs.json`。
   - 续跑跳过的条件改成：`summary.json` 存在，不是 mock，profile 是 `b0-v2`，variant 与当前 phase 一致。条件不满足就报错停下，不要覆盖。summary 里如果还没有 mock/profile 字段，就在 `run_task` 里补上。
   - `write_b0_handoff` 遇到 mock summary 就报错。
4. 测试：用临时目录构造一个 mock summary，证明正式 phase 会拒绝它。

## P2 时间过滤只信卡片自带字段，并且不能静默退化（阻塞）

现状：

- `temporal_filter` 从 `docs/sprint/memory-source-runs.json`（dev 交接文件）读取卡片的 repo 和 `created_at`。R6 的卡片有一部分来自 pool B0，dev 交接文件里没有这些日期，所以这部分卡片会因为 `not meta.get("created_at")` 被全部丢弃，B2 实际上只剩 dev 卡。
- B2 拿不到目标的 `created_at` 时会退回到 `leave_one_out`，时间过滤被悄悄跳过。
- 比较方式是字符串比较。现在两边都是 `Z` 结尾，暂时正确，但写法一变就会出错。
- `dated_cards` 遇到没有日期的行会静默丢弃。

要做：

1. `temporal_filter` 改用卡片自己的 `repo` 和 `created_at`（v5 卡片都有这两个字段）。如果交接文件里也有这张卡的日期，就做交叉核对，不一致时报错。
2. 日期统一用 `datetime.fromisoformat`（先把 `Z` 换成 `+00:00`）解析成带时区的时间再比较。解析失败就报错。
3. B2 拿不到目标 `created_at` 时直接报错。目标日期来源固定为 `main-targets.yaml`，dev 任务则用 dev 交接文件。
4. `dated_cards` 遇到缺日期的行直接报错，不再静默丢弃。
5. 测试：pool 来源的卡片（不在 dev 交接文件里）能正常参与过滤；时间写法不同（`+08:00` 对 `Z`）时结果正确；缺日期时报错。

## P3 Django docstring 测试 id 映射回测试方法（阻塞，影响判分有效性）

现状：SWE-bench 的 django 日志解析器会把带 docstring 的测试记成 docstring 的第一行，例如 `Searches over multi-valued relationships return rows from related`。我们的 observer 没法定位这类 id：

- django-15022 的 F2P 从 3 条减到 1 条，这道题"解出"的标准明显变松。
- 一共丢掉了 216 条 P2P。
- django-14434 的 54 条同类 id 没有被识别规则拦下，而是被当成 gold 失败排除了，口径和其他题不一致。

要做：

1. 在应用了测试补丁的源码树上，用 `ast` 扫描测试文件，找出 docstring 第一行（strip 之后）和这个 id 完全相等的测试方法，映射成 `module.Class.method`。扫描范围：测试补丁涉及的文件，加上同一道题里其他可定位 id 所属的模块。必须唯一匹配，零个或多个匹配都算定位失败。
2. 固定规则：映射之后仍有 F2P 无法定位，就把这道题排除出 pool，理由记为 `f2p_unaddressable`。无法定位的 P2P 照旧丢弃并记录。
3. 校准回执的 `nodeids` 里新增 `mapped` 计数和映射明细。
4. 对所有 django 题重新校准，其他 repo 不动。校准只用 empty 和 gold，不涉及模型。更新 `MAIN-CALIBRATION.md` 和合格题数。
5. 如果有题因此被排除，按原规则更新 accepted 列表，不补题。

## P4 扫描排除规则加护栏（小项）

现状：0cf55dd 按"和基础镜像同 sha"或"和 pip RECORD 同 sha"排除命中。审计显示整个 pool 只排除了 6 个文件（babel 的 mofile/pofile、`attr/_cmp.py`、`pickle.py`/`pickletools.py`），都和目标项目无关。但规则本身太宽。

要做：

1. `/opt/repo` 下的命中，以及路径属于目标项目顶层包（`/opt/repo` 下带 `__init__.py` 的顶层目录名）的命中，一律不适用这两条排除。
2. 加测试。
3. 在 `MAIN-CALIBRATION.md` 里列出这 6 个排除文件和排除理由。
4. 不需要重建镜像。用新规则对 56 个 receipt 重新跑一遍扫描判定，确认结论不变即可。

## P5 杂项

1. 删除仓库根目录下未跟踪的 `pelican-bicycle.html`。
2. 等 agent 侧提交 v5 final 之后，用 v5 final 卡片对 P1 里那 3 道题跑一次 mock B2（写到 mock 根目录），确认过滤和注入记录正常。

## 完成标准

- 以上各项的测试全部通过，全量测试不回退。
- `runs/a5-main/` 不存在或为空，`docs/sprint/main-b0-runs.json` 不存在。
- CHECKPOINT-5 补记：P1–P5 的结果、django 重新校准前后的 F2P/P2P 数量对比、最终合格题数。
- 真实模型花费为 0。
- 不打 tag，停下等审计。

## 约束

沿用 R5 的全部硬约束：不泄露密钥，gold/test/F2P/P2P 不进入 agent 可见范围，pool 题在冻结前不跑真实模型，小步提交，不 force push，不删旧证据，不改 coding-agent 仓库。
