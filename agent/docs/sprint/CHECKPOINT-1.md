# CHECKPOINT-1（2026-09-24）

停在这里，等审计。第 5 步没有执行。

## 提交（pre-memory-rebuild..HEAD）

tag `pre-memory-rebuild` 指向基线 `22305bd baseline snapshot 2026-09-24`。其后：

- `da29c0a` 盘点运行路径和 11 条源记忆
- `bf92d0a` 接入 grader 状态映射（文件还不存在，全部 `unverified`）
- `f511b99` 规则提炼 11 张记忆卡
- `58f2566` BM25 检索和 B0–B3 插件

## 两张渲染样例

`django__django-10914`：

```
[historical attempt on a different issue in this repo; status=unverified — use as navigation hints, not as the answer]
repo: django/django @ e7fd69d051ea
source: django__django-10914
issue: Set default FILE_UPLOAD_PERMISSION to 0o644. Description Hello, As far as I can see, the File Uploads documentation page does not mention any permission issues.
files: django/conf/global_settings.py, docs/ref/settings.txt, docs/releases/3.0.txt, tests/test_utils/tests.py
tests: (none recorded)
pitfalls: git: not found (exit 127)
approach: Edited 4 paths (global_settings.py, settings.txt, 3.0.txt, test_utils/tests.py). Issue asks for default FILE_UPLOAD_PERMISSION 0o644. Diff text is not included.
```

`pytest-dev__pytest-5103`：

```
[historical attempt on a different issue in this repo; status=unverified — use as navigation hints, not as the answer]
repo: pytest-dev/pytest @ 10ca84ffc56c
source: pytest-dev__pytest-5103
issue: Unroll the iterable for all/any calls to get better reports.
files: src/_pytest/assertion/rewrite.py, src/_pytest/assertion
tests: (none recorded)
pitfalls: (none recorded)
approach: Edited src/_pytest/assertion/rewrite.py. Also listed src/_pytest/assertion. Diff text is not included.
```

轨迹里的 `run_command` 没有参数，所以测试命令大多是空的。

## 20 道目标题的离线检索

同一排序器，`min_score=1.0`，`max_bytes=4096`。B1 注入截断轨迹，一条往往就顶满字节，所以 B1 比 B2 选得少。B3 的排序和 B2 相同，但这次没有目标仓库检出，依赖路径都不存在，因此凡是排上了的卡都被标成 `rejected_invalid`，实际注入为空。`sympy-20154` 和 4 道 sphinx 在阈值下一条都选不到。

| 目标题 | 排序（分数） | B1 注入 | B2 注入 | B3 注入 |
|---|---|---|---|---|
| django-13265 | 10924 42.79；11039 10.52；10914 1.56 | 10924 | 三条都注入 | 无 |
| django-15781 | 10914 6.95；11039 1.73 | 10914 | 两条 | 无 |
| django-13590 | 10924 3.60；10914 1.56 | 10924 | 两条 | 无 |
| django-13448 | 11039 15.41；10924 14.61；10914 12.02 | 11039 | 三条 | 无 |
| sympy-20154 | 无 | 无 | 无 | 无 |
| sympy-24152 | 11400 7.87；12171 5.29 | 11400 | 两条 | 无 |
| sympy-20442 | 12171 1.52 | 12171 | 12171 | 无 |
| sympy-18532 | 11400 1.94 | 11400 | 11400 | 无 |
| sklearn-25747 | 10949 54.31；10297 16.20；11040 7.40；11281 2.43 | 10949 | 10949、10297 | 无 |
| sklearn-25500 | 10949 23.23；10297 23.01；11040 7.79；11281 2.91 | 10949 | 10949、10297 | 无 |
| sklearn-25638 | 10949 52.20；10297 11.69；11040 6.55；11281 1.87 | 10949 | 10949、10297 | 无 |
| sklearn-25570 | 10949 33.12；10297 21.56；11040 7.73；11281 1.87 | 10949 | 10949、10297 | 无 |
| pytest-8365 | 5221 7.11；5103 1.94 | 5221 | 两条 | 无 |
| pytest-7432 | 5221 6.99；5103 6.10 | 5221 | 两条 | 无 |
| pytest-9359 | 5221 11.21；5103 9.18 | 5221 | 两条 | 无 |
| pytest-7220 | 5221 11.96；5103 4.56 | 5221 | 两条 | 无 |
| sphinx-10451 / 8721 / 8595 / 8713 | 无 | 无 | 无 | 无 |

## 给 harness 的新入口

```python
load_memory_cards(path) -> tuple[MemoryCard, ...]
MemoryCardPlugin(variant, cards, repo, issue, target_root, max_bytes=4096, min_score=1.0)
await plugin.decide(policy_input) -> dict
```

返回字段与 `A5PublicMemoryPlugin` 相同。harness 侧通常只把 `register_public_memory` 的工厂从 `A5PublicMemoryPlugin` 换成 `MemoryCardPlugin`，并改用 `load_memory_cards`。旧入口仍可用。本仓库没有改 coding-harness。

## 第 5 步方案（不执行）

现在 11 张卡：django 3、sympy 2、scikit-learn 4、pytest 2、sphinx 0。建议等 harness 的 B0 变稳之后，再造轨迹。源题不能和 20 个目标题重叠。

优先补这 13 条（都已在 SWE-bench Lite 公开清单里，且不是目标题）：

- 已列入旧 memory build、但没进当前 11 条的：`django-11001`、`django-11019`、`sympy-11870`、`sympy-11897`、`sympy-12236`、`sklearn-10508`、`pytest-5227`、`pytest-5413`、`pytest-5495`
- sphinx 四条：`sphinx-10325`、`sphinx-7686`、`sphinx-7975`、`sphinx-8273`

费用参照已有一条 django 轨迹：24 次调用，0.244 CNY。13 条各跑 1 次大约 3.2 CNY；若每条允许重试 1 次，上限约 6.5 CNY。这一步要调真实模型，超过本计划默认的 3 CNY 观察线，所以没有执行。
