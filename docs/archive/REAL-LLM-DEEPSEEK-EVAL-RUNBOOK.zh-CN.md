# Composer Task: Real DeepSeek LLM Eval

> 用途：交给 Cursor Composer 执行真实 LLM 评测。  
> 目标：使用仓库根目录 `.env` 中的 DeepSeek/OpenAI-compatible 配置，运行真实 `LLMDeveloperAgent`，产出可审计的 `Mock LLM: False` 评测报告。  
> 环境：Windows PowerShell，conda env `coding-agent`。  
> 阶段定位：这是 Phase 6 之后、Phase 7 之前的真实模型验证，不是最终包装阶段。

---

## 0. 安全红线

`.env` 里可能有真实 API key。执行时必须遵守：

- 不要打印 `.env` 内容。
- 不要把 API key 写入 README、报告、trace、JSON、Markdown、测试文件或代码。
- 不要在命令行里显式写 key。
- 不要把 key 粘贴进 commit message、聊天回复或日志。
- 如果要检查 key 是否存在，只输出布尔值，不输出原文、前后缀或可恢复片段。

允许读取的环境变量名：

```text
LLM_PROVIDER
LLM_BASE_URL
LLM_MODEL
LLM_API_KEY
LLM_TIMEOUT_SECONDS
```

以 `.env` 中的实际配置为准。不要把模型名、base url 或 key 写死进代码。

---

## 1. 当前状态

已完成：

- LLM client：`reposkill_agent/llm/client.py`
  - OpenAI-compatible `/v1/chat/completions`
  - 默认读取 `LLM_API_KEY / LLM_BASE_URL / LLM_MODEL`
  - `response_format={"type": "json_object"}`
  - 记录 HTTP/network/parse error 和 token 估算
- LLM developer：`reposkill_agent/agents/llm_developer.py`
  - 真实模型生成 full-file edits
  - 限制可修改路径
  - 记录 parse/reject/apply/call/token metrics
- LLM ablation runner：`scripts/run_llm_ablation.py`
  - 支持 L0-L5：
    - `L0_llm_single`
    - `L1_llm_planner`
    - `L2_llm_multi`
    - `L3_llm_skill`
    - `L4_llm_memory`
    - `L5_llm_full`
  - 支持 `--mock-llm`，但本任务禁止使用它

当前缺口：

- 已有 `reports/llm/*` 大概率还是 mock run。
- 需要至少一份真实 API run：`Mock LLM: False`。

---

## 2. 执行边界

本任务优先跑通真实 LLM eval，不做大规模重构。

允许：

- 修 `.env` 中的 provider/base_url/model/timeout 配置。
- 修明显的 LLM prompt/schema/JSON 解析问题。
- 修报告字段或 runner 的小 bug。
- 增加不泄露 key 的诊断信息。

不允许：

- 使用 `--mock-llm` 伪装真实结果。
- 放开所有路径限制来追求更高通过率。
- 把 API key、完整 prompt、完整模型输出塞进公开报告。
- 为了让结果好看修改 benchmark task、expected behavior 或测试断言。

---

## 3. 前置检查

在仓库根目录执行：

```powershell
conda activate coding-agent
```

只做安全 `.env` 检查，不打印值：

```powershell
python -c "from pathlib import Path; p=Path('.env'); text=p.read_text(encoding='utf-8') if p.exists() else ''; print('env_exists', p.exists()); print('has_LLM_API_KEY', 'LLM_API_KEY=' in text); print('has_LLM_BASE_URL', 'LLM_BASE_URL=' in text); print('has_LLM_MODEL', 'LLM_MODEL=' in text)"
```

然后跑本地质量门禁：

```powershell
python -m pytest -o cache_dir=.tmp/pytest_cache --basetemp=.tmp/pytest
python -m ruff check reposkill_agent tests scripts benchmarks
```

通过标准：

- pytest 全绿。
- ruff 无报错。
- 未打印 `.env` 原文。

---

## 4. 真实 LLM Smoke Eval

先只跑 3 个 hard tasks：

```powershell
python scripts/run_llm_ablation.py --tasks benchmarks/tasks/phase6_hard_12.yaml --limit 3 --repeats 1 --seed 42
```

注意：

- 不要加 `--mock-llm`。
- `scripts/run_llm_ablation.py` 会在没有现成 `LLM_API_KEY` 环境变量时自动读取根目录 `.env`。
- 如果 `.env` 缺少 `LLM_API_KEY`，脚本应失败并提示缺少配置；不要改成静默 mock。

Smoke 成功标准：

- 生成 `reports/llm/<run_id>/llm-ablation-summary.md`
- 该 Markdown 中：
  - `Mock LLM: False`
  - `Task count: 3`
  - 表格中 `llm_calls` 大于 0
- 生成 `reports/llm/<run_id>/llm-ablation-summary.json`
- JSON 中能看到：
  - `llm_call_total`
  - `llm_parse_error_total`
  - `llm_patch_rejected_total`
  - `llm_patch_applied_total`
  - `llm_prompt_tokens_total`
  - `llm_completion_tokens_total`
  - `failure_taxonomy_distribution`

如果 smoke 失败，不要继续跑 full eval。先按第 7 节排查。

---

## 5. 真实 LLM Full Eval

Smoke 通过后，跑完整 12 个 hard tasks：

```powershell
python scripts/run_llm_ablation.py --tasks benchmarks/tasks/phase6_hard_12.yaml --repeats 1 --seed 42
```

验收重点：

