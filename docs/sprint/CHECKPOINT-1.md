# CHECKPOINT-1

日期：2026-09-24。范围：`pre-capability-sprint..HEAD`。累计花费 **1.591 CNY**。没有跑 20 个 pilot、B1–B3 或 240 矩阵。

## 提交

- `e977a98` 通用 B0 运行器和 9 题 dev 集
- `29e9d35` `read_file` 行号、offset、续读提示
- `985dea1` 只读 `search_code`
- `95da116` masking 保留路径和退出码
- `dd77ba3` SWE 提示词，以及每轮剩余调用数
- `4a332be` 嵌套 profile 能读到仓库 `.env`

## dev 集结果

只跑了 3 道能进 grader 文件数上限的 pytest 题。sympy / sklearn 仍受 8MB 传输上限限制，没有跑。

| 题 | solved | 改了文件 | 模型调用 | 费用 CNY | grader |
| --- | --- | --- | --- | --- | --- |
| pytest-5103 | 否 | 是，`rewrite.py` | 40 | 0.715 | invalid_env |
| pytest-5221 | 否 | 否 | 40 | 0.551 | invalid_env |
| pytest-5227 | 否 | 否 | 27 | 0.325 | invalid_env |

## 每项改动的效果

- `read_file` / `search_code` / masking / 提示词：5103 终于改了一个文件。改之前同类题是 24 轮 0 个文件。这次改动把 pytest 的 import 改坏了，40 次调用用完，没有解出。
- 5221 和 5227：delta 仍为空，这两项工具改动没有变成一次有效编辑。
- `.env` 查找：不修的话真实调用发的是空 Bearer。这是让对照跑能够发出去的前提，本身不提高解出率。
- thinking 开/关没有比。当前 grader 给不出 pass/partial/fail，多花一轮模型费区分不出模式。

## 卡在哪里

1. 三题 grader 都是 `invalid_env`。5103 是补丁破坏了 import，收不到 receipt。5221 的 nodeid 和收集结果对不上。5227 报测试文件找不到。上传整棵树的 grader 和第 1 步 mock 一样，P2P 也不能复现镜像里的基线。
2. 单题 40 次调用大约 0.3–0.7 CNY，预算用完就停，来不及改完并重跑测试。
3. Django 超 2048 文件，sympy/sklearn 超 8MB，dev 集里只有 pytest 三题能打分。

## 建议

先修 grader，让未改动的树能稳定复现镜像基线，再谈解出率。然后才值得做 thinking 对照和第 3 步的外部 agent。本节点停下，等审计。
