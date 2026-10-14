# A5-main 分析

解出率是非 infra_error 运行里的解出次数除以有效运行数。
有效运行少于 2 次的题不进入主要分析。
置换检验和 bootstrap 各 10000 次，种子 20260926。

## 逐题

| 题 | 仓库 | B0 | B2 | d_t | B2 注入 |
|---|---|---|---|---|---|
| django__django-11211 | django/django | 3/3 | 3/3 | 0.000 | True |
| django__django-11749 | django/django | 3/3 | 2/3 | -0.333 | True |
| django__django-12276 | django/django | 3/3 | 3/3 | 0.000 | True |
| django__django-13109 | django/django | 3/3 | 3/3 | 0.000 | True |
| django__django-13512 | django/django | 0/3 | 0/3 | 0.000 | True |
| django__django-13964 | django/django | 2/3 | 0/3 | -0.667 | True |
| django__django-14434 | django/django | 3/3 | 3/3 | 0.000 | True |
| django__django-15022 | django/django | 1/3 | 0/3 | -0.333 | True |
| django__django-15499 | django/django | 3/3 | 3/3 | 0.000 | True |
| django__django-15973 | django/django | 0/3 | 0/3 | 0.000 | True |
| django__django-16527 | django/django | 3/3 | 3/3 | 0.000 | True |
| pytest-dev__pytest-10081 | pytest-dev/pytest | 3/3 | 3/3 | 0.000 | True |
| pytest-dev__pytest-5262 | pytest-dev/pytest | 3/3 | 3/3 | 0.000 | True |
| pytest-dev__pytest-5631 | pytest-dev/pytest | 3/3 | 3/3 | 0.000 | True |
| pytest-dev__pytest-5809 | pytest-dev/pytest | 3/3 | 3/3 | 0.000 | True |
| pytest-dev__pytest-5840 | pytest-dev/pytest | 0/3 | 0/3 | 0.000 | True |
| pytest-dev__pytest-6202 | pytest-dev/pytest | 3/3 | 3/3 | 0.000 | True |
| pytest-dev__pytest-7205 | pytest-dev/pytest | 3/3 | 3/3 | 0.000 | True |
| pytest-dev__pytest-7324 | pytest-dev/pytest | 0/3 | 0/3 | 0.000 | True |
| pytest-dev__pytest-7490 | pytest-dev/pytest | 2/3 | 3/3 | 0.333 | True |
| pytest-dev__pytest-7521 | pytest-dev/pytest | 3/3 | 3/3 | 0.000 | True |
| pytest-dev__pytest-7982 | pytest-dev/pytest | 3/3 | 3/3 | 0.000 | True |
| pytest-dev__pytest-8399 | pytest-dev/pytest | 3/3 | 3/3 | 0.000 | True |
| scikit-learn__scikit-learn-10908 | scikit-learn/scikit-learn | 2/3 | 3/3 | 0.333 | True |
| scikit-learn__scikit-learn-12585 | scikit-learn/scikit-learn | 3/3 | 3/3 | 0.000 | True |
| scikit-learn__scikit-learn-12973 | scikit-learn/scikit-learn | 0/3 | 0/3 | 0.000 | True |
| scikit-learn__scikit-learn-13142 | scikit-learn/scikit-learn | 3/3 | 3/3 | 0.000 | True |
| scikit-learn__scikit-learn-13439 | scikit-learn/scikit-learn | 3/3 | 3/3 | 0.000 | True |
| scikit-learn__scikit-learn-14053 | scikit-learn/scikit-learn | 3/3 | 3/3 | 0.000 | True |
| scikit-learn__scikit-learn-14496 | scikit-learn/scikit-learn | 3/3 | 3/3 | 0.000 | True |
| scikit-learn__scikit-learn-14710 | scikit-learn/scikit-learn | 3/3 | 3/3 | 0.000 | True |
| scikit-learn__scikit-learn-15100 | scikit-learn/scikit-learn | 3/3 | 3/3 | 0.000 | True |
| scikit-learn__scikit-learn-9288 | scikit-learn/scikit-learn | 3/3 | 2/3 | -0.333 | False |
| sphinx-doc__sphinx-10323 | sphinx-doc/sphinx | 3/3 | 3/3 | 0.000 | True |
| sphinx-doc__sphinx-10614 | sphinx-doc/sphinx | 0/3 | 0/3 | 0.000 | True |
| sphinx-doc__sphinx-7440 | sphinx-doc/sphinx | 3/3 | 2/3 | -0.333 | False |
| sphinx-doc__sphinx-7590 | sphinx-doc/sphinx | 0/3 | 0/3 | 0.000 | True |
| sphinx-doc__sphinx-7910 | sphinx-doc/sphinx | 3/3 | 3/3 | 0.000 | True |
| sphinx-doc__sphinx-8120 | sphinx-doc/sphinx | 1/3 | 3/3 | 0.667 | True |
| sphinx-doc__sphinx-8459 | sphinx-doc/sphinx | 3/3 | 2/3 | -0.333 | True |
| sphinx-doc__sphinx-8593 | sphinx-doc/sphinx | 3/3 | 2/3 | -0.333 | True |
| sphinx-doc__sphinx-9258 | sphinx-doc/sphinx | 1/3 | 3/3 | 0.667 | True |
| sphinx-doc__sphinx-9461 | sphinx-doc/sphinx | 0/3 | 0/3 | 0.000 | True |
| sphinx-doc__sphinx-9673 | sphinx-doc/sphinx | 3/3 | 1/3 | -0.667 | True |
| sympy__sympy-11618 | sympy/sympy | 2/3 | 2/3 | 0.000 | False |
| sympy__sympy-13091 | sympy/sympy | 0/3 | 1/3 | 0.333 | True |
| sympy__sympy-13757 | sympy/sympy | 3/3 | 2/3 | -0.333 | False |
| sympy__sympy-14248 | sympy/sympy | 0/3 | 0/3 | 0.000 | False |
| sympy__sympy-15599 | sympy/sympy | 0/3 | 1/3 | 0.333 | True |
| sympy__sympy-16766 | sympy/sympy | 3/3 | 3/3 | 0.000 | True |
| sympy__sympy-17655 | sympy/sympy | 3/3 | 3/3 | 0.000 | True |
| sympy__sympy-19040 | sympy/sympy | 1/3 | 0/3 | -0.333 | True |
| sympy__sympy-20428 | sympy/sympy | 0/3 | 0/3 | 0.000 | True |
| sympy__sympy-21596 | sympy/sympy | 0/3 | 0/3 | 0.000 | True |
| sympy__sympy-22714 | sympy/sympy | 3/3 | 3/3 | 0.000 | True |
| sympy__sympy-23950 | sympy/sympy | 1/3 | 2/3 | 0.333 | True |

