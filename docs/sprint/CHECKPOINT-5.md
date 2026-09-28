# CHECKPOINT-5（2026-09-26）

停在这里，等审计。没有调模型，花费 0。没有改 coding-harness，没有改检索或渲染规则，没有碰 R6 数据。

## 提交

tag `mem5-start` 在 `b96c4d8`。其后：

- `6a26357` interim v5，卡片带 `repo` 和 `created_at`
- `6da4ec6` 通用构建脚本，输出和 v5 逐字节一致
- `d57c14d` 分析脚本，只用合成数据
- `1a04e0e` dev 按时间留一法

## v5

`sprint5.memory-source-runs.v2` 还没出现。`HANDOFF-CONVENTIONS.md` 也还没写，sha256 用的是 UTF-8 + LF。

`benchmarks/a5/memory-cards-v5.manifest.json`：

- status：`interim`
- cards_sha256：`3ac51554f0e7c56e22fc8135e310ac01f2b6ab9136d44bac33dcddab2ece83ca`
- memory_source_runs_sha256：null
- interim_handoff_sha256：`89c33557b611fdb0578c050b54952a7c8a5b062e115db097f619b456ae84d073`（现有 b0-v2 交接文件的 LF 哈希）
- handoff_schema：`sprint4.memory-source-runs.v1`

14 张卡。`created_at` 来自 canonical handoff 的公开 `historical_pr_created_at`，不在渲染正文里。缺 `repo` 或 `created_at` 时构建失败。7 张 `validated_fix`，7 张 `failed_attempt`，和 v4 选中的 repeat 相同。

## 通用构建

`scripts/build_memory_cards.py --handoff <文件> --out <jsonl>` 不写死源题清单。用 dev 交接文件再跑一次，jsonl 和 v5 逐字节一致。同时检查了目标题 id、gold/test patch 的长行和隐藏 nodeid 没有进入卡片。

## 分析脚本

`scripts/analyze_a5_main.py`。合成数据三组都通过：零效应时结论是“没有检出大于 49.0 个百分点的效应”；六题全解出时报告 100.0 个百分点；`infra_error` 不进分母，有效运行不足 2 次的题被列出来。样例报告是正效应那一组：`docs/sprint/A5-MAIN-SYNTHETIC-REPORT.md`。

## 按时间留一法

表在 `docs/sprint/DEV-TIME-SELECTION.md`。14 道里 6 道会注入至少一张更早的 `validated_fix`。sympy 四题和 pytest 两题目前没有可注入的卡，因为同仓库里没有更早的已验证修复。

## 2026-09-28：v2 交接文件已到

`memory-source-runs.json` 已升级为 `sprint5.memory-source-runs.v2`。v5 已重建为 final。

- cards_sha256：`40d22ef838af7172ba8e72b09954107ea055d65501e11219c71ae2e0a88c015c`
- memory_source_runs_sha256：`984826707e8f69ad9b900134bd244c6056f2d8860f3036a3606bfc60b4bcb450`
- `created_at` 来自交接文件本身，例如 django-10914 是 `2019-01-30T13:13:20Z`
- `cards.py`、`cards_v3.py`、`cards_v4.py` 不再用 `1970-01-01` 填时间，缺字段直接报错

## 花费

0。
