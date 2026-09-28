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

## 修订 1

tag `a5-main-freeze-r1` 指向加入本节的提交。原 tag `a5-main-freeze` 保留不动。依据是 `docs/sprint/HARNESS-SPRINT-6A-FIX.zh-CN.md` 和 CHECKPOINT-6 的两次审计结论。

### 原因

canary 里 sphinx-8593 在运行前比对失败。构建镜像时，`pre_install` 用 sed 改写的文件不参与 source-only 比对；运行时却参与了，而且没有排除。12 道题会因此在运行前失败（11 道 sphinx 和 pytest-8399）。镜像本身没有问题，也不是泄漏。

### 改动与提交

| 项 | 内容 | 提交 |
| --- | --- | --- |
| F1 | 被改写的文件按"在 clean image 的 /tmp tmpfs 里断网重放 sed 后的期望 sha"比对，不再有跳过不比的文件；构建和运行都通过 `overrides_for` 读同一份 `docs/sprint/rewritten-expected/<task>.json` | `a3b4450`、`53c072a` |
| F2 | `run_a5_main.py --preflight`：56 道题执行全部运行前检查，不调用模型 | `43ee604` |
| F3 | `--out-root`（只能和 `--mock` 一起用）和全池 mock 核对脚本 `scripts/sprint6_mock_e2e_check.py` | `43ee604`、`a3cdc3a` |
| F4 | 移动 sphinx-8593 的失败槽位，见下文 | 只移动文件，没有提交 |
| F5 | infra_error 次数 ≥ 3 **并且**超过已完成运行的 10% 时才停止 | `653ebbb` |

`docs/sprint/rewritten-expected/` 在本修订中的 git tree 是 `dab524dfff1c46344e1a3ec524b66048739c140e`。

### 改写命令的解析规则

- **guarded_sed**（审计批准新增）：一条命令按 `&&`、`||` 拆开后，每一段都是 `sed -i … <文件>` 或 `grep -q … <文件>`，至少有一段是 sed，并且都指向同一个不含 `/` 的文件。这时整条命令原文算作这个文件的改写命令，重放时整条交给 `/bin/sh` 执行，顺序和规格一致。
- **plain_sed 的收紧**：原来的"以 sed 开头、最后一个词不含 `/`"规则保留，但现在要求整条命令只有一段。否则 `sed … && pip install -e .` 会被误算成对 `.` 的改写。
- 其他命令都不算改写，比对时也不为它们放宽。
- 记录里每条命令都标明匹配的规则（`plain_sed` 或 `guarded_sed`）。
- 这次规则修改只影响 sphinx-9258：它的 `setup.py` 多了 2 条 guarded_sed 命令，期望 sha 是 `27bcaf655c0321c29b0c30ce9c740c8551c63a67cefd9a89436c05361cf5255a`。另外 11 份记录只新增了 `rules` 字段，其他内容不变。plain_sed 的收紧不影响 56 道题中的任何一道。

### 核对口径修正

1. **F2（审计批准）**：运行时 P2P 条数等于校准 `nodeids.p2p.used` 减去 `p2p_excluded` 条数，并且每个被排除的 id 都必须在选中的 P2P 列表里。涉及 sphinx-8120、9673、10323。
2. **F3（审计批准）**：有 `p2p_excluded` 的三道题，P2P 通过数等于 `empty_p2p` 的通过数，总数等于 `empty_p2p` 的总数减去排除条数；同时确认被排除的 id 没有出现在 grader 的用例里。
3. **F3（按第二次审计的授权自行修正）**：原口径要求"F2P 全部失败，并且等于 empty_f2p"。django-13512（1/3）和 sympy-14248（1/12）在空改动下各有 1 条 F2P 通过，运行时的结果和 `empty_f2p` 完全相同。校准的合格规则（`sprint5_prepare_main.py` 的 `acceptance`）只要求空改动下 F2P 不全部通过。新口径：F2P 的通过数和总数等于 `empty_f2p`，通过数小于总数，summary 的 `solved` 为 false。依据的记录字段是校准 JSON 的 `empty_f2p` 和 `accepted`。

三处都只改核对口径，不改任何运行时行为。

### F4 规则

模型调用为 0、花费为 0、因为 harness 运行前检查的 bug 而失败的运行，不算实验数据，可以移出后重跑这个槽位。**有模型调用的运行一律不适用这条规则。**

按这条规则，`runs/a5-main/sphinx-doc__sphinx-8593/b0/r1/` 已整个移到 `runs/a5-main-halted/sphinx-doc__sphinx-8593/b0/r1/`，`runs/a5-main/b0-report.json` 移到 `runs/a5-main-halted/b0-report.json`。

### 已完成的 canary

django-13964 r1 和 sklearn-13142 r1 继续有效。它们跑在 `02c8671` 上，`pre_install` 不改写源码文件，override 为空，新旧比对规则的结果相同。它们也没有 `p2p_excluded`，两种 id 口径的结果一致。

### F2、F3 结果

- F2 预检：56/56 通过。所有题 `answer_isolation_pass` 为 true，带 override 的 source-only 比对全部通过，grader id 按修正后的口径和校准一致，public task 全部生成。
- F3 mock 端到端：56 道 mock B0 r1 写在 `runs/a5-main-mock-e2e/`，花费 0，没有停止。
  - 没有 answer isolation 失败，没有 infra_error，grader 没有崩溃，没有 `missing`。
  - 按修正后的口径 56/56 一致：F2P 等于 `empty_f2p`（54 道 0 通过，2 道部分通过）。
  - P2P 全部通过，并且等于 `empty_p2p`（三道有排除的题是 43/43、23/23、38/38）。
  - 被排除的 id 都没有进入 grader。

冻结输入的 sha 没有变化，本修订没有改 clean image、校准记录、profile 和 `src/eval`。全量测试 343 passed、199 skipped。
