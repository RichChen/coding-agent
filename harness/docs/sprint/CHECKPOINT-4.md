# 第四轮审计节点

日期：2026-09-25。本轮模型花费 14.712 CNY，上限 20 CNY。到这里停下，等审计。

## 答案隔离

只读核对过旧包：`django-11039` 的 `baseline.tar.gz` 里有 `test_sqlmigrate_for_non_transactional_databases`，original 里没有。旧镜像把这个包解进 `/opt/repo`。

clean image 只用 original `source.tar.gz`。14 道 dev 题的 source-only hash 与 original 一致，全文件系统扫描没有命中 test patch 或 gold patch 的新增行。三道题的空 delta 导出为空。sklearn 复制仓库后可以导入。

`b0-v2` 的 42 次运行 `answer_isolation_pass` 都是 true。没有因为隔离失败停波。

## 校准

14 道 dev 题的零模型校准都接受：空改动 F2P 未通过，gold F2P 全部通过，两边 nodeid 结果不同。清单在 `docs/sprint/clean-calibration/`。

20 道 pilot 没有建 clean image，也没有重做校准。旧的 0/20 仍然只说明当时的镜像和 grader 不匹配。

## v1 和 v2

v1 是测试可见条件下的历史结果，32/42。v2 是 clean image，17/42。花费 14.712 CNY，预计 16。

| 题 | v2 | v1 |
| --- | --- | --- |
| django-10914 | 3/3 | 3/3 |
| django-10924 | 2/3 | 3/3 |
| django-11039 | 3/3 | 3/3 |
| pytest-5103 | 0/3 | 1/3 |
| pytest-5227 | 3/3 | 3/3 |
| sklearn-10297 | 3/3 | 3/3 |
| sklearn-10508 | 0/3 | 3/3 |
| sklearn-10949 | 0/3 | 0/3 |
| sklearn-11040 | 2/3 | 3/3 |
| sklearn-11281 | 1/3 | 3/3 |
| sympy-11400 | 0/3 | 3/3 |
| sympy-11870 | 0/3 | 0/3 |
| sympy-11897 | 0/3 | 3/3 |
| sympy-12171 | 0/3 | 1/3 |

有几次运行改了仓库里本来就有的测试文件，记在交接文件的 `test_files_touched`。sklearn-11281 r2 是 `StoreError`，摘要里的模型调用数是 0，账本是 0.668 CNY。

## 交接

`docs/sprint/memory-source-runs.json`

- schema：`sprint4.memory-source-runs.v1`
- profile_tag：`b0-v2`
- sha256：`89c33557b611fdb0578c050b54952a7c8a5b062e115db097f619b456ae84d073`
- 42 次都带 `answer_isolation_pass: true` 和 clean image digest

v4 仍然不能转成 final。本轮没有跑记忆对照。

## 未决

- pilot 的 clean image 和重新校准还没做。
- sklearn-11281 r2 的 `StoreError` 没有重跑。
