# coding-harness 收尾 + 实习简历向增强（给 Claude Code）

> **用途**：在 `CLAUDE-CODE-IMPROVEMENTS.md` 已落地的基础上，完成「未接线」收尾，并做 **2～3 个高 ROI 简历亮点**。  
> **目标仓库**：`coding-harness`（当前无 git 亦可改代码；git init 由用户自行完成，不在本任务内）。  
> **原则**：保持 OpenAI 消息格式；不实现多 Agent / Web / SWE-bench / Docker（见 §7）。

---

## 0. 当前基线（改前请先读）

已完成（勿回退）：

- `src/harness/factory.py` — `load_config` + `build_agent`
- `src/config/schema.py` — Pydantic 校验
- `src/policy/limits.py` — 文件大小限制
- `src/runtime/hooks.py` + `compact.py` — micro_compact（YAML 默认关）
- `src/tracing/events.py` — EventBus（**loop 已 emit，factory 未接线**）
- `src/tools/edit.py` — edit_file（**YAML 未默认启用**）
- `src/tools/events.py` — read_events（**factory 未注册**）
- `loop.py` — `total_tool_invocations`、`step_number`、精确 `tool_failure_rate`
- `run_eval` — 每任务 TraceLogger；CSV 含 `trace_file`
- 测试：`pytest tests/` — **68 passed**（改完须仍全绿）

---

## 1. 执行顺序（必须按批）

```text
批次 A（Wiring 收尾）  →  pytest 全绿
批次 B（简历亮点，选做项见 §4）  →  pytest 全绿 + 更新 README.zh-CN.md 简短说明
```

**不要**在同一 commit 里混做 A 和 B 中未完成的半成品；A 完成并测试通过后再做 B。

---

## 2. 批次 A — Wiring 收尾（必做）

### A-1：EventBus 接入 factory 与运行入口

**问题**：`AgentLoop` 在 `event_bus` 非空时会 `emit`，但 `EventBus.emit` 要求先 `open(task_id)`；`build_agent` 未创建/传入 `EventBus`，`run_single` / `run_eval` 不会产生 `events_*.jsonl`。

**参考**：`tests/test_compact.py` 中 `TestEventBus::test_events_in_agent_loop` 的接线方式。

**改动**：

1. `build_agent(..., *, event_bus: EventBus | None = None)`  
   - 若 `config["tracing"]` 中 `lifecycle_events: true`（见 A-4 schema），则创建 `EventBus(output_dir=tracing.output_dir)` 并传入 `AgentLoop`。  
   - 默认 `lifecycle_events: false`，与现网行为兼容。

2. **`AgentLoop.run` 开头**（在 `run_start` emit 之前）：若 `self.event_bus` 且尚未 open，则 `self.event_bus.open(task_id)`。  
   - 或在 `run_single` / `EvalRunner._run_task` 里 open/close，二选一，**避免泄漏文件句柄**；推荐在 `run()` 内 `try/finally: bus.close()`。

3. `run_end` / 异常路径均 `close()` EventBus。

4. **验收**：
   - `python scripts/run_single.py --config configs/baseline.yaml` 且 tracing 开启 lifecycle 后，`traces/` 下出现 `events_<task_id>_*.jsonl`，含 `run_start`、`llm_complete`、`tools_complete`、`run_end` 等事件。
   - `tests/test_compact.py` 仍通过；可增 1 个 test：`build_agent` + mock LLM + lifecycle_events=true → events 文件存在。

---

### A-2：新增 `configs/debug.yaml`

**目的**：debug 专用配置，不把 `read_events` 放进 hardened。

**内容要点**：

```yaml
# 在 baseline 或 hardened 基础上继承/复制，并：
tracing:
  lifecycle_events: true
tools:
  enabled:
    - read_file
    - write_file
    - list_dir
    - run_command
    - read_events   # 仅 debug
```

**factory 改动**：

- `enabled` 含 `read_events` 时：注册 `ReadEventsTool`，并对该 tool 调用 `set_event_bus(agent.event_bus)`（需在 agent 构建后或 lazy 绑定）。
- 文档说明：仅用于本地调试，**不要**用于 baseline/hardened 批量 eval。

---

### A-3：`edit_file` 意图文档化（不必强行改 hardened）

**现状**：`EditFileTool` 已实现；`hardened.yaml` 使用 `search_replace`（唯一匹配），未启用 `edit_file`。

**要求**（README.zh-CN.md 一小节即可，≤15 行）：

