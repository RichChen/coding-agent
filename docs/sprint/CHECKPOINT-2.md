# CHECKPOINT-2（2026-09-25）

停在这里，等审计。没有调模型，花费 0。没有改 coding-harness，没有造新轨迹。

## 提交（mem2-start..HEAD）

tag `mem2-start` 在 `c4ecbf0`。其后：

- `474ae89` 从 `run/events.jsonl` 提取命令、诊断和改动符号
- `a6f865d` 滤掉旧 transport 镜像的噪声
- `1cd3ae3` 规则生成 `memory-cards-v3.jsonl`，不做 LLM 提炼
- `d31803f` 用目标题 base 源码重跑 B3，路径被挪走但符号还在时记为 `relocated`

## 三张 v3 渲染

django `django-10914`（unverified）：

```
approach: The issue asks to set the default FILE_UPLOAD_PERMISSIONS to 0o644. Changed no named function or class.
files: django/conf/global_settings.py:1-100, docs/ref/settings.txt:1-40, docs/releases/3.0.txt, tests/test_utils/tests.py
tests: python -c 打印 FILE_UPLOAD_PERMISSIONS；python tests/runtests.py test_utils.tests.OverrideSettingsTests.test_override_file_upload_permissions
```

pytest `pytest-5221`（unverified）：

```
approach: FixtureDef has a scope attribute. Modify _showfixtures_main and _show_fixtures_per_test to display the scope. Changed no named function or class.
files: src/_pytest/python.py:1-80
tests: python -c "import pytest; print(pytest.__version__, pytest.__file__)"
pitfalls: (none)
```

sklearn `sklearn-10949`（unverified）：

```
approach: DataFrame has no .dtype (it has .dtypes), so warn_on_dtype never fires. Changed _get_dtype.
files: sklearn/utils/validation.py:1-120
tests: python -c "import sklearn; print(sklearn.__file__)"; python -m py_compile sklearn/utils/validation.py
```

完整原文由 `render_card` 生成，头部仍是 `status=unverified — use as navigation hints, not as the answer`。上面三张为了本页篇幅去掉了重复的 banner 和被截断的 issue 句。

## 11 张卡的字段

| 卡 | tests | approach | pitfalls |
|---|---|---|---|
| django-10914 | 有 runtests.py | 点了 0o644，没对上函数名 | 有，要求文档和设置一起改 |
| django-10924 | none run | 有，`_check_path` | 有 |
| django-11039 | 有 pytest | 有，sqlmigrate 测试名 | 有 |
| sympy-11400 | 有 python -c | 有，`_print_sinc` | 空 |
| sympy-12171 | 有 python -c | 有，`_print_Float` | 有 |
| sklearn-10297 | 有 python -c | 有，`RidgeClassifierCV` | 有 |
| sklearn-10949 | 有 python -c | 有，`_get_dtype` | 空 |
| sklearn-11040 | none run | 有，`n_neighbors` | 空 |
| sklearn-11281 | 有 python -c | 有，`fit_predict` | 空 |
| pytest-5103 | none run | 有，`_visit_all_any` | 空 |
| pytest-5221 | 只有 import pytest | 点了函数名，符号没对上 | 空 |

## 20 题离线选择

B1/B2 排序相同。B1 常常只能注入第一条，因为原文更长。B3「前」是路径缺失即 `invalid`；「后」是缺失但符号还在则 `relocated` 并注入。

| 目标题 | 排序 | B2 注入 | B3 前 | B3 后 |
|---|---|---|---|---|
| django-13265 | 10924 52.3；11039 14.4；10914 10.5 | 10924、11039 | 只注入 10914 | 同左 |
| django-15781 | 10924 23.5；10914 4.2；11039 1.5 | 10924、10914 | 只注入 10914 | 同左 |
| django-13590 | 10924 9.1；10914 7.3；11039 1.8 | 10924、10914 | 只注入 10914 | 同左 |
| django-13448 | 11039 25.6；10924 22.0；10914 14.1 | 11039、10924 | 只注入 10914 | 同左 |
| sympy-20154 | 无 | 无 | 无 | 无 |
| sympy-24152 | 12171 10.7；11400 8.1 | 两条 | 全拒绝 | 同左 |
| sympy-20442 | 12171 3.1 | 12171 | 拒绝 | 同左 |
| sympy-18532 | 12171 7.3；11400 3.6 | 两条 | 全拒绝 | 同左 |
| sklearn-25747 | 10949 56.4；10297 21.6；11040 10.1；11281 8.1 | 10949、10297 | 全拒绝 | 注入 11281（relocated） |
| sklearn-25500 | 10297 27.4；10949 25.1；11281 10.7；11040 6.2 | 10297、10949 | 全拒绝 | 注入 11281 |
| sklearn-25638 | 10949 53.8；10297 12.5；11040 8.1；11281 3.6 | 10949、10297 | 全拒绝 | 注入 11281 |
| sklearn-25570 | 10949 32.7；10297 21.0；11040 12.4；11281 2.4 | 10949、10297 | 全拒绝 | 注入 11281 |
| pytest-8365 | 5103 5.6；5221 4.9 | 两条 | 注入 5221 | 同左 |
| pytest-7432 | 5103 6.7；5221 6.6 | 两条 | 注入 5221 | 同左 |
| pytest-9359 | 5103 17.8；5221 9.3 | 两条 | 注入 5221 | 同左 |
| pytest-7220 | 5221 10.7；5103 8.5 | 两条 | 注入 5221 | 同左 |
| sphinx 四题 | 无 | 无 | 无 | 无 |

## 验证和花费

- 状态：`partial_attempt` 1 张（pytest-5103），`unverified` 10 张。harness 验证文件还没被新 grader 更新。
- LLM 提炼：没做。规则版已经能指出具体函数或设置，花费 0。
