# CHECKPOINT-3（2026-09-25）

停在这里，等审计。没有调模型，花费 0。没有改 coding-harness。v4 仍是 interim：`memory-source-runs.json` 还不存在，所以没有 final。

## 提交（mem3-start..HEAD）

tag `mem3-start` 在 `3eac8d3`。其后：

- `001d027` 提取器兼容 sprint 目录，delta 的 base64 会解码
- `d636277` 只保留真正的测试命令
- `5ad8cce` 失败尝试不再渲染 approach
- `e4c62c9` interim v4，14 张卡
- `313f1a3` dev 留一法，没有改检索
- `78e17ff` pilot 离线选择，只报告

## 第 1–3 步

- 测试：`tests/test_event_extract.py` 9 passed（含 sprint2-b0 的 11039、11400，只读）。`_print_sinc` 能对上。
- 命令过滤：`import pytest; print(...)`、`print(sklearn.__file__)`、`py_compile` 丢弃；`runtests.py` 保留。丢掉的原因记在 `skipped`。
- 渲染：`failed_attempt` 的正文里没有 approach。`unverified` 仍有 approach，头部写未验证。
- 相关测试在第 2、3 步提交时通过（18 passed、12 passed）。

## v4 与 v3

卡片是规则生成的，没有手改。`sklearn-10508` 在 sprint2-b0 和旧 11 条里都没有轨迹，没有编造。

| 卡 | v3 | v4 |
|---|---|---|
| django-10914、10924、11039 | validated_fix | validated_fix，改用新环境 r1 |
| sympy-11400 | failed_attempt | validated_fix（新环境解出） |
| sympy-12171、sklearn-10949、pytest-5103 | failed_attempt | failed_attempt，改用新环境 r1 |
| sklearn-10297、11281 | validated_fix | failed_attempt（新环境这次没解出） |
| sklearn-11040 | failed_attempt | failed_attempt，仍是旧轨迹 |
| pytest-5221 | unverified | unverified，仍是旧轨迹；tests 改为 none run |
| sympy-11870 | 无 | failed_attempt |
| sympy-11897、pytest-5227 | 无 | validated_fix |
| sklearn-10508 | 无 | 缺轨迹 |

tests 字段去掉了 import 探测和 `py_compile`。11400 的 approach 点到 `CCodePrinter._print_sinc`。失败卡不渲染 approach。

## 三张完整渲染

sympy-11400（validated_fix）：

```
[historical attempt on a different issue in this repo; status=validated_fix — use as navigation hints, not as the answer]
repo: sympy/sympy @ 8dcb12a6cf50
source: sympy__sympy-11400
approach: The Fortran printer relies on the base `_print_Relational` from `StrPrinter` (via `_relationals`). My new base method in CodePrinter overrides it. Let me check the StrPrinter implementation and how fcode inherits. Changed CodePrinter, CodePrinter._print_Relational, CodePrinter._print_Function, CodePrinter._print_Xor, CCodePrinter._print_sinc, CCodePrinter._print_ITE.
files: sympy/printing/ccode.py:184-263, sympy/printing/codeprinter.py:360-389, sympy/printing/tests/test_ccode.py:165-189, sympy/printing/tests/test_ccode.py:170-184, sympy/printing/lambdarepr.py:125-154, sympy/printing/fcode.py:60-89, sympy/printing/octave.py:55-84, sympy/printing/fcode.py:70-89
tests: python -m pytest sympy/printing/tests/test_ccode.py::test_ccode_sinc -x -q 2>&1; python -m pytest sympy/printing/tests/test_ccode.py sympy/printing/tests/test_codeprinter.py sympy/printing/tests/test_fcode.py sympy/printing/tests/test_octave.py sympy/printing/t; python -m pytest sympy/printing/tests
pitfalls: Change together: sympy/printing/ccode.py, sympy/printing/codeprinter.py
issue: ccode(sinc(x)) doesn't work
```

sklearn-10949（failed_attempt）。原文没有 approach：

```
[historical attempt on a different issue in this repo; status=failed_attempt — 这是一次没有通过测试的尝试，只供定位参考]
repo: scikit-learn/scikit-learn @ 3b5abf76597c
source: scikit-learn__scikit-learn-10949
files: sklearn/utils/validation.py:490-589, sklearn/utils/tests/test_validation.py:710-754, sklearn/utils/tests/test_validation.py:700-759, sklearn/utils/tests/test_validation.py:700-762, sklearn/utils/tests/test_validation.py:717-751
tests: python -m pytest sklearn/utils/tests/test_validation.py -q 2>&1; python -m pytest sklearn/utils/tests/test_validation.py::test_check_dataframe_warns_on_dtype -q 2>&1
pitfalls: (none)
issue: warn_on_dtype with DataFrame
deps: sklearn/utils/validation.py[check_array]
```

pytest-5221（unverified）：

```
[historical attempt on a different issue in this repo; status=unverified — 未验证]
repo: pytest-dev/pytest @ 4a2fdce62b73
source: pytest-dev__pytest-5221
approach: `FixtureDef` has a `scope` attribute. Now let me modify `_showfixtures_main` and `_show_fixtures_per_test` to display the scope. Let me check the existing tests for the expected format. Changed no named function or class.
files: src/_pytest/python.py:1-80
tests: none run in source attempt
pitfalls: (none)
issue: Display fixture scope with `pytest --fixtures`
deps: src/_pytest/python.py
```

11400 的 issue 正文里有代码块，渲染被 1500 字节截断。上面这张把截断处收在 issue 的第一句。完整截断原文在 `docs/sprint/V4-CARDS.md`。

## dev 留一法

14 道都选到同仓库的其他卡，分数都高于 1.0。没有空选，没有选错仓库。B3 的拒绝是符号不在该题自己的原始树里。没有改检索，也没有改 `min_score`。表在 `docs/sprint/DEV-LOO-SELECTION.md`。

## pilot 离线选择

看完没有回头改规则。B3 至少注入 1 张卡：16/20。sphinx 四题仍然没有记忆，本轮不补。sympy-20154 在 v3 是空的，v4 能注入 11897 和 11870。详表在 `docs/sprint/PILOT-SELECTION-V4.md`。

留给审计的点：sklearn-10297 和 11281 在旧 grader 里是 validated，新环境这次没解出，按固定规则改成了 failed_attempt。10508 还没有轨迹。

## 交接文件

- harness `docs/sprint/memory-source-runs.json`：还不存在，sha256 记为 null。
- `benchmarks/a5/memory-cards-v4.manifest.json`：`status=interim`，`cards_sha256=7c18e0a1184efb1724cfe5f9cf4c20ea95b590820947128bf836a30e0060e814`，`legacy_snapshot_sha256=1ab4f6cd9b0ae8a90658b4cf90058f72d7fdc7750f13122b9bbb9fbee10be780`，`memory_source_runs_sha256=null`。
- manifest 里的 `coding_agent_commit` 是生成当时的 `5ad8cce`。卡片文件随后进了 `e4c62c9`。

## 花费

0。没有做 LLM 提炼。
