# A6-R 合成数据检查

日期：2026-10-13。没有调用模型，没有真实 A6 数据。

## 修订

- 第一版：分析脚本和生成器在 `a4c005d` 提交后跑，结果记在 `eb068af`；`095ed17` 换成 harness 的 diff 归一化后重跑，输出逐字节不变。对应 tag `a6-retry-freeze`。
- 本版（审计 `AUDIT-A6-1.zh-CN.md` 第 3 节第 1、2 条之后，脚本在 `199047a`）：结论句里的 X 从 2.8×0.35/√N 改为 2.8×s_obs/√N，并写出 95% 区间上限；合成清单改成 harness 的结构（列表在 `records`，计数在 `attempts`）。重跑后三套的点估计、p、区间、结论和次要指标都和第一版相同。变化只有两处：一是主分析里 X 相关的几行，二是因为清单文件结构变了，两个交接 sha 也跟着变了。对应 tag `a6-retry-freeze-r1`。

## 做法

- 生成器 `scripts/make_a6_synthetic.py`，分析脚本 `scripts/analyze_a6_retry.py`。判据（点估计离真效应不超过 0.10；零效应重复 200 套）在第一版跑之前就写进了生成器，本版没有改。
- 每套数据是一个和 harness 同布局的假根目录（`runs/a5-main`、`runs/sprint5-main-images/<task>/staging/original`、`runs/a6-retry`、`docs/sprint/a6-attempts.json`、`docs/sprint/a6-retry-runs.json`），分析脚本走的是和真实数据相同的读取路径，包括 diff 归一化和交接 sha 核对。
- 形状照 A5 B0 的失败分布：13 道 0/3 题各 3 次第一次尝试，9 道中间档（5 道 1/3 各 2 次，4 道 2/3 各 1 次），共 53 次、22 道题、318 个槽位。每套随机标 2 个槽位为 `infra_error`。
- 每题的"新鲜重试率"按题抽取：0/3 档在 [0, 0.1] 均匀，中间档在 [0.3, 0.7] 均匀。R1 在每次运行上加同一个真效应，所以 d_t 平均的期望等于真效应。
- 次要指标的假数据：R0 有 0.4 的概率原样重复第一次 diff，R1 是 0.15；53 次第一次尝试里 11 次没改非测试源码。这些只用来检查计数路径，不代表任何预期。
- 种子：三套分别是 `20261013 + 0`、`+ 15`、`+ 30`；零效应重复第 i 套用 `20261013 × 1000 + i`。
- 复现：`python scripts/make_a6_synthetic.py --out .tmp/a6-synthetic-r1`（输出在 `.tmp/`，不进 git）。

## 结果

| 真效应 | 平均 d_t | 双侧 p | 95% 区间 | s_obs | X（2.8×s_obs/√22） | 区间上限 | 离真效应 ≤ 0.10 | 脚本结论 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 0.0145 | 0.6552 | -0.0385 到 0.0676 | 0.1292 | 7.7pp | 6.8pp | 是 | 未检出大于 7.7 个百分点的效应 |
| +15pp | 0.1313 | 0.0142 | 0.0404 到 0.2260 | 0.2289 | 13.7pp | 22.6pp | 是 | 检出效应 |
| +30pp | 0.3308 | 0.0000 | 0.2551 到 0.4116 | 0.1936 | 11.6pp | 41.2pp | 是 | 检出效应 |

- 三套结论和第一版相同：零效应未检出，+15pp 和 +30pp 检出，三套都不满足第二阶段触发条件。
- 零效应时 p = 0.6552，不显著。零效应时 X 是 7.7pp，第一版是 20.9pp。
- 200 套零效应数据里 12 套 p < 0.05，即 6.0%，和第一版相同。按二项分布，名义 5% 时 200 套里落在 4–16 套之间都正常，置换检验的第一类错误率没有偏高。
- 三套的输入核对全部为"无"，第一次尝试 53/22、槽位 318、`attempts_sha256` 一致。
- +15pp 这一套检出了，但这只是一次抽样，不能当成功效估计。预注册的功效数字来自 OPTIONS 的模拟，不在这里重算。

