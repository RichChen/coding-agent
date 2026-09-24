# RepoSkillAgent 代码库结构详解（目录 + 文件级说明）

> 目的：给“深入读代码”阶段提供一份可直接对照的结构地图。  
> 范围：覆盖当前仓库主要子目录与文件职责；对海量生成产物目录采用“结构规则 + 关键文件”说明。  
> 说明：本文件**不改动任何现有代码**，仅做阅读导览。

---

## 1. 仓库顶层总览

### 1.1 顶层目录

- `reposkill_agent/`：主代码包（核心逻辑）
- `benchmarks/`：评测任务定义与本地 benchmark 仓库
- `scripts/`：可执行脚本入口（baseline / graph / ablation）
- `tests/`：pytest 测试
- `configs/`：默认配置
- `docs/`：项目文档、证据、案例、交接
- `reports/`：评测报告产物（按 run_id 组织）
- `traces/`：运行 trace、工作区临时目录
- `.tmp/`：临时测试目录（pytest basetemp/cache）

### 1.2 顶层关键文件

- `README.md`：项目首页与最终主结果（Batch 5.10）
- `pyproject.toml`：依赖、脚本入口、pytest/ruff 配置
- `PROJECT-PLAN-OpenHands-RepoSkillAgent.zh-CN.md`：总计划
- `PHASE6-EVAL-STRENGTHENING-PLAN.zh-CN.md`：Phase 6 计划
- `LLM-DEEPSEEK-INTEGRATION-PLAN.zh-CN.md`：LLM 接入计划
- `PHASE7_1-POSITIVE-GAIN-HARDENING-PLAN.zh-CN.md`：Phase 7.1 执行计划
- `REAL-LLM-DEEPSEEK-EVAL-RUNBOOK.zh-CN.md`：真实评测运行手册
- `NEW-PROJECT-BRIEF.zh-CN.md`：项目背景与定位简报
- `paper-*.pdf`：参考论文
- `.env`：本地私密配置（API key 等，勿提交）
- `.gitignore`：忽略规则

---

## 2. `reposkill_agent/`（主代码包）

> 这是你阅读时最核心的目录。建议顺序：`eval` -> `agents` -> `llm` -> `skills` -> `memory`。

### 2.1 包入口与CLI

- `reposkill_agent/__init__.py`：包说明与导出入口
- `reposkill_agent/__main__.py`：`python -m reposkill_agent` 入口
- `reposkill_agent/cli.py`：Typer CLI 主入口

### 2.2 `adapters/`（执行环境抽象）

- `adapters/__init__.py`：导出适配器模块
- `adapters/base.py`：`WorkspaceAdapter` 抽象接口定义
- `adapters/fake_adapter.py`：本地 deterministic 假适配器（测试/离线）
- `adapters/openhands_adapter.py`：OpenHands SDK 适配层（可选）

### 2.3 `agents/`（角色代理）

- `agents/__init__.py`：角色代理导出
- `agents/contracts.py`：角色代理输入输出契约
- `agents/manager.py`：管理节点（inspect/summarize）逻辑
- `agents/locator.py`：定位节点（文件/符号/上下文扩展）逻辑
- `agents/developer.py`：deterministic 开发代理
- `agents/llm_developer.py`：LLM 开发代理（PatchPlan / repair / error type）
- `agents/qa.py`：测试与结果检查
- `agents/memory_curator.py`：从 run 结果提炼 procedural memory

### 2.4 `core/`（核心数据结构与运行基础）

- `core/__init__.py`：core 模块导出
- `core/contracts.py`：核心契约（TaskSpec、GraphRunResult、GraphMetrics 等）
- `core/task_graph.py`：任务图节点模型
- `core/planner.py`：deterministic planner 与 replan 决策
- `core/trace.py`：JSONL trace 写入
- `core/context_expansion.py`：`needs_more_context` 路径扩展逻辑

### 2.5 `llm/`（模型接入层）

- `llm/__init__.py`：llm 模块导出
- `llm/client.py`：OpenAI-compatible 客户端（DeepSeek 等）
- `llm/prompts.py`：提示词构建（skills/memory/context 注入格式）
- `llm/schemas.py`：PatchPlan 结构化 schema

### 2.6 `skills/`（SkillCard 体系）

- `skills/__init__.py`：skills 模块导出
- `skills/models.py`：SkillCard 数据模型（v2）
- `skills/registry.py`：SkillCard 加载与索引
- `skills/retriever.py`：skill 检索
- `skills/validator.py`：evidence/domain/negative-transfer gating
- `skills/domain.py`：domain 匹配规则

