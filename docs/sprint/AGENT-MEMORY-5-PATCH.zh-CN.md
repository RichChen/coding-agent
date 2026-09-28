# AGENT R5 补丁（R5-patch）

日期：2026-09-28。依据：R5 审计。本轮不调用模型。做完停下等审计。

## A1 提交补做内容（阻塞）

工作区里的改动都已审过，结论是正确的，21 个卡片测试全部通过。分两次提交：

1. `created_at` 缺失时报错，不再默认 1970：`cards.py`、`cards_v3.py`、`cards_v4.py` 及对应测试。
2. v5 final：`memory-cards-v5.jsonl`、manifest、`cards_v5.py` 的 sha 规范化、`dev_time_selection.py`、`DEV-TIME-SELECTION.md`、`CHECKPOINT-5.md`、`PROGRESS.md`。

## A2 核对 v5 final（阻塞）

写一个简短的核对结果到 CHECKPOINT-5 补记：

- manifest 的 `memory_source_runs_sha256` 等于 harness `docs/sprint/memory-source-runs.json` 的发布 sha（UTF-8 + LF）。
- `cards_sha256` 能从文件复算出来。
- `validated_fix` 卡恰好 7 张：django 10914/10924/11039、sklearn 10297/11040/11281、pytest-5227。11281 的来源是 r2，因为这是编号最小的解出运行。
- 每张卡都有 `repo` 和 `created_at`，而且是 UTC `Z` 写法。

## A3 卡片构建支持 dev 加 pool 两份交接（阻塞，R6 要用）

R6 的卡片来源是 dev b0-v2 加 pool B0。harness 会把 pool B0 交接写到 `docs/sprint/main-b0-runs.json`（schema `sprint6.main-b0-runs.v1`，每条 run 有 `source_id`、`repo`、`created_at`、`repeat`、`solved`、`status`、`summary`）。

1. `scripts/build_memory_cards.py` 支持多个 `--handoff`，逐份校验。遇到 `scope` 为 mock 的交接文件（例如 `step7-mock`）直接拒绝。同一个 `source_id` 出现在两份交接里时报错。
2. 选轨迹的规则不变：取编号最小的解出运行，没有解出的取 r1 作为 `failed_attempt`。
3. manifest 里记录每份交接的发布 sha。
4. 测试：用两份合成交接文件（一份 dev 格式，一份 pool 格式）构建成功；mock scope 被拒绝；重复 id 被拒绝。

## A4 分析脚本对接真实目录结构（小项）

`scripts/analyze_a5_main.py` 要能直接读取 harness 的 `runs/a5-main/<task>/<b0|b2>/r<k>/summary.json` 和 `main-b0-runs.json`：

1. 输入是 mock 数据（summary 或交接文件标了 mock）时拒绝。
2. 某道题 B0 或 B2 不满 3 次时，按预注册规则处理（在输出里列出，不静默补齐）。
3. 测试用合成目录，不要读 harness 仓库的真实文件。

## 完成标准

- 提交完成，工作区干净，全量测试通过。
- CHECKPOINT-5 补记写明 A1–A4 的结果。
- 不改 coding-harness 仓库，停下等审计。
