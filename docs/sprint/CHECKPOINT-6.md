# CHECKPOINT-6

日期：2026-09-28。第 0 步已完成。第 1 步等 harness 写完 CHECKPOINT-6a 再做。

## 冻结

tag `a5-main-freeze` 指向 `a22e4ca0a3994012c167a3e02e06498731c24a18`。

这一步改了三件事：

- 解出率分母改为有效运行数，`infra_error` 不计入。有效运行少于 2 次的题仍然不进主要分析。
- 没有解出时，取编号最小的非 `infra_error` 运行作为 `failed_attempt`。全部是 `infra_error` 的题不出卡，写在 manifest 的 `omitted_infra_only`。
- mock 测试不再往仓库的 `reports/` 和 `traces/` 写文件。

全量测试：`python -m pytest -q`，321 passed，1 skipped。花费 0。没有调用模型，没有改 coding-harness。