#### `skills/library/`（具体 SkillCards）

- `add_regression_test.md`：回归测试补丁思路
- `config_precedence_merge.md`：配置合并优先级
- `event_serializer_compat.md`：事件序列化兼容
- `fix_import_error.md`：导入错误修复
- `handler_registry_api.md`：handler 注册 API 修复
- `inspect_pytest_traceback.md`：pytest traceback 导向修复
- `inventory_tax_api.md`：inventory 税/Result 约定
- `multi_file_api_migration.md`：多文件 API 迁移模式
- `rename_symbol_across_files.md`：跨文件符号重命名
- `repo_result_convention.md`：Result 约定修复
- `retry_policy_semantics.md`：重试策略语义修复
- `update_api_signature.md`：API 签名更新

### 2.7 `memory/`（记忆系统）

- `memory/__init__.py`：memory 模块导出
- `memory/models.py`：MemoryHint v2 模型
- `memory/episodic.py`：episodic 持久化（JSONL + SQLite index）
- `memory/procedural.py`：procedural 持久化（JSONL）
- `memory/repo_profile.py`：repo profile 持久化（JSON）
- `memory/retriever.py`：memory 候选检索、排序、注入裁剪
- `memory/matching.py`：domain/tag 匹配、seed pairing、test signal 提取
- `memory/consolidator.py`：run 结果 -> episodic/procedural/profile 构建器

### 2.8 `eval/`（评测与运行编排）

- `eval/__init__.py`：eval 模块导出
- `eval/runner.py`：single-agent baseline runner
- `eval/graph_runner.py`：TaskGraph 主执行器（PlanAct + role agents）
- `eval/ablation.py`：Phase 6 A0-A5 deterministic ablation runner
- `eval/llm_ablation.py`：L0-L5 真实 LLM ablation runner
- `eval/injection_policy.py`：category-aware 注入路由策略
- `eval/report.py`：评测报告生成（Markdown/聚合统计）
- `eval/task_spec.py`：任务 YAML 加载与 catalog
- `eval/task_category.py`：primary category 判定
- `eval/scripted_fixes.py`：tiny 任务 scripted fix 集合（fake 模式）

### 2.9 `baselines/`（外部对比接口）

- `baselines/__init__.py`：baseline 模块导出
- `baselines/contracts.py`：BaselineRunRequest / Result 契约
- `baselines/vanilla_deepseek.py`：vanilla LLM baseline（L0 风格）
- `baselines/external_command.py`：通用外部命令 baseline 运行器
- `baselines/openhands_sdk.py`：OpenHands baseline（可选、可 skip）
- `baselines/swe_agent.py`：SWE-agent baseline（可选、可 skip）
- `baselines/aider.py`：Aider baseline（可选、可 skip）

---

## 3. `scripts/`（脚本入口）

- `scripts/run_baseline.py`：运行 tiny baseline（single-agent）
- `scripts/run_graph.py`：运行 deterministic graph runner
- `scripts/run_memory_ablation.py`：no-memory vs memory 对比
- `scripts/run_phase6_ablation.py`：A0-A5 ablation 主脚本
- `scripts/run_llm_ablation.py`：L0-L5 ablation 主脚本（支持 repeats/seed/seed-memory）
- `scripts/run_external_baselines.py`：运行 optional 外部 baseline
- `scripts/run_mechanism_smoke.py`：机制烟测（skill/memory/context/repair）

---

## 4. `tests/`（测试）

### 4.1 核心逻辑测试

- `test_contracts.py`：核心契约模型
- `test_planner.py`：planner/replan 行为
- `test_graph_runner.py`：graph runner 执行链路
- `test_agents.py`：角色代理行为
- `test_fake_adapter.py`：fake adapter
- `test_context_expansion.py`：context expansion + repair
- `test_llm_developer.py`：LLM developer 结构化输出与错误处理
- `test_llm_client.py`：LLM client
- `test_llm_call_state.py`：LLM 调用预算状态隔离

### 4.2 评测与基线测试

- `test_ablation.py`：Phase 6 ablation runner
- `test_llm_ablation.py`：LLM ablation runner
- `test_baseline_runner.py`：baseline runner
- `test_external_baselines.py`：外部 baseline 适配与 skip 行为
- `test_phase7_benchmark.py`：phase7 benchmark 健全性
- `test_mechanism_smoke.py`：Batch 4.5 机制烟测

### 4.3 Skill/Memory 专项测试