## 三份脚本输出（原样，本版）

### 真效应 0

```text
# A6-R 分析（合成数据，scope=synthetic）

- `a6-retry-runs.json` handoff_sha256：`b07f03a46da0f926d1d5717291faa118eaa734e809648d29e39f83582114d0e3`
- `a6-attempts.json` handoff_sha256：`1303ab25c2a0126e940beea9513f87e50b1fd5fe346481d78b850bf4cac1b6f7`
- runs 里记录的 `attempts_sha256`：`1303ab25c2a0126e940beea9513f87e50b1fd5fe346481d78b850bf4cac1b6f7`，一致

解出率是非 infra_error 运行里的解出次数除以有效运行数。
每题每组有效运行少于 2 次的题不进入主分析。
置换检验和 bootstrap 各 10000 次，种子 20261013。

## 输入核对

- 第一次尝试：53 次、22 道题（预期 53/22）
- 槽位行数：318（预期 318）
- infra_error：2 次
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
| django__django-90000 | django/django | 0/3 | 3 | 1/8 | 0/9 | -0.125 |
| django__django-90004 | django/django | 0/3 | 3 | 1/9 | 1/9 | 0.000 |
| django__django-90008 | django/django | 0/3 | 3 | 0/9 | 0/9 | 0.000 |
| django__django-90012 | django/django | 0/3 | 3 | 0/9 | 1/9 | 0.111 |
| django__django-90016 | django/django | 中间档 | 2 | 3/6 | 1/6 | -0.333 |
| django__django-90020 | django/django | 中间档 | 1 | 2/3 | 2/3 | 0.000 |
| pytest-dev__pytest-90001 | pytest-dev/pytest | 0/3 | 3 | 0/9 | 1/9 | 0.111 |
| pytest-dev__pytest-90005 | pytest-dev/pytest | 0/3 | 3 | 0/9 | 1/9 | 0.111 |
| pytest-dev__pytest-90009 | pytest-dev/pytest | 0/3 | 3 | 0/8 | 0/9 | 0.000 |
| pytest-dev__pytest-90013 | pytest-dev/pytest | 中间档 | 2 | 0/6 | 2/6 | 0.333 |
| pytest-dev__pytest-90017 | pytest-dev/pytest | 中间档 | 2 | 2/6 | 2/6 | 0.000 |
| pytest-dev__pytest-90021 | pytest-dev/pytest | 中间档 | 1 | 1/3 | 1/3 | 0.000 |
| sphinx-doc__sphinx-90002 | sphinx-doc/sphinx | 0/3 | 3 | 1/9 | 1/9 | 0.000 |
| sphinx-doc__sphinx-90006 | sphinx-doc/sphinx | 0/3 | 3 | 1/9 | 0/9 | -0.111 |
| sphinx-doc__sphinx-90010 | sphinx-doc/sphinx | 0/3 | 3 | 0/9 | 0/9 | 0.000 |
| sphinx-doc__sphinx-90014 | sphinx-doc/sphinx | 中间档 | 2 | 3/6 | 4/6 | 0.167 |
| sphinx-doc__sphinx-90018 | sphinx-doc/sphinx | 中间档 | 1 | 1/3 | 1/3 | 0.000 |
| sympy__sympy-90003 | sympy/sympy | 0/3 | 3 | 2/9 | 1/9 | -0.111 |
| sympy__sympy-90007 | sympy/sympy | 0/3 | 3 | 0/9 | 0/9 | 0.000 |
| sympy__sympy-90011 | sympy/sympy | 0/3 | 3 | 0/9 | 0/9 | 0.000 |
| sympy__sympy-90015 | sympy/sympy | 中间档 | 2 | 4/6 | 5/6 | 0.167 |
| sympy__sympy-90019 | sympy/sympy | 中间档 | 1 | 2/3 | 2/3 | 0.000 |

## 剔除

无

## 主分析

- 题数：22
- 平均 d_t：0.0145
- 双侧符号翻转 p：0.6552
- 95% 区间：-0.0385 到 0.0676
- d_t 样本标准差 s：0.1292
- 数据检测下限：7.7 个百分点（2.8×s/√N）
- 95% 区间上限：6.8 个百分点
- 结论：未检出大于 7.7 个百分点的效应（2.8×s/√N）；95% 区间上限 6.8 个百分点。点估计 1.5 个百分点，95% 区间 -3.9 到 6.8
- 事先算好的功效（OPTIONS 模拟，假设每次失败运行同一加性提升）：+10pp 约 54%，+15pp 约 85%，+20pp 约 98%。
- 第二阶段触发（点估计 ≥ +5pp 且区间含 0）：不满足，不做第二阶段

## 次要指标（描述性，不做检验，不进结论句）

只算进入主分析的题的有效运行。

### 1. diff 重复率

- R0：62/157（0.395）
- R1：17/159（0.107）

### 2. 文件复用

- R0：78/157（0.497）
- R1：64/159（0.403）

### 3. first_edit_step

- R0：平均 8.671，中位数 8.0，null 11 次
- R1：平均 9.286，中位数 10.0，null 12 次

### 4. model_calls

- R0：平均 27.764，用满 40 次 5/157（0.032）
- R1：平均 25.755，用满 40 次 5/159（0.031）

### 5. 花费 CNY

- R0：平均 0.444
- R1：平均 0.412

### 6. 按 A5 B0 档位（只描述，不作为效应证据）

- 0/3：13 题，平均 d_t -0.0011
- 中间档：9 题，平均 d_t 0.0370
```

