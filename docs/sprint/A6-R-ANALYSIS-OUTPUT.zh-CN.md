# A6-R 分析

- `a6-retry-runs.json` handoff_sha256：`a0870f766a3b02f6ce34d6e5291ae59f8ab5160f46ae6e7671f3fd39f08a4256`
- `a6-attempts.json` handoff_sha256：`bd93252922c990ec61071caecb5a6bf5e604202cbbcf30d296f2b875794dd3ce`
- runs 里记录的 `attempts_sha256`：`bd93252922c990ec61071caecb5a6bf5e604202cbbcf30d296f2b875794dd3ce`，一致

解出率是非 infra_error 运行里的解出次数除以有效运行数。
每题每组有效运行少于 2 次的题不进入主分析。
置换检验和 bootstrap 各 10000 次，种子 20261013。

## 输入核对

- 第一次尝试：53 次、22 道题（预期 53/22）
- 槽位行数：318（预期 318）
- infra_error：0 次
- 列出的退役目录（未计入）：无
- 缺的槽位：无
- 重复的槽位：无
- 清单外的槽位：无
- run_dir 与槽位不符：无
- R1 的 attempt_sha256 与清单不符：无
- R0 的 prompt_sha256 与 A5 B0 不同的题：无

## 逐题

| 题 | 仓库 | A5 B0 档位 | 第一次尝试数 | R0 | R1 | d_t |
|---|---|---|---|---|---|---|
| django__django-13512 | django/django | 0/3 | 3 | 0/9 | 2/9 | 0.222 |
| django__django-13964 | django/django | 中间档 | 1 | 2/3 | 1/3 | -0.333 |
| django__django-15022 | django/django | 中间档 | 2 | 0/6 | 3/6 | 0.500 |
| django__django-15973 | django/django | 0/3 | 3 | 2/9 | 0/9 | -0.222 |
| pytest-dev__pytest-5840 | pytest-dev/pytest | 0/3 | 3 | 0/9 | 0/9 | 0.000 |
| pytest-dev__pytest-7324 | pytest-dev/pytest | 0/3 | 3 | 1/9 | 2/9 | 0.111 |
| pytest-dev__pytest-7490 | pytest-dev/pytest | 中间档 | 1 | 3/3 | 2/3 | -0.333 |
| scikit-learn__scikit-learn-10908 | scikit-learn/scikit-learn | 中间档 | 1 | 3/3 | 2/3 | -0.333 |
| scikit-learn__scikit-learn-12973 | scikit-learn/scikit-learn | 0/3 | 3 | 1/9 | 0/9 | -0.111 |
| sphinx-doc__sphinx-10614 | sphinx-doc/sphinx | 0/3 | 3 | 0/9 | 0/9 | 0.000 |
| sphinx-doc__sphinx-7590 | sphinx-doc/sphinx | 0/3 | 3 | 0/9 | 0/9 | 0.000 |
| sphinx-doc__sphinx-8120 | sphinx-doc/sphinx | 中间档 | 2 | 5/6 | 0/6 | -0.833 |
| sphinx-doc__sphinx-9258 | sphinx-doc/sphinx | 中间档 | 2 | 5/6 | 4/6 | -0.167 |
| sphinx-doc__sphinx-9461 | sphinx-doc/sphinx | 0/3 | 3 | 0/9 | 0/9 | 0.000 |
| sympy__sympy-11618 | sympy/sympy | 中间档 | 1 | 0/3 | 1/3 | 0.333 |
| sympy__sympy-13091 | sympy/sympy | 0/3 | 3 | 2/9 | 1/9 | -0.111 |
| sympy__sympy-14248 | sympy/sympy | 0/3 | 3 | 0/9 | 0/9 | 0.000 |
| sympy__sympy-15599 | sympy/sympy | 0/3 | 3 | 0/9 | 0/9 | 0.000 |
| sympy__sympy-19040 | sympy/sympy | 中间档 | 2 | 0/6 | 0/6 | 0.000 |
| sympy__sympy-20428 | sympy/sympy | 0/3 | 3 | 0/9 | 0/9 | 0.000 |
| sympy__sympy-21596 | sympy/sympy | 0/3 | 3 | 0/9 | 0/9 | 0.000 |
| sympy__sympy-23950 | sympy/sympy | 中间档 | 2 | 3/6 | 2/6 | -0.167 |

## 剔除

无

## 主分析

- 题数：22
- 平均 d_t：-0.0657
- 双侧符号翻转 p：0.2880
- 95% 区间：-0.1768 到 0.0379
- d_t 样本标准差 s：0.2660
- 数据检测下限：15.9 个百分点（2.8×s/√N）
- 95% 区间上限：3.8 个百分点
- 结论：未检出大于 15.9 个百分点的效应（2.8×s/√N）；95% 区间上限 3.8 个百分点。点估计 -6.6 个百分点，95% 区间 -17.7 到 3.8
- 事先算好的功效（OPTIONS 模拟，假设每次失败运行同一加性提升）：+10pp 约 54%，+15pp 约 85%，+20pp 约 98%。
- 第二阶段触发（点估计 ≥ +5pp 且区间含 0）：不满足，不做第二阶段

## 次要指标（描述性，不做检验，不进结论句）

只算进入主分析的题的有效运行。

### 1. diff 重复率

- R0：29/159（0.182）
- R1：44/159（0.277）

### 2. 文件复用

- R0：104/159（0.654）
- R1：111/159（0.698）

### 3. first_edit_step

- R0：平均 15.367，中位数 12.0，null 20 次
- R1：平均 16.376，中位数 12.0，null 18 次

### 4. model_calls

- R0：平均 31.377，用满 40 次 89/159（0.560）
- R1：平均 32.082，用满 40 次 87/159（0.547）

### 5. 花费 CNY

- R0：平均 0.497
- R1：平均 0.589

### 6. 按 A5 B0 档位（只描述，不作为效应证据）

- 0/3：13 题，平均 d_t -0.0085
- 中间档：9 题，平均 d_t -0.1481