## 剔除

无

## 不满 3 次

无

## 主要分析

- 题数：56
- 平均 d_t：-0.0179
- 双侧符号翻转 p：0.7175
- 95% 区间：-0.0833 到 0.0476
- 设计检测下限：13.1 个百分点（2.8×0.35/√N）
- 本次数据检测下限：9.0 个百分点（2.8×s/√N）
- 结论：没有检出大于 13.1 个百分点的效应

## 次要分析

分组依据是处理前预测会注入至少 1 张卡的题。实际注入只用来核对。
- 题数：51
- 平均 d_t：0.0000
- 双侧符号翻转 p：1.0000
- 95% 区间：-0.0654 到 0.0654
- 结论：没有检出大于 13.7 个百分点的效应

### 按仓库

- django/django：11 题，平均 d_t -0.1212
- pytest-dev/pytest：12 题，平均 d_t 0.0278
- scikit-learn/scikit-learn：9 题，平均 d_t 0.0370
- sphinx-doc/sphinx：10 题，平均 d_t 0.0000
- sympy/sympy：9 题，平均 d_t 0.0741

### 实际注入核对

预测注入和实际注入的题一致。
- 实际注入至少 1 张卡的题数：51
- 平均 d_t：0.0000

## 漂移检查（描述性，非预注册）

- 题数：56
- 平均差（r4 减 r1–r3）：-0.0238
- 95% 区间：-0.0833 到 0.0298
不做显著性检验。

### 用 r4 作同期 B0（描述性，非预注册）

- 题数：56
- 平均（B2 的 k/3 减 r4）：0.0060
不做显著性检验。

## 按 B0 档位（描述性，非预注册）

按 B0 结果分组会受回归均值影响，不可作为效应证据。
- 0/3：13 题，平均 d_t 0.0513
- 1-2/3：9 题，平均 d_t 0.1111
- 3/3：34 题，平均 d_t -0.0784

## 花费和过程

- 花费 CNY：B0 0.329，B2 0.340
- 模型调用次数：B0 23.619，B2 23.720
- 第一次编辑轮次：B0 10.215，B2 9.730

## 按仓库的解出率、花费和调用（描述性，非预注册）

解出率是各题有效运行解出率的平均。花费和调用是有效运行的平均。不做显著性检验。

| 仓库 | 题数 | B0 解出率 | B2 解出率 | B0 花费 | B2 花费 | B0 调用 | B2 调用 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| django/django | 11 | 0.7273 | 0.6061 | 0.311 | 0.294 | 22.788 | 21.485 |
| pytest-dev/pytest | 12 | 0.8056 | 0.8333 | 0.228 | 0.250 | 18.972 | 19.806 |
| scikit-learn/scikit-learn | 10 | 0.8667 | 0.8667 | 0.105 | 0.113 | 9.500 | 9.467 |
| sphinx-doc/sphinx | 11 | 0.6061 | 0.5758 | 0.524 | 0.556 | 34.879 | 36.000 |
| sympy/sympy | 12 | 0.4444 | 0.4722 | 0.456 | 0.460 | 30.472 | 30.306 |

## 局限

卡片按规则从轨迹提取。approach 可能是 agent 中途的自述，而不是最终修法。

B0 结果两极分布：34 道 3/3，13 道 0/3。能提升的空间只在 22 道题上。