### 真效应 +15pp

```text
# A6-R 分析（合成数据，scope=synthetic）

- `a6-retry-runs.json` handoff_sha256：`9f41f44d7362018231932369acbe098d3dbfe8fa66efd8846c6a3c49fdce23e8`
- `a6-attempts.json` handoff_sha256：`1303ab25c2a0126e940beea9513f87e50b1fd5fe346481d78b850bf4cac1b6f7`
- runs 里记录的 `attempts_sha256`：`1303ab25c2a0126e940beea9513f87e50b1fd5fe346481d78b850bf4cac1b6f7`，一致

解出率是非 infra_error 运行里的解出次数除以有效运行数。
每题每组有效运行少于 2 次的题不进入主分析。
置换检验和 bootstrap 各 10000 次，种子 20261013。

## 输入核对

- 第一次尝试：53 次、22 道题（预期 53/22）
- 槽位行数：318（预期 318）
- infra_error：2 次
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
| django__django-90000 | django/django | 0/3 | 3 | 1/9 | 3/9 | 0.222 |
| django__django-90004 | django/django | 0/3 | 3 | 0/9 | 3/9 | 0.333 |
| django__django-90008 | django/django | 0/3 | 3 | 0/9 | 0/9 | 0.000 |
| django__django-90012 | django/django | 0/3 | 3 | 0/9 | 1/9 | 0.111 |
| django__django-90016 | django/django | 中间档 | 2 | 3/6 | 3/6 | 0.000 |
| django__django-90020 | django/django | 中间档 | 1 | 2/3 | 2/3 | 0.000 |
| pytest-dev__pytest-90001 | pytest-dev/pytest | 0/3 | 3 | 1/9 | 2/9 | 0.111 |
| pytest-dev__pytest-90005 | pytest-dev/pytest | 0/3 | 3 | 0/9 | 2/9 | 0.222 |
| pytest-dev__pytest-90009 | pytest-dev/pytest | 0/3 | 3 | 0/9 | 2/8 | 0.250 |
| pytest-dev__pytest-90013 | pytest-dev/pytest | 中间档 | 2 | 5/6 | 5/6 | 0.000 |
| pytest-dev__pytest-90017 | pytest-dev/pytest | 中间档 | 2 | 2/6 | 3/6 | 0.167 |
| pytest-dev__pytest-90021 | pytest-dev/pytest | 中间档 | 1 | 1/3 | 1/3 | 0.000 |
| sphinx-doc__sphinx-90002 | sphinx-doc/sphinx | 0/3 | 3 | 2/9 | 1/9 | -0.111 |
| sphinx-doc__sphinx-90006 | sphinx-doc/sphinx | 0/3 | 3 | 0/9 | 4/9 | 0.444 |
| sphinx-doc__sphinx-90010 | sphinx-doc/sphinx | 0/3 | 3 | 0/9 | 0/9 | 0.000 |
| sphinx-doc__sphinx-90014 | sphinx-doc/sphinx | 中间档 | 2 | 2/6 | 5/6 | 0.500 |
| sphinx-doc__sphinx-90018 | sphinx-doc/sphinx | 中间档 | 1 | 1/3 | 3/3 | 0.667 |
| sympy__sympy-90003 | sympy/sympy | 0/3 | 3 | 0/9 | 2/8 | 0.250 |
| sympy__sympy-90007 | sympy/sympy | 0/3 | 3 | 0/9 | 0/9 | 0.000 |
| sympy__sympy-90011 | sympy/sympy | 0/3 | 3 | 0/9 | 2/9 | 0.222 |
| sympy__sympy-90015 | sympy/sympy | 中间档 | 2 | 3/6 | 2/6 | -0.167 |
| sympy__sympy-90019 | sympy/sympy | 中间档 | 1 | 1/3 | 0/3 | -0.333 |

## 剔除

无

## 主分析

- 题数：22
- 平均 d_t：0.1313
- 双侧符号翻转 p：0.0142
- 95% 区间：0.0404 到 0.2260
- d_t 样本标准差 s：0.2289
- 数据检测下限：13.7 个百分点（2.8×s/√N）
- 95% 区间上限：22.6 个百分点
- 结论：检出效应：平均 d_t 为 13.1 个百分点（95% 区间 4.0 到 22.6，p = 0.0142）
- 事先算好的功效（OPTIONS 模拟，假设每次失败运行同一加性提升）：+10pp 约 54%，+15pp 约 85%，+20pp 约 98%。
- 第二阶段触发（点估计 ≥ +5pp 且区间含 0）：不满足，不做第二阶段

## 次要指标（描述性，不做检验，不进结论句）

只算进入主分析的题的有效运行。

### 1. diff 重复率

- R0：62/159（0.390）
- R1：30/157（0.191）

### 2. 文件复用

- R0：78/159（0.491）
- R1：73/157（0.465）

### 3. first_edit_step

- R0：平均 8.993，中位数 9.0，null 7 次
- R1：平均 9.227，中位数 9.0，null 7 次

### 4. model_calls

- R0：平均 27.195，用满 40 次 8/159（0.050）
- R1：平均 25.580，用满 40 次 6/157（0.038）

### 5. 花费 CNY

- R0：平均 0.435
- R1：平均 0.409

### 6. 按 A5 B0 档位（只描述，不作为效应证据）

- 0/3：13 题，平均 d_t 0.1581
- 中间档：9 题，平均 d_t 0.0926
```