| 工具 | 行为 | 适用场景 |
|------|------|----------|
| `search_replace` | 必须唯一匹配，否则失败 | 严格、可审计的替换 |
| `edit_file` | 替换**首次**出现 | 模型不确定唯一性时 |

- 明确：**hardened 故意不启用 `edit_file`** 是为减少误改；若要在某配置启用，在 `tools.enabled` 加入即可。
- **不必**修改 `hardened.yaml`，除非你认为应对 1～2 条 dataset 任务启用并说明理由。

---

### A-4：配置 schema 小扩展（配合 A-1 / A-2）

在 `src/config/schema.py` 的 `TracingConfig` 增加：

```python
lifecycle_events: bool = False
```

`baseline.yaml` / `hardened.yaml` 可写 `lifecycle_events: false`（显式）或省略（默认 false）。  
`debug.yaml` 为 `true`。

---

### 批次 A 完成定义

- [ ] `lifecycle_events: true` 时 `run_single` / `run_eval` 产出 `events_*.jsonl`
- [ ] `configs/debug.yaml` 存在且可 `load_config` 通过校验
- [ ] `read_events` 仅在 debug 配置注册
- [ ] README.zh-CN.md 有 edit_file vs search_replace 说明
- [ ] `pytest tests/ -v` 全绿

---

## 3. 批次 B — 实习简历向增强（按优先级做满 §3.1 三项，§3.2 时间允许再做一项）

### 3.1 必做三项（高 ROI）

#### B-1：SYSTEM_PROMPT 外置

**动机**：面试可讲「prompt 与代码解耦、可做配置实验」。

**改动**：

1. 新建 `prompts/system_default.md`（从 `loop.py` 的 `SYSTEM_PROMPT` 迁出，内容保持一致，英文）。
2. `HarnessConfig` 增加可选字段，例如：
   ```yaml
   runtime:
     system_prompt_path: prompts/system_default.md  # 相对仓库根
   ```
   或顶层 `prompts: { system: prompts/system_default.md }`（与 schema 风格统一即可）。
3. `build_agent` 或 `AgentLoop.run` 启动时读取文件；文件不存在 → 清晰 `FileNotFoundError`。
4. `loop.py` 删除硬编码长字符串，保留极短 fallback 或要求必须配置（二选一，文档写明）。
5. **可选**：`prompts/system_strict.md` 供 `strict.yaml` 使用（见 B-4），多一行「更保守的工具使用规则」即可，不必长篇。

**验收**：改 prompt 文件后无需改 Python 即可改变 agent 行为；单测可用 tmp_path 放 prompt 文件。

---

#### B-2：新增 `expected.type` — 推荐 `file_exists`

**动机**：证明评测框架可扩展；实现量比 `diff_contains` 小。

**改动**：

1. `EvalRunner._run_task` 增加分支：
   ```python
   elif expected.get("type") == "file_exists":
       expected_check = self._check_file_exists(workspace, expected)
   ```
2. `_check_file_exists(workspace, expected)`：`path` 相对 workspace，`exists()` 即可；可选 `min_size_bytes`。
3. 在 `datasets/mini_tasks.json` **新增 1 条**任务（勿破坏现有 35 条 id），例如 `id: "file_exists_gitignore"`，`expected: { "type": "file_exists", "path": ".gitignore" }`。
4. `tests/test_runner.py`：对 `_check_file_exists` 或聚合逻辑加 2～3 个单元测试。

**文档**：README.zh-CN.md「判定类型」表格增加一行。

**验收**：`pytest tests/test_runner.py` 通过；仅跑新任务 id 的 mock/单元测即可，不要求全量 API eval。

---

#### B-3：提交脱敏的 demo 轨迹

**动机**：简历/面试展示「真实 think → act → observe」，补 mock 集成测的缺口。

**改动**：

1. 新建目录 `docs/examples/` 或 `traces/demo/`（二选一，推荐 `docs/examples/` 以免与运行时 `traces/` 混淆）。
2. 放入 **1 份** 脱敏示例（二选一）：
   - **首选**：真实跑 `run_single` 一条简单任务后导出的 JSONL（删掉 API key、敏感路径、过长 content 可截断到 2k 字符并注明 `truncated: true`）。
   - **备选**：用 `MockLLMClient` 生成结构等价、字段完整的「合成 demo」，文件名 `demo_baseline_synthetic.jsonl`，README 标明 synthetic。
3. `README.zh-CN.md` 增加「示例轨迹」：说明如何阅读（step / tool_calls / policy 拒绝样例若有更好）。