- `test_skills.py`：registry/retriever/validator 基础
- `test_skill_memory_v2.py`：SkillCard v2 + MemoryHint v2 联动
- `test_injection_policy.py`：category policy 路由
- `test_memory.py`：memory 存取
- `test_memory_matching.py`：matching、seed pairing、signal hint 质量

### 4.4 其他

- `tests/__init__.py`：测试包初始化

---

## 5. `benchmarks/`（任务与测试仓库）

### 5.1 `benchmarks/tasks/`

- `tiny_python_tasks.yaml`：最小 3 任务（baseline 起点）
- `phase6_tiny_24.yaml`：Phase 6 plumbing 集（高重复）
- `phase6_hard_12.yaml`：Phase 6 hard deterministic / early real LLM 集
- `phase7_medium_24.yaml`：Phase 7 主战场（24 tasks）
- `phase7_probe_12.yaml`：Probe 平衡子集（12 tasks）
- `phase7_medium_48.yaml`：最终 medium-48（Batch 5.9/5.10）

### 5.2 `benchmarks/repos/`（各 benchmark 仓库）

#### 5.2.1 tiny/hard 基础仓库

- `fix_import_error/`
  - `conftest.py`
  - `app/calculator.py`
  - `tests/test_calculator.py`
- `fix_off_by_one/`
  - `conftest.py`
  - `app/range_sum.py`
  - `tests/test_range_sum.py`
- `add_greeting_function/`
  - `conftest.py`
  - `app/greet.py`
  - `tests/test_greet.py`
- `update_api_signature/`
  - `conftest.py`
  - `app/__init__.py`
  - `app/math_api.py`
  - `tests/test_math_api.py`
- `rename_symbol/`
  - `conftest.py`
  - `app/__init__.py`
  - `app/processor.py`
  - `tests/test_processor.py`
- `add_regression_test/`
  - `conftest.py`
  - `app/division.py`
  - `tests/test_division.py`
- `parse_pytest_traceback/`
  - `conftest.py`
  - `app/__init__.py`
  - `app/text_utils.py`
  - `tests/test_text_utils.py`

#### 5.2.2 Phase 7 medium 仓库

- `medium_inventory/`
  - `conftest.py`
  - `inventory/__init__.py`
  - `inventory/api.py`
  - `inventory/discounts.py`
  - `inventory/models.py`
  - `inventory/pricing.py`
  - `inventory/validators.py`
  - `tests/test_api_tax.py`
  - `tests/test_api_tax_holdout.py`
  - `tests/test_bulk_pricing.py`
  - `tests/test_bulk_pricing_holdout.py`
  - `tests/test_convention.py`
  - `tests/test_convention_holdout.py`
  - `tests/test_discount_stack.py`
  - `tests/test_discount_stack_holdout.py`
  - `tests/test_regression_cart.py`
  - `tests/test_regression_region.py`
  - `tests/test_rename.py`
  - `tests/test_rename_holdout.py`
  - `tests/test_stock_guard.py`
  - `tests/test_stock_guard_holdout.py`

- `medium_config_loader/`
  - `conftest.py`
  - `config_loader/__init__.py`
  - `config_loader/api.py`
  - `config_loader/defaults.py`
  - `config_loader/env.py`
  - `config_loader/merge.py`
  - `config_loader/schema.py`
  - `config_loader/sources.py`
  - `tests/test_convention.py`
  - `tests/test_default_merge.py`
  - `tests/test_default_merge_holdout.py`
  - `tests/test_env_override.py`
  - `tests/test_env_override_holdout.py`
  - `tests/test_key_alias.py`
  - `tests/test_key_alias_holdout.py`
  - `tests/test_merge_order.py`
  - `tests/test_merge_order_holdout.py`
  - `tests/test_nested_key.py`
  - `tests/test_nested_key_holdout.py`
  - `tests/test_schema_validation.py`
  - `tests/test_type_coerce.py`
  - `tests/test_type_coerce_holdout.py`

- `medium_event_pipeline/`
  - `conftest.py`
  - `events/__init__.py`
  - `events/handlers.py`
  - `events/message.py`
  - `events/pipeline.py`
  - `events/registry.py`
  - `events/serializer.py`
  - `tests/test_context_pipeline.py`
  - `tests/test_deadletter.py`
  - `tests/test_deadletter_holdout.py`
  - `tests/test_fanout.py`
  - `tests/test_fanout_holdout.py`
  - `tests/test_handler_registry.py`
  - `tests/test_handler_registry_holdout.py`
  - `tests/test_payload_filter.py`
  - `tests/test_payload_filter_holdout.py`
  - `tests/test_retry_policy.py`
  - `tests/test_retry_policy_holdout.py`
  - `tests/test_serialization.py`
  - `tests/test_serialization_holdout.py`
  - `tests/test_traceback_fix.py`

