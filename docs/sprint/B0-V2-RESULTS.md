# B0 v2 三次重复

profile 是 `b0-v2`。镜像是 clean image。v1 是测试可见条件下的历史结果，不并进这个分母。

| 题 | v2 | v1 | 平均花费 | 停止原因 |
| --- | --- | --- | --- | --- |
| django-10914 | 3/3 | 3/3 | 0.225 | completed, completed, completed |
| django-10924 | 2/3 | 3/3 | 0.288 | completed, completed, completed |
| django-11039 | 3/3 | 3/3 | 0.213 | completed, completed, completed |
| pytest-5103 | 0/3 | 1/3 | 0.707 | max_model_calls, max_model_calls, max_model_calls |
| pytest-5227 | 3/3 | 3/3 | 0.525 | completed, completed, max_model_calls |
| scikit-learn-10297 | 3/3 | 3/3 | 0.110 | completed, completed, completed |
| scikit-learn-10508 | 0/3 | 3/3 | 0.093 | completed, completed, completed |
| scikit-learn-10949 | 0/3 | 0/3 | 0.170 | completed, completed, completed |
| scikit-learn-11040 | 2/3 | 3/3 | 0.176 | completed, completed, completed |
| scikit-learn-11281 | 1/3 | 3/3 | 0.563 | max_model_calls, StoreError, completed |
| sympy-11400 | 0/3 | 3/3 | 0.257 | completed, completed, completed |
| sympy-11870 | 0/3 | 0/3 | 0.639 | max_model_calls, max_model_calls, max_model_calls |
| sympy-11897 | 0/3 | 3/3 | 0.616 | max_model_calls, max_model_calls, max_model_calls |
| sympy-12171 | 0/3 | 1/3 | 0.322 | max_model_calls, completed, completed |

解出 17/42。花费 14.712 CNY。隔离失败 0 次。