- `Mock LLM: False`
- `Task count: 12`
- `L5_llm_full` 是否优于或至少不显著弱于 `L0_llm_single`
- `L3_llm_skill` 相比无 skill 配置是否减少失败或提高成功率
- `L4_llm_memory / L5_llm_full` 是否出现 `memory_useful_total`
- `llm_parse_error_total` 是否可控
- `llm_patch_rejected_total` 是否主要来自合理的路径保护
- failure taxonomy 是否能解释失败原因

不要把单次真实 LLM 结果包装成统计显著结论。这里只能作为机制有效性的 smoke/full evidence。

---

## 6. 可选：Seeded Memory Eval

如果 full eval 正常，再补 seeded memory run：

```powershell
python scripts/run_llm_ablation.py --tasks benchmarks/tasks/phase6_hard_12.yaml --repeats 1 --seed 42 --seed-memory
```

目的：

- 看长期/过程 memory 是否能在相同任务分布下积累收益。
- 如果没有收益，也要如实记录为 negative result。

---

## 7. 常见失败处理

### 7.1 `http_error`

优先检查 `.env`，但不要打印 key：

- `LLM_BASE_URL` 是否是 provider 接受的 OpenAI-compatible endpoint。
- `LLM_MODEL` 是否是 provider 接受的模型 id。
- `LLM_API_KEY` 是否有效。

处理原则：

- 只改 `.env` 或 provider 配置。
- 不要把 key 写进代码。
- 不要因为 `http_error` 自动切到 mock。

### 7.2 `network_error`

可能原因：

- 网络不可达。
- base url 不通。
- 代理或防火墙问题。
- provider 临时不可用。

处理原则：

- 只重复最小 smoke，不要直接跑 12 tasks。
- 记录错误类型和时间。

### 7.3 `llm_parse_error`

说明模型没有稳定输出 JSON object。

可修：

- 强化 `build_system_prompt()` 的 JSON-only 约束。
- 在 prompt 中加入更明确的 schema 示例。
- 保持 temperature 为 0。
- 保持 `response_format={"type": "json_object"}`。

修完后必须重跑：

```powershell
python -m pytest -o cache_dir=.tmp/pytest_cache --basetemp=.tmp/pytest
python -m ruff check reposkill_agent tests scripts benchmarks
python scripts/run_llm_ablation.py --tasks benchmarks/tasks/phase6_hard_12.yaml --limit 3 --repeats 1 --seed 42
```

### 7.4 `patch_rejected_path_scope`

说明模型想改的文件不在允许范围内。

优先检查：

- task 的 `expected_files` 是否覆盖真实目标文件。
- locator 是否命中目标文件。
- prompt 是否明确要求只改 allowed paths。

不要直接放开到全仓库写权限。路径约束是项目可靠性证据的一部分。

### 7.5 LLM 有 patch 但测试失败

检查对应 run 的 trace 和 workspace diff：

- patch 是否漏 import。
- full-file rewrite 是否误删原有逻辑。
- 失败是否需要多文件修改，但 task 只允许了单文件。
- 测试错误是否暴露 prompt 中缺少的 repo context。

只做最小修复，并记录修复点。

---

## 8. 交付给我看的结果

执行完成后，请给出这份摘要，不要粘贴 API key：

```text
pytest:
ruff:

Smoke run id:
Smoke Mock LLM:
Smoke Task count:
Smoke L0 success:
Smoke L3 success:
Smoke L5 success:
Smoke llm calls:
Smoke parse errors:
Smoke patch rejected:
Smoke main failures:

Full run id:
Full Mock LLM:
Full Task count:
Full L0 success:
Full L3 success:
Full L5 success:
Full llm calls:
Full parse errors:
Full patch rejected:
Full prompt tokens:
Full completion tokens:
Full main failures:

是否建议进入 Phase 7:
主要 blocker:
需要补强的代码/文档:
```

如果 smoke 没过，只填 smoke 失败信息和 blocker，不要跑 full。

---

## 9. Phase 7 准入标准

满足下面条件后，才建议进入 Phase 7：

- 至少有一份 `Mock LLM: False` 的 smoke 报告。
- 最好有一份完整 `phase6_hard_12.yaml` 的真实 LLM 报告。
- 报告中包含真实 `llm_calls`、parse error、patch reject、token estimate、failure taxonomy。
- README 能明确区分三类证据：
  - fake plumbing eval
  - deterministic mechanism eval
  - real LLM eval
- 没有 API key 或敏感请求内容泄露到报告、trace、README 或代码。

---

## 10. 可直接发给 Composer 的提示词

```text
请执行仓库根目录的 REAL-LLM-DEEPSEEK-EVAL-RUNBOOK.zh-CN.md。

使用 conda env coding-agent，并使用本地 .env 中的 DeepSeek/OpenAI-compatible 配置跑真实 LLM eval。严禁打印或写入 API key，严禁使用 --mock-llm。

先执行：
python -m pytest -o cache_dir=.tmp/pytest_cache --basetemp=.tmp/pytest
python -m ruff check reposkill_agent tests scripts benchmarks

然后执行真实 smoke：
python scripts/run_llm_ablation.py --tasks benchmarks/tasks/phase6_hard_12.yaml --limit 3 --repeats 1 --seed 42

确认最新 reports/llm/<run_id>/llm-ablation-summary.md 中 Mock LLM 为 False，Task count 为 3，llm_calls 大于 0。

如果 smoke 通过，再执行：
python scripts/run_llm_ablation.py --tasks benchmarks/tasks/phase6_hard_12.yaml --repeats 1 --seed 42

最后按文档第 8 节输出摘要，判断是否建议进入 Phase 7。不要输出 .env 内容或 API key。
```