- `medium_auth_rules/`
  - `conftest.py`
  - `auth_rules/__init__.py`
  - `auth_rules/api.py`
  - `auth_rules/models.py`
  - `auth_rules/policy.py`
  - `auth_rules/tokens.py`
  - `tests/test_policy_merge.py`
  - `tests/test_policy_merge_holdout.py`
  - `tests/test_role_check.py`
  - `tests/test_role_check_holdout.py`
  - `tests/test_token_format.py`
  - `tests/test_token_format_holdout.py`

- `benchmarks/repos/README.md`：benchmark 仓库说明

---

## 6. `configs/`

- `configs/default.yaml`：默认运行配置（adapter、tasks_file、planner/skill/memory 开关等）

---

## 7. `docs/`（文档目录）

- `docs/current-evidence.md`：证据分层（主证据 vs 历史证据）
- `docs/project-chronology.zh-CN.md`：完整变更历程
- `docs/code-reading-guide.zh-CN.md`：代码阅读顺序与问题模板
- `docs/evaluation-contract.md`：三层评测边界定义
- `docs/case-study-skill-gating.md`：技能门控案例
- `docs/case-study-memory-reuse.md`：记忆复用案例
- `docs/case-study-context-repair.md`：上下文扩展/修复案例
- `docs/limitations.md`：限制与风险披露
- `docs/SESSION-HANDOFF.zh-CN.md`：会话交接状态文档

---

## 8. `reports/`（报告产物）

> 该目录由脚本自动生成，run_id 数量会持续增长；不建议逐文件人工阅读全部内容。

### 8.1 顶层汇总报告

- `reports/phase6-eval-summary.md`
- `reports/phase7-probe-12-summary.md`
- `reports/phase7-full24-failure-analysis.md`
- `reports/phase7-medium48-summary.md`
- `reports/phase7-variance-summary.md`
- `reports/phase7-positive-gain-summary.md`
- `reports/memory-ablation-summary.md`

### 8.2 按 run_id 组织的自动产物

- `reports/llm/<run_id>/`
  - `llm-ablation-summary.json`
  - `llm-ablation-summary.md`
  - `<config>/rows.json`
  - `<config>/traces/...`
  - `<config>/memory/...`（仅 memory 开启配置）
- `reports/phase6/<run_id>/`
  - `ablation-summary.md`
  - 及对应 JSON / traces
- `reports/external_baselines/<run_id>/`
  - `summary.md`

### 8.3 归档目录

- `reports/archive/batch5.7-full24/`
  - `README.md`
  - `llm-ablation-summary.md/json`
  - `phase7-positive-gain-summary.md`
  - `phase7-probe-12-summary-pre58.md`

---

## 9. `traces/`、`.tmp/`、`__pycache__/`（生成目录）

### 9.1 `traces/`

- 运行时 trace JSONL、临时 workspace、pytest 临时输出
- 常见路径：
  - `traces/*.jsonl`
  - `traces/graph_workspaces/...`
  - `traces/.pytest_tmp/`
  - `traces/.pytest_cache/`

### 9.2 `.tmp/`

- 人工指定的 pytest 临时目录（如 `--basetemp=.tmp/pytest`）
- 仅临时缓存，不应纳入逻辑阅读范围

### 9.3 `__pycache__/`

- Python 字节码缓存
- 无业务语义，阅读时可全部忽略

---

## 10. 初次阅读时“先看哪些目录，后看哪些目录”

### 第一优先级（看逻辑）

- `reposkill_agent/eval/`
- `reposkill_agent/agents/`
- `reposkill_agent/llm/`
- `reposkill_agent/skills/`
- `reposkill_agent/memory/`

### 第二优先级（看输入与验收）

- `benchmarks/tasks/`
- `benchmarks/repos/medium_*`
- `tests/`

### 第三优先级（看结果解释）

- `reports/phase7-variance-summary.md`
- `reports/phase7-positive-gain-summary.md`

### 最后看（产物/缓存）

- `reports/llm/<run_id>/traces/...`
- `traces/`
- `.tmp/`
- `__pycache__/`

---

## 11. 一句话记忆版

- **代码主干在** `reposkill_agent/`  
- **任务定义在** `benchmarks/tasks/`  
- **可执行入口在** `scripts/`  
- **正确性保证在** `tests/`  
- **结论证据在** `reports/phase7-*.md`  
- **过程知识在** `docs/`
