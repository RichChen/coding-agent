# A5-main 冻结记录

harness tag `a5-main-freeze` 指向加入本文件的提交。它的父提交 `2b1d2442c88d869534c8c54a3a667310477808c4` 是第 0 步的代码改动（infra_error 重跑、停止条件、模型记录）。

coding-agent tag `a5-main-freeze` 指向 `a22e4ca0a3994012c167a3e02e06498731c24a18`（见 coding-agent 提交 `1053203` 的 CHECKPOINT-6）。

从这里到 R6 结束，不改 runner、grader、镜像和校准。只有停止条件要求时才改，改动单独提交并在 CHECKPOINT 里写明影响了哪些已完成的运行。

## 输入文件

sha 用 `scripts/handoff_sha.py` 的 `handoff_sha256` 算：先把换行统一成 LF，再取 sha256。

| 文件 | sha256 |
|------|--------|
| `configs/sprint/main-targets.yaml` | `3556a5fdfac8b7d4ac2b631a31e2a7951312523aff605014f3b32eaf184738a4` |
| `docs/sprint/main-accepted-ids.txt`（56 道合格题） | `d71cb17adb44fd06f71bf8b0f8babcac12ea839354f1dcec30aae2ffa719b730` |
| `configs/sprint/b0-v2.yaml` | `ddf53b2db293bf03c7a099a43a34ea96aee5ecca365d9b8b4f11d66afb344e60` |
| `docs/sprint/memory-source-runs.json`（dev 交接） | `984826707e8f69ad9b900134bd244c6056f2d8860f3036a3606bfc60b4bcb450` |

`main-accepted-ids.txt` 是 `docs/sprint/main-calibration/*.json` 里 `accepted: true` 的 id，按字母排序，每行一个，末尾有换行。各仓库题数：pytest 12，sympy 12，django 11，sphinx 11，scikit-learn 10。

## 运行参数

| 参数 | 值 |
|------|----|
| `PARALLEL` | 4（B0 与 B2 相同） |
| `TOTAL_CAP` | 150 元 |
| B0 软上限 | 80 元 |
| `MAX_INFRA_RERUNS` | 2 |
| infra_error 停止线 | 超过已完成运行的 10% |

Docker Desktop：8 核，7.7 GiB 内存。
