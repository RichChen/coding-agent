# 记忆盘点（2026-09-24）

快照：`coding-harness/docs/upgrade/evidence/A5-real240-77-harness-preflight/memory-snapshot.jsonl`（11 行）。本仓库没有副本。

## 实验里真正走到的入口

- `memory/public_runtime_view.py`：harness 调用的入口。`load_public_episodes` 读快照行，再读各源目录的 `public-trajectory.json`，硬性要求正好 11 条。`A5PublicMemoryPlugin.decide` 用词交集选最多 2 条。B1 注入截断 JSON，B2 注入动作列表 JSON，B3 只检查改过的文件是否存在。不使用 `MemoryRecord`、`gate.py`、`validity.py`、`record_store.py`、`dependency_index.py`。
- `integrations/harness_h4.py`：另一条 H4 适配器。`decide` 调 `evidence/strategy.py` 的 `plan_public_step`，那里会走 `gate.select_memory` 和 `validity.check_validity`。输入是调用方事先放进来的 `MemoryRecord`，不读这 11 条快照。
- `memory/lightweight_snapshot.py`：`eval/graph_runner.py` 在配置了快照时加载。只保留合同允许的哈希字段，注入的是引用，不是轨迹正文。

## 离线能力（demo、fixture、单测）

| 模块 | 能做什么 | 谁在用 |
|---|---|---|
| `records.py` | `MemoryRecord`：过程文本、依赖、验证证据、密钥筛查 | 单测、`upgrade_demo`、`experiments/`、H4 类型 |
| `builder.py` | 从公开轨迹规则抽出 candidate，不自动晋升 | `upgrade_demo`、`experiments/offline.py` |
| `gate.py` | 词重叠检索 + 有效性过滤 + 注入回执 | `upgrade_demo`、`evidence/strategy.py` |
| `validity.py` | 用宿主提供的事实核对包版本、文件哈希、API 签名 | `gate`、`experiments/variants.py` |
| `record_store.py` | 按 memory_id 存取记录 | `upgrade_demo`、`migration.py` |
| `dependency_index.py` | 按依赖键反查会受影响的记录 | 仅 `test_memory_validity.py` |
| `eval/upgrade_demo.py` | 把上面几件串成离线演示 | 集成测试 |

第 3、4 步复用 `MemoryRecord` 所在模块，以及 `validity.py` / `gate.py` 的检查结果类型。运行时注入改走新入口，旧的 `load_public_episodes` 和 `A5PublicMemoryPlugin` 保持不动。

## 11 条源记忆

轨迹字段全部相同：`issue_summary`、`public_evidence`、`actions`（`tool` 或 `tool:path`）、`public_verification`、`failure_notes`。`run_command` 不带参数。同目录还有 `candidate-delta.json`，运行时没读。`failure_notes` 这 11 条都是空的。

| source_id | repo | base_revision | 源目录 |
|---|---|---|---|
| django__django-10914 | django/django | e7fd69d051ea | `.../A5-memory-pool-75-s1-smoke/django__django-10914-reverify` |
| django__django-10924 | django/django | bceadd2788dc | `.../A5-memory-pool-75-s1-smoke/django__django-10924-reverify` |
| django__django-11039 | django/django | d5276398046c | `.../A5-memory-pool-76-s2/builds/django__django-11039` |
| sympy__sympy-11400 | sympy/sympy | 8dcb12a6cf50 | `.../A5-memory-pool-75-s1-smoke/sympy__sympy-11400-reverify` |
| sympy__sympy-12171 | sympy/sympy | ca6ef27272be | `.../A5-memory-pool-76-s2/builds/sympy__sympy-12171` |
| scikit-learn__scikit-learn-10297 | scikit-learn/scikit-learn | b90661d6a46a | `.../A5-memory-pool-75-s1-smoke/scikit-learn__scikit-learn-10297-reverify` |
| scikit-learn__scikit-learn-10949 | scikit-learn/scikit-learn | 3b5abf76597c | `.../A5-memory-pool-76-s2/builds/scikit-learn__scikit-learn-10949` |
| scikit-learn__scikit-learn-11040 | scikit-learn/scikit-learn | 96a02f393495 | `.../A5-memory-pool-76-s2/builds/scikit-learn__scikit-learn-11040` |
| scikit-learn__scikit-learn-11281 | scikit-learn/scikit-learn | 4143356c3c51 | `.../A5-memory-pool-76-s2/builds/scikit-learn__scikit-learn-11281` |
| pytest-dev__pytest-5103 | pytest-dev/pytest | 10ca84ffc56c | `.../A5-memory-pool-75-s1-smoke/pytest-dev__pytest-5103-reverify` |
| pytest-dev__pytest-5221 | pytest-dev/pytest | 4a2fdce62b73 | `.../A5-memory-pool-76-s2/builds/pytest-dev__pytest-5221` |

路径前缀都是 `D:/crq/src/coding-harness/docs/upgrade/evidence/`。
