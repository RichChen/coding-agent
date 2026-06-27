# P1-1 显式 Planner 最小版记录

## 状态

已完成 P1-1 最小交付：新增显式计划对象，并在 `plan_act` 模式下记录计划创建、状态推进和最终计划状态。

默认 `react` 模式保持不变。

## 改动范围

### Planner 模块

新增 `src/runtime/planner.py`：

- `PlanStatus`
- `PlanStep`
- `Plan`
- `SimplePlanner`

`SimplePlanner` 不额外调用 LLM，只基于任务描述和启用工具生成 3 步确定性计划：

1. 理解任务并检查相关文件
2. 应用修改或使用工具收集答案
3. 运行验证或检查最终状态

### AgentLoop 接入

修改 `src/runtime/loop.py`：

- `AgentRunResult` 增加 `plan` 字段。
- `AgentLoop` 增加：
  - `runtime_mode`
  - `planner`
- `runtime_mode == "plan_act"` 且 planner 存在时：
  - run 开始生成 plan
  - EventBus 发出 `plan_created`
  - 每轮工具执行后推进 plan 状态
  - EventBus 发出 `plan_updated`
  - 正常完成时将所有 plan step 标记为 `done`

### Eval trace metadata

修改 `src/eval/runner.py`：

- `TraceRun.metadata` 增加 `plan`。

### 配置与工厂

修改：

- `src/config/schema.py`
- `src/harness/factory.py`

新增配置：

- `runtime.mode`
- `runtime.planner.enabled`

新增示例配置：

- `configs/plan_act.yaml`

### 测试

新增/修改：

- `tests/test_planner.py`
- `tests/test_agent_loop.py`
- `tests/test_runner.py`

覆盖：

- planner 生成和状态推进
- `plan_act` 模式返回 completed plan
- 默认 `react` 模式没有 plan
- `configs/plan_act.yaml` 能构建 planner

## 非目标

本阶段没有做：

- 额外 LLM planner 调用
- 复杂 DAG
- 自动 replan
- plan 质量评分
- plan 注入 prompt

这些应放到后续 P1 扩展中。

## 验证命令

建议运行：

```bash
python -m pytest tests/test_planner.py tests/test_agent_loop.py tests/test_runner.py -q --basetemp .pytest_tmp
```

配置验证：

```bash
python -c "from src.harness.factory import load_config; print(load_config('configs/plan_act.yaml')['runtime']['mode'])"
```

## 回退方式

如需回退本阶段改动：

1. 删除 `src/runtime/planner.py`。
2. 删除 `tests/test_planner.py`。
3. 删除 `configs/plan_act.yaml`。
4. 从 `src/runtime/loop.py` 移除：
   - `SimplePlanner` / `Plan` import
   - `AgentRunResult.plan`
   - `runtime_mode` / `planner`
   - plan 创建、更新、返回逻辑
5. 从 `src/config/schema.py` 移除：
   - `RuntimePlannerConfig`
   - `RuntimeConfig.mode`
   - `RuntimeConfig.planner`
6. 从 `src/harness/factory.py` 移除 planner 构造。
7. 从 `src/eval/runner.py` 的 trace metadata 移除 `plan`。

## 下一步建议

下一步按方案进入 P1-2：上下文管理 L0/L1 增强。

建议保持同样边界：先补 trace 和统计，不急着做 L2 LLM 总结。
