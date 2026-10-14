# Case Study: Context Expansion & JSON Repair

> 机制：`reposkill_agent/core/context_expansion.py`、`agents/llm_developer.py`、`eval/graph_runner.py`  
> 证据：Batch 4 落地；Batch 5.10 context_heavy mean 持平（L2=L5=85%）

## 问题

Phase 6 real LLM eval 上 `needs_more_context` 导致 api/context 类任务直接 test_failure — LLM 声明需要更多文件但 graph 未扩展可读路径。同时 L4/L5 prompt 膨胀后出现 JSON parse error（2–3 次/run），patch plan 无法应用。

## 机制

### 1. needs_more_context 恢复

当 `LLMDeveloperAgent` 返回 `llm_error_type=needs_more_context` 或 patch action 含 `requested_context` 时，graph runner 触发 **context expansion replan**：

1. `collect_requested_context(previous_actions)` 读取 LLM 请求的文件/context 关键词
2. `expand_allowed_paths(...)` 按关键词扩展可读路径（tests/、expected_files 父目录、package modules 等）
3. 每轮最多 `MAX_PATHS_PER_ROUND=3`，总计 `MAX_TOTAL_ALLOWED_PATHS=6`
4. Replan 后 Locator/Developer 在扩展 context 下重试 patch

Metrics：`ctx_expand`、`paths_added`、`ctx_recovered`（recovery 成功计数）

### 2. JSON repair retry

Patch plan 必须为结构化 JSON（`PatchPlan` schema）。Parse 失败时：

1. 捕获 JSON decode / validation error
2. 发起 repair prompt，要求 LLM 修正格式
3. Metrics：`repair_try`、`repair_ok`

Batch 5.10：L2 repair 10/10，L5 repair 7/7（2 repeats aggregate）— repair 路径有效降低 hard parse failure。

### 3. Context recovery augmentation policy

Context expansion replan 使用 **`context_recovery_minimal`** 或 **`memory_context_recovery`**（memory_heavy 上允许少量 memory hint），**禁止 skill 注入**，避免 replan 轮次 prompt 膨胀与干扰叠加。

## 效果

| 指标 | L2（5.10 mean） | L5（5.10 mean） |
| --- | ---: | ---: |
| context_heavy success | 85.0% | 85.0% |
| ctx_expand | 19 | 13 |
| ctx_recovered | 9 | 7 |
| parse_err total | 10 | 10 |
| repair try/ok | 10/10 | 7/7 |

**解读**：Context expansion 是 L2 baseline 可靠性的重要组成（L2 context 85% vs L0 60%）。L5 在 context_heavy 上 mean **持平** — full stack augmentation 未在此 category 带来额外增益，但也没有显著回退（Batch 5.8 后 context_primary 零 augmentation）。

Repeat 0 曾出现 context_heavy L5 < L2（−10pp），Repeat 1 拉回（+10pp），说明 context 路径对 run-to-run 波动敏感。

## 典型 trace 模式

1. 首轮 patch：`needs_more_context` + `requested_context=["tests", "callers"]`
2. Expansion 添加 `tests/test_api.py`、`src/pkg/caller.py` 等
3. Replan：minimal policy，Developer 在扩展 context 下生成 patch
4. 若 JSON parse fail → repair retry → `repair_ok=1`

## 局限

- Context expansion 是 **L2 级能力**，不是 L5 相对 L2 的主要 delta 来源
- 路径扩展 heuristic 可能漏掉关键文件；依赖 LLM 的 `requested_context` 质量
- traceback_repair category mean 持平（70%），样本仅 5 tasks
- 扩展路径增加 prompt 长度，与 parse_err 存在张力（L5 std 高于 L2 部分原因）

## 相关文档

- `docs/current-evidence.md` — Phase 6 needs_more_context gap
- `reports/phase7-variance-summary.md` — context_heavy per-repeat 波动
- `docs/case-study-skill-gating.md` — context_primary zero augmentation
