# CHECKPOINT-2

日期：2026-09-25。范围：`sprint2-start..HEAD`。本轮花费 **4.390 CNY**。没有跑 20 道 pilot，也没有改 coding-agent。

## 提交

- `7208395` 忽略 private-spec，summary 能看出 `delta_lost`
- `810d415` agent 改跑 baseline 镜像，delta 不再用 gold 白名单
- `26ceecc` 镜像内 grader
- `65a874d` 12 题校准后的 dev 集
- `1b020d3` 11 条记忆源重打分
- `5b904df` grader spec 不再哈希整棵树

## 校准

20 道候选都跑了空改动和 gold。入选 12 道：django 10914、10924、11039；pytest 5103、5227；sympy 11400、11870、11897、12171；sklearn 10297、10949、11281。空改动 F2P 为 0，gold 下 F2P 和保留的 P2P 通过。django 10914 排除 2 条 P2P，11039 排除 4 条。

未入选：django 11001、11019 空改动已经通过部分 F2P。pytest 5221 gold 没通过 F2P。pytest 5413、5495 没有收据。sympy 12236 gold 没通过。

## 重放

5227 的第一轮编辑（`logging.py` 加 changelog）在新 grader 上解出，F2P 3/3，P2P 31/31。5221 没有解出，F2P 0/2，P2P 0/170。

## 记忆源

5 条 pass：django 10914、10924、11039，sklearn 10297、11281。5 条 fail：sympy 11400、12171，pytest 5103，sklearn 10949、11040。pytest 5221 是 `grader_unavailable`。

## B0 和 thinking

12 题解出 6 题，费用 4.390 CNY。前 3 题没有 `delta_lost`，也没有装依赖。后面 sympy-11870 出现一次 `delta_lost`。sklearn 三题的 delta 混进了 `.so`，P2P 被打成 0。thinking 对照没有跑：客户端拒绝 `thinking: enabled`。

## 建议

导出 delta 时不要把镜像里的 `.so` 算成模型改动。查 sympy-11870 为什么编辑没有进 delta。thinking 要等 reasoning 回放做好再比。
