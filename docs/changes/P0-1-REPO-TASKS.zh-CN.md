# P0-1 高质量 Repo 任务改进记录

## 状态

已完成第一批最小交付：新增分层 repo 级评测任务，并为这些任务补充必要的 fixture 加载与组合裁判能力。

本记录只覆盖第一个缺陷：“评测集偏玩具化”。没有继续推进 `--runs`、统计显著性、Planner、Context 或 Agent-as-Tool。

## 改动范围

### 新增数据集

- `datasets/repo_tasks.json`

包含 8 个 repo 级任务：

| 难度 | 任务数 | 任务 |
|---|---:|---|
| easy | 3 | `easy_math_bug`, `easy_config_json`, `easy_remove_debug` |
| medium | 3 | `medium_rename_symbol`, `medium_validation_bug`, `medium_todo_feature` |
| hard | 2 | `hard_cross_file_api`, `hard_report_transform` |

### 新增 fixtures

- `tests/fixtures/repos/easy_math_bug/`
- `tests/fixtures/repos/easy_config_json/`
- `tests/fixtures/repos/easy_remove_debug/`
- `tests/fixtures/repos/medium_rename_symbol/`
- `tests/fixtures/repos/medium_validation_bug/`
- `tests/fixtures/repos/medium_todo_feature/`
- `tests/fixtures/repos/hard_cross_file_api/`
- `tests/fixtures/repos/hard_report_transform/`

这些 fixture 都是小型本地 Python/JSON/CSV 项目，不依赖网络或额外第三方包。

### EvalRunner 配套能力

修改 `src/eval/runner.py`：

- 支持任务字段 `fixture_dir`，运行任务前复制 fixture 到临时 workspace。
- 新增 `file_not_contains` 裁判。
- 新增 `command_success` 裁判。
- 新增 `pytest_passes` 裁判别名。
- 新增 `multi_assert` 组合裁判。
- 保持原有 `mini_tasks.json` 的 `initial_files` 和旧裁判兼容。

### 测试

修改 `tests/test_runner.py`：

- 覆盖 `file_not_contains`。
- 覆盖 `command_success`。
- 覆盖 `multi_assert`。
- 覆盖 `_copy_fixture_dir`。

## 验证命令

建议运行：

```bash
python -m pytest tests/test_runner.py -q
```

可选验证数据集可加载：

```bash
python -c "import json; data=json.load(open('datasets/repo_tasks.json', encoding='utf-8')); print(len(data['tasks']))"
```

真实 Agent 评测仍需要 LLM API：

```bash
python scripts/run_eval.py --dataset datasets/repo_tasks.json --configs baseline
```

## 回退方式

如需回退本阶段改动：

1. 删除 `datasets/repo_tasks.json`。
2. 删除 `tests/fixtures/repos/` 下本次新增的 8 个 fixture 目录。
3. 在 `src/eval/runner.py` 中移除：
   - `fixture_dir` 复制逻辑
   - `_copy_fixture_dir`
   - `_check_expected`
   - `_check_file_not_contains`
   - `_check_command_success`
   - `multi_assert` / `pytest_passes` 分支
4. 在 `tests/test_runner.py` 中删除 `TestEnhancedJudges`。

## 下一步建议

下一阶段应进入 P0-2/P0-3：

1. 清洗现有 `mini_tasks.json` 中弱裁判任务。
2. 增加 `run_eval.py --runs`。
3. 报告输出均值和标准差。

不要在下一步直接进入 Planner 或 Agent-as-Tool，先把评测闭环继续打稳。
