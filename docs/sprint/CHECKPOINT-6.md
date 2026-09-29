# CHECKPOINT-6

日期：2026-09-28。第 0 步已完成。第 1 步等 harness 写完 CHECKPOINT-6a 再做。

## 冻结

tag `a5-main-freeze` 指向 `a22e4ca0a3994012c167a3e02e06498731c24a18`。

这一步改了三件事：

- 解出率分母改为有效运行数，`infra_error` 不计入。有效运行少于 2 次的题仍然不进主要分析。
- 没有解出时，取编号最小的非 `infra_error` 运行作为 `failed_attempt`。全部是 `infra_error` 的题不出卡，写在 manifest 的 `omitted_infra_only`。
- mock 测试不再往仓库的 `reports/` 和 `traces/` 写文件。

全量测试：`python -m pytest -q`，321 passed，1 skipped。花费 0。没有调用模型，没有改 coding-harness。

## 第 1 步：v6 final（2026-09-29）

用 dev 交接 `memory-source-runs.json` 和 pool 交接 `main-b0-runs.json`（`sprint6.main-b0-runs.v2`）生成 `benchmarks/a5/memory-cards-v6.jsonl`。`sprint6.main-b0-runs.v1` 会被拒绝。pool 的 issue 从 `public_task` 读取，并核对 `issue_sha256`。

- 卡片 70 张。没有全部是 `infra_error` 的题。
- `cards_sha256`：`3416eb9d8f6119081330fb3b0a2d612b8fde4678d6ec1c73a7fc681cedfcfc70`
- dev 交接 sha：`984826707e8f69ad9b900134bd244c6056f2d8860f3036a3606bfc60b4bcb450`
- pool 交接 sha：`fe0f47b8df67730a0335d7109631dc09bc4d6b5d19a601acfec0963f5dcb1f8c`
- jsonl 242190 字节。渲染后的卡片字节：最小 614，四分位 855，中位 1036，四分位 1328，最大 1500。

| repo | validated_fix | failed_attempt |
| --- | --- | --- |
| django/django | 12 | 2 |
| pytest-dev/pytest | 11 | 3 |
| scikit-learn/scikit-learn | 12 | 3 |
| sphinx-doc/sphinx | 8 | 3 |
| sympy/sympy | 7 | 9 |

F2P/P2P id 检查：轨迹字段命中 0，公开 issue 里命中 0。检查只在内存里读了私有 id，没有把 id 写进卡片或日志。有 4 条来源题测试命令原来带了这些 id，写入前换成了 `[hidden-test]`。

预期可注入表按 6B 交给 harness 的 D6，这里没有做。

预注册追加项在 `docs/sprint/A5-MAIN-PREREG-ADDENDUM.zh-CN.md`，和 `scripts/analyze_a5_main.py` 一起提交。主要分析仍只用 r1–r3，分母仍是有效运行数。次要分析改为预测注入至少 1 张卡，实际注入只做核对。漂移、r4 敏感性和按 B0 档位都标成描述性，不做检验。

花费 0。没有调用模型，没有改 coding-harness。停下等审计。第 2 步等 harness 写完 CHECKPOINT-6。
