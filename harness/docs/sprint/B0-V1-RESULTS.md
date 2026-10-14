# B0 v1 三次重复

profile 是 `b0-v1`。14 题各跑 3 次，花费 16.173 CNY。没有运行改过测试文件。

| 题 | 解出 | 平均花费 | 平均调用 | 首次编辑 | 停止原因 | 一致 |
| --- | --- | --- | --- | --- | --- | --- |
| django-10914 | 3/3 | 0.280 | 24.0 | 5 / 8 / 5 | completed, completed, completed | 3/3 |
| django-10924 | 3/3 | 0.198 | 18.7 | 8 / 11 / 11 | completed, completed, completed | 3/3 |
| django-11039 | 3/3 | 0.111 | 14.0 | 9 / 10 / 9 | completed, completed, completed | 3/3 |
| pytest-5103 | 1/3 | 0.741 | 40.0 | 20 / 33 / 22 | max_model_calls, max_model_calls, max_model_calls | 混合 |
| pytest-5227 | 3/3 | 0.116 | 14.3 | 10 / 10 / 7 | completed, completed, completed | 3/3 |
| scikit-learn-10297 | 3/3 | 0.145 | 12.7 | 7 / 6 / 9 | completed, completed, completed | 3/3 |
| scikit-learn-10508 | 3/3 | 0.505 | 36.0 | 3 / 3 / 3 | completed, max_model_calls, completed | 3/3 |
| scikit-learn-10949 | 0/3 | 0.456 | 32.7 | 15 / 11 / 10 | max_model_calls, completed, max_model_calls | 0/3 |
| scikit-learn-11040 | 3/3 | 0.283 | 24.7 | 14 / 12 / 10 | completed, completed, completed | 3/3 |
| scikit-learn-11281 | 3/3 | 0.336 | 25.7 | 15 / 16 / 18 | completed, completed, completed | 3/3 |
| sympy-11400 | 3/3 | 0.580 | 40.0 | 24 / 23 / 10 | completed, max_model_calls, completed | 3/3 |
| sympy-11870 | 0/3 | 0.637 | 40.0 | 34 / 18 / 20 | max_model_calls, max_model_calls, max_model_calls | 0/3 |
| sympy-11897 | 3/3 | 0.515 | 35.7 | 21 / 38 / 22 | completed, max_model_calls, completed | 3/3 |
| sympy-12171 | 1/3 | 0.488 | 40.0 | 4 / 4 / 4 | max_model_calls, max_model_calls, max_model_calls | 混合 |

总体解出 32/42。3/3 的题 10 道，0/3 的题 2 道，混合 2 道。

抽查两道解出的运行：django-10914 r1 改的是 `django/conf/global_settings.py` 和 `docs/ref/settings.txt`，没有改测试。sklearn-10297 r1 只改了 `sklearn/linear_model/ridge.py`。42 次运行的 `test_files_touched` 都是空的。