**注意**：不要把 `.env` 或含 key 的文件提交进仓库。

---

### 3.2 选做一项（中 ROI，时间够做 1 个即可）

#### B-4（推荐）：`configs/strict.yaml` + 三配置对比

- 比 `hardened` 更严：`max_steps: 10`、`file_size_limit_bytes: 65536`、`read_file_max_lines: 200`、更短 timeout；`tools.enabled` 可去掉 `run_command` 或缩小白名单。
- `run_eval --configs baseline hardened strict` 或文档给出命令。
- 报告已支持多 config；确认 CSV/Markdown 能列出三行。

#### B-5：按 `difficulty` 聚合成功率

- `mini_tasks.json` 每条已有 `difficulty`（easy/medium/hard）。
- `aggregate_metrics` 或 `ReportGenerator` 增加「按 difficulty 分桶」表（passed rate per bucket per config）。
- 测试：用 3 条假 `TaskResult` 验证分桶数学。

#### B-6：`run_single` / `run_eval` 的 `--verbose` 与 `--dry-run`

- `--verbose`：每步打印 step_number、tool 名、messages 长度、policy block 摘要。
- `--dry-run`：LLM 仍调用（或可选 mock），工具不执行，返回 `[dry-run] would call {name}`；**默认关**，文档说明仅调试。

---

### 批次 B 完成定义

- [ ] §3.1 三项（B-1～B-3）全部完成
- [ ] §3.2 至少 0 项（推荐 B-4 或 B-5 二选一）
- [ ] `LEARNING.zh-CN.md` 若与 prompt 路径 / 新 expected 冲突则更新 1～2 段
- [ ] `pytest tests/ -v` 全绿

---

## 4. 文件改动清单（速查）

| 批次 | 文件 |
|------|------|
| A | `src/harness/factory.py`, `src/runtime/loop.py`, `src/config/schema.py`, `configs/debug.yaml`, `configs/*.yaml`（tracing 字段）, `README.zh-CN.md` |
| B | `prompts/*.md`, `src/config/schema.py`, `src/eval/runner.py`, `datasets/mini_tasks.json`, `tests/test_runner.py`, `docs/examples/*`, `configs/strict.yaml`（可选）, `src/eval/report.py`（可选 B-5）, `scripts/run_*.py`（可选 B-6） |

---

## 5. 面试叙事（改完后 README 可摘 3 句）

1. **Harness**：plan-act-observe 循环 + policy 沙箱/白名单 + budget，baseline vs hardened（+ strict）可复现对比。  
2. **Eval**：可扩展 `expected.type`（含新增的 `file_exists`），`success` 与 `expected_check` 分离，指标用真实 `total_tool_invocations`。  
3. **可观测**：JSONL step trace + 可选 lifecycle EventBus；仓库内附 demo 轨迹与脱敏说明。

---

## 6. 与 `CLAUDE-CODE-IMPROVEMENTS.md` 的关系

| 文档 | 内容 |
|------|------|
| `CLAUDE-CODE-IMPROVEMENTS.md` | 架构对齐 learn 项目（P0～P2）— **主体已完成** |
| **本文档** | 未接线收尾 + 实习展示向增量 |

未在本文明做的 P2-4（LLM auto_compact）、`configs/long_run.yaml` 可另开任务；**eval 默认仍禁止 auto_compact**。

---

## 7. 明确不做

- Next.js / Web 学习站  
- 多 Agent、MessageBus、Skills 加载器全套  
- Git worktree 并行  
- 切换 Anthropic SDK  
- Docker / nsjail / SWE-bench 全量  
- 在本任务内 `git init`（用户自行处理）

---

## 8. 给 Claude Code 的起始提示（复制即用）

```text
请阅读仓库根目录 CLAUDE-CODE-RESUME-POLISH.md。

1. 先完成「批次 A」全部项（EventBus 接线、debug.yaml、edit_file 文档、schema lifecycle_events），pytest 全绿后停止并简要汇报。
2. 再继续「批次 B」§3.1 必做三项（prompt 外置、expected.type file_exists、demo 轨迹）。
3. 时间允许再做 §3.2 一项（优先 strict.yaml 或 difficulty 分桶报告）。
4. 保持 OpenAI messages/tool 格式；不要实现 §7 禁止项。
5. 每批结束运行：pytest tests/ -v
```

---

*文档版本：与当前 coding-harness 代码快照对齐（68 tests, factory/compact/events 已存在）。*
