# P0-2 裁判系统增强记录

## 状态

已完成第二步最小交付：增强 eval 裁判能力，并清洗 `mini_tasks.json` 中 5 个弱裁判任务，降低关键词匹配导致的假阳性。

本阶段没有实现 `--runs`、bootstrap CI、Planner、Context 或 Agent-as-Tool。

## 改动范围

### EvalRunner 新增裁判

修改 `src/eval/runner.py`：

- `json_equals`
  - 读取目标 JSON 文件并与期望结构做精确比较。
  - JSON 语法错误会判定失败。
- `regex_match`
  - 对目标文件内容执行正则匹配。
  - 默认启用 `re.MULTILINE`。
  - 可通过 `dotall: true` 启用 `re.DOTALL`。

沿用上一阶段已加入的：

- `file_not_contains`
- `command_success`
- `pytest_passes`
- `multi_assert`

### 测试

修改 `tests/test_runner.py`：

- 增加 `json_equals` 正反例。
- 增加 `regex_match` 正反例。

### 清洗 mini_tasks 弱裁判

修改 `datasets/mini_tasks.json` 中 5 个任务：

| 任务 | 原裁判 | 新裁判 |
|---|---|---|
| `file_create_config` | `file_contains` | `json_equals` |
| `file_create_json_array` | `file_contains` | `json_equals` |
| `file_modify_fix_json` | `file_contains` | `json_equals` |
| `file_modify_delete_line` | `file_contains` | `multi_assert` + `file_not_contains` |
| `file_modify_escape_quotes` | `file_contains` | `multi_assert` + `regex_match` |

## 验证命令

建议运行：

```bash
python -m pytest tests/test_runner.py -q --basetemp .pytest_tmp
```

校验数据集 JSON：

```bash
python -m json.tool datasets/mini_tasks.json
```

确认目标裁判类型：

```bash
python -c "import json; data=json.load(open('datasets/mini_tasks.json', encoding='utf-8')); ids=['file_create_config','file_create_json_array','file_modify_fix_json','file_modify_delete_line','file_modify_escape_quotes']; tasks={t['id']:t for t in data['tasks']}; [print(i, tasks[i]['expected']['type']) for i in ids]"
```

## 回退方式

如需回退本阶段改动：

1. 在 `src/eval/runner.py` 中移除：
   - `import re`
   - `json_equals` 分支
   - `regex_match` 分支
   - `_check_json_equals`
   - `_check_regex_match`
2. 在 `tests/test_runner.py` 中移除：
   - `test_json_equals`
   - `test_regex_match`
3. 将 `datasets/mini_tasks.json` 中上述 5 个任务的 expected 恢复为原 `file_contains`。

## 下一步建议

下一步进入 P0-3：多次运行统计稳定性。

建议最小实现：

- `scripts/run_eval.py` 增加 `--runs N`
- 保持 `runs=1` 兼容当前报告
- `runs>1` 时输出 success rate、avg steps、avg time、tool failure rate 的 mean/std

不要在 P0-3 前进入 Planner 或 Agent-as-Tool。
