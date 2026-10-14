# CHECKPOINT-4（2026-09-25）

停在这里。没有把 interim v4 改成 final，没有用 `b0-v1` 交接文件重建卡片，没有跑 memory smoke，没有调模型。花费 0。

## 提交

tag `mem4-start` 在 `3d9cccc`。B2 过滤在其后的提交里。

## B2

`MemoryCardPlugin` 的 B2 只检索 `verification_status == validated_fix` 的卡。`failed_attempt` 和 `unverified` 不会被注入。B1 仍会选这些卡，B3 的依赖检查没改。

测试 31 passed，覆盖插件、v2/v3/v4 卡片、源题验证和两种目录格式的提取器。

## 交接文件

`D:\crq\src\coding-harness\docs\sprint\memory-source-runs.json` 存在，但不符合重建条件：

- `profile_tag` 是 `b0-v1`，不是 `b0-v2`
- `runs` 有 42 条
- 各条都没有 `answer_isolation_pass=true`（字段缺失）

这批轨迹是测试可见条件下的历史证据。`benchmarks/a5/memory-cards-v4.manifest.json` 仍是 `status=interim`。

留一法表没有用这批 interim 卡重跑。等隔离通过的 `b0-v2` 交接文件到了，再重建 final，并按新的 B2 规则重出留一法。

## 2026-09-26：交接已到

上面的停止条件已经满足。`memory-source-runs.json` 是 `b0-v2`，42 条全部 `answer_isolation_pass=true`。LF sha256 `89c33557b611fdb0578c050b54952a7c8a5b062e115db097f619b456ae84d073`。

已重建 `benchmarks/a5/memory-cards-v4.jsonl`。manifest `status=final`，`cards_sha256=d31af37b612ae38f12eb40bcdba05b0de8ad7ab1c6e2622a440b9347ceaf2017`，`memory_source_runs_sha256` 等于上面的交接哈希。7 张 `validated_fix`，7 张 `failed_attempt`。没有 `pytest-5221`。没有跑 memory smoke，没有调模型。
