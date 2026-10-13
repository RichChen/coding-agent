# A6-R 冻结记录

日期：2026-10-13。依据：`A6-R-PLAN.zh-CN.md` 第 5 节 A6-2、`AUDIT-A6-1b.zh-CN.md` 第 3 节。

harness tag `a6-retry-freeze` 指向加入本文件的提交。它的父提交 `4b10d63c75a89540c6f72e1efa8119a931cfc0f3` 只是审计文件入库；最后一次代码改动是 `69178cc`（runner），记录和清单是 `27a7a0a`。

coding-agent tag `a6-retry-freeze-r2` 指向 `6c67739e8816621826493d9ef4ca4da64508ac37`，见 agent 的 `docs/sprint/CHECKPOINT-A6-1c.md`（第 9 行）。`a6-retry-freeze` 和 `a6-retry-freeze-r1` 保留不动。

从这里到 A6-3 结束，不改 runner、grader、镜像、记录和清单，也不因为 canary 或中途结果调整模板、槽位或停止条件。必须改代码时单独提交，并在 CHECKPOINT 里写明影响了哪些已完成的运行。

## 输入文件

sha 用 `scripts/handoff_sha.py` 的 `handoff_sha256` 算：先把换行统一成 LF，再取 sha256。

| 文件 | sha256 |
| --- | --- |
| `docs/sprint/a6-attempts.json`（53 份记录的清单） | `bd93252922c990ec61071caecb5a6bf5e604202cbbcf30d296f2b875794dd3ce` |
| `configs/sprint/b0-v2.yaml` | `ddf53b2db293bf03c7a099a43a34ea96aee5ecca365d9b8b4f11d66afb344e60` |
| `configs/sprint/main-targets.yaml` | `3556a5fdfac8b7d4ac2b631a31e2a7951312523aff605014f3b32eaf184738a4` |
| `scripts/run_a6_retry.py` | `aa1c8a6ace488ec7599f1c54eeab3278e1b29ecccf5b9479bf51999bf670b971` |
| `scripts/build_a6_attempts.py` | `688e79f42770a30bd8355e8b1c7117c603f047d1b667628521b64d02b5157216` |
| `scripts/run_swe_task.py` | `dca20cc63b6ac70f1f200876136332cf7c0fe2c8b50e0b44bd71d5fdef31d3c3` |
| `scripts/run_a5_main.py`（只复用，未修改） | `e298c1a80dbb28d8e4cd95d7f805a98102e4b04c7a5495ad62bee0b5d9d9fde0` |

`b0-v2.yaml` 和 `main-targets.yaml` 的 sha 与 `A5-MAIN-FREEZE.md` 记录的相同。

模板 sha（`build_a6_attempts.template_sha256()`，即模板全部文字和上限）：`7bed7ba8560276be361c3840393baefdf103f954ad4dbcf8636f0de1e021b32e`。runner 启动时会核对清单里的 `template_sha256` 是否等于当前代码算出的值。

## 运行参数

| 参数 | 值 |
| --- | --- |
| 槽位 | 53 份记录 × {r0, r1} × k∈{1,2,3} = 318 |
| 打乱 | 按 (task, arm, first, k) 排序后 `random.Random(20261013).shuffle` |
| `PARALLEL` | 3 |
| `TOTAL_CAP` | 210 元 |
| `MAX_INFRA_RERUNS` | 2（目录改名为 `r<k>.infra<n>`） |
| 调用上限 | 40（`b0-v2.yaml` 的 `max_model_calls`） |
| 模型（配置解析结果） | `deepseek-flash`，base_url 主机 `api.deepseek.com`；canary 实际记录的值作为后续基准 |
| 正式目录 | `runs/a6-retry/<task>/<arm>/<first>/r<k>` |

Docker Desktop：8 核，约 9.7 GiB 内存。

## canary 槽位

规则：队列里第一个、第二个 R0 槽位，加第一个、第二个 R1 槽位，按队列顺序跑。在当前清单下，这 4 个正好是队列的前 4 个：

1. `django__django-15022/r1/b0r2/r3`
2. `pytest-dev__pytest-7324/r0/b0r2/r3`
3. `sphinx-doc__sphinx-7590/r0/b0r1/r3`
4. `sympy__sympy-19040/r1/b0r3/r3`

canary 是正式运行的一部分，A6-3 续跑时这 4 个槽位按已完成处理，不重跑。

## 停止条件

任一满足就不再启动新运行，在跑的运行结束后写 CHECKPOINT。

计划第 1 节：

- 累计 `infra_error` 超过已完成运行数的 10%（同 A5：同时要求至少 3 次）；
- 任何 `answer_isolation_pass=false` 或 source-only 校验失败；
- grader 报 `missing` 或崩溃；
- R0 的 `prompt_sha256` 与 A5 B0 不同，或者 R1 实际发给模型的第一条 user 消息不等于"A5 B0 prompt + 清单里该 first 的记录全文"（每次运行后从 `events.jsonl` 核对）；
- 模型名或 base_url 主机与 canary 不同（runner 要求正式目录内所有运行一致，出现 `changed_to` 也停）；
- 累计花费达到 210 元。

第 1 节以外沿用 A5 的条件：任何一次运行 `harness_tool_errors > 0` 就停（A5 全程为 0）。按审计决定，不接 A5 的 `fault_alarm`。

A6-2 另加一条人工规则：单次运行花费超过 1.5 元就停，不进入 A6-3。

## 冻结前的检查

- 全量测试（`.venv`，在 `4b10d63` 上）：661 passed，22 skipped。
- `--preflight` 在 canary 之前、同一次开机里重跑，结果写在 `CHECKPOINT-A6-2.md`。