### 真效应 +30pp

```text
# A6-R 分析（合成数据，scope=synthetic）

- `a6-retry-runs.json` handoff_sha256：`4ea657107be5eaa2808e4a3a863a4217df175f4f2d38753aff56d64db3837e6e`
- `a6-attempts.json` handoff_sha256：`1303ab25c2a0126e940beea9513f87e50b1fd5fe346481d78b850bf4cac1b6f7`
- runs 里记录的 `attempts_sha256`：`1303ab25c2a0126e940beea9513f87e50b1fd5fe346481d78b850bf4cac1b6f7`，一致

解出率是非 infra_error 运行里的解出次数除以有效运行数。
每题每组有效运行少于 2 次的题不进入主分析。
置换检验和 bootstrap 各 10000 次，种子 20261013。

## 输入核对

- 第一次尝试：53 次、22 道题（预期 53/22）
- 槽位行数：318（预期 318）
- infra_error：2 次
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
| django__django-90000 | django/django | 0/3 | 3 | 0/9 | 5/9 | 0.556 |
| django__django-90004 | django/django | 0/3 | 3 | 1/9 | 3/9 | 0.222 |
| django__django-90008 | django/django | 0/3 | 3 | 0/9 | 2/9 | 0.222 |
| django__django-90012 | django/django | 0/3 | 3 | 0/9 | 5/9 | 0.556 |
| django__django-90016 | django/django | 中间档 | 2 | 3/6 | 6/6 | 0.500 |
| django__django-90020 | django/django | 中间档 | 1 | 1/3 | 3/3 | 0.667 |
| pytest-dev__pytest-90001 | pytest-dev/pytest | 0/3 | 3 | 0/7 | 3/9 | 0.333 |
| pytest-dev__pytest-90005 | pytest-dev/pytest | 0/3 | 3 | 1/9 | 4/9 | 0.333 |
| pytest-dev__pytest-90009 | pytest-dev/pytest | 0/3 | 3 | 2/9 | 3/9 | 0.111 |
| pytest-dev__pytest-90013 | pytest-dev/pytest | 中间档 | 2 | 1/6 | 5/6 | 0.667 |
| pytest-dev__pytest-90017 | pytest-dev/pytest | 中间档 | 2 | 4/6 | 5/6 | 0.167 |
| pytest-dev__pytest-90021 | pytest-dev/pytest | 中间档 | 1 | 2/3 | 3/3 | 0.333 |
| sphinx-doc__sphinx-90002 | sphinx-doc/sphinx | 0/3 | 3 | 0/9 | 1/9 | 0.111 |
| sphinx-doc__sphinx-90006 | sphinx-doc/sphinx | 0/3 | 3 | 0/9 | 2/9 | 0.222 |
| sphinx-doc__sphinx-90010 | sphinx-doc/sphinx | 0/3 | 3 | 1/9 | 4/9 | 0.333 |
| sphinx-doc__sphinx-90014 | sphinx-doc/sphinx | 中间档 | 2 | 2/6 | 4/6 | 0.333 |
| sphinx-doc__sphinx-90018 | sphinx-doc/sphinx | 中间档 | 1 | 1/3 | 3/3 | 0.667 |
| sympy__sympy-90003 | sympy/sympy | 0/3 | 3 | 0/9 | 2/9 | 0.222 |
| sympy__sympy-90007 | sympy/sympy | 0/3 | 3 | 1/9 | 4/9 | 0.333 |
| sympy__sympy-90011 | sympy/sympy | 0/3 | 3 | 1/9 | 3/9 | 0.222 |
| sympy__sympy-90015 | sympy/sympy | 中间档 | 2 | 4/6 | 5/6 | 0.167 |
| sympy__sympy-90019 | sympy/sympy | 中间档 | 1 | 2/3 | 2/3 | 0.000 |

## 剔除

无

## 主分析

- 题数：22
- 平均 d_t：0.3308
- 双侧符号翻转 p：0.0000
- 95% 区间：0.2551 到 0.4116
- d_t 样本标准差 s：0.1936
- 数据检测下限：11.6 个百分点（2.8×s/√N）
- 95% 区间上限：41.2 个百分点
- 结论：检出效应：平均 d_t 为 33.1 个百分点（95% 区间 25.5 到 41.2，p = 0.0000）
- 事先算好的功效（OPTIONS 模拟，假设每次失败运行同一加性提升）：+10pp 约 54%，+15pp 约 85%，+20pp 约 98%。
- 第二阶段触发（点估计 ≥ +5pp 且区间含 0）：不满足，不做第二阶段

## 次要指标（描述性，不做检验，不进结论句）

只算进入主分析的题的有效运行。

### 1. diff 重复率

- R0：60/157（0.382）
- R1：21/159（0.132）

### 2. 文件复用

- R0：79/157（0.503）
- R1：76/159（0.478）

### 3. first_edit_step

- R0：平均 8.862，中位数 9.0，null 5 次
- R1：平均 8.461，中位数 9.0，null 5 次

### 4. model_calls

- R0：平均 26.675，用满 40 次 6/157（0.038）
- R1：平均 26.434，用满 40 次 8/159（0.050）

### 5. 花费 CNY

- R0：平均 0.427
- R1：平均 0.423

### 6. 按 A5 B0 档位（只描述，不作为效应证据）

- 0/3：13 题，平均 d_t 0.2906
- 中间档：9 题，平均 d_t 0.3889
```
