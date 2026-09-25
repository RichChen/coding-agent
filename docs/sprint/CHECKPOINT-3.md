# 第三轮审计节点

日期：2026-09-25。本轮模型花费 16.173 CNY，上限 40 CNY。到这里停下，等审计。

## 第 1–3 步，以及对 CHECKPOINT-2 的更正

CHECKPOINT-2 说 sklearn 的 `.so` 进了 delta。计划书第 0 节说 delta 里没有 `.so`。两边都只看了 `changed`。诊断结果：三份保存的 delta 里，`changed` 各只有一个 `.py`，`deleted` 里各有约 40 个 `.so`。运行前把扩展模块换成了指向镜像的符号链接，导出时符号链接被跳过，原文件就被记成删除。评分器应用删除后，`sklearn.__check_build._check_build` 导入失败，收集数为 0。空 delta 可以收集测试。修复是导出和评分都跳过编译产物。重打分后 10297 和 11281 解出，10949 仍是模型失败（`test_check_dataframe_warns_on_dtype`）。三题 gold 校准仍然通过。

11870 当时 `step_deadline` 取消了正在执行的命令，`docker exec` 随即删掉容器，导出没有发生，`snapshot_error` 是空的。现在命令超时把结果交回模型，运行结束时先导出。容器已经不在时，`snapshot_error` 写 `container_gone_before_snapshot`。事件重放改了 `fu.py` 和 `trigsimp.py`，打分 F2P 0/1、P2P 58/58，没有解出。

`stop_reason` 先读运行结果里的 `termination_kind` 和 `failure_reason`。`run.finished` 只剩 `artifact_ref` 时，从 `session/artifacts/` 读回正文。`verify_memory` 改走 `ImageGrader`。pytest-5221 的原因是 `gold_fails_calibration`。

## B0 v1

tag `b0-v1` 在 14 题 mock 通过之后。之后没有改 prompt、工具集、profile 和 grader 判定逻辑。

42 次重复，预计 16 CNY，实际 16.173 CNY，单次都低于 1 CNY。解出 32/42。10 道题 3/3，2 道题 0/3（sympy-11870、sklearn-10949），2 道题混合（pytest-5103 1/3，sympy-12171 1/3）。抽查 django-10914 r1 和 sklearn-10297 r1，没有改测试。42 次 `test_files_touched` 都是空的。详见 `docs/sprint/B0-V1-RESULTS.md`。交接文件是 `docs/sprint/memory-source-runs.json`。

## pilot 校准

20 道题都没有被接受。3 道 pytest 的镜像里没有 `/opt/repo`，没有重建。django-13265 是已知合同阻塞，没有打分。9 道空改动已经通过 F2P。6 道 gold 没有通过。表在 PROGRESS 第 6 步，清单在 `configs/sprint/pilot-tasks.yaml`。没有在 pilot 上调用模型。

## 记忆

留一法测试和一次 B2 mock 通过。django-10914 的卡被过滤，注入的是 10924 和 11039。v3 卡片。v4 manifest 复查时 `status` 仍是 `interim`，`build_inputs.memory_source_runs_sha256` 仍是空的，和 `memory-source-runs.json` 对不上。第 8 步因此跳过，没有跑 B2/B3 对照，也没有自造卡片。

第 9 步只写了 `docs/sprint/MEMORY-SOURCE-EXPANSION.md`。没有做那一道 sphinx 试跑，因为本地没有可用的 sphinx baseline 镜像，本轮不现场重建。

## 花费

| 步 | 花费 |
| --- | --- |
| 1–4、6、7 | 0 |
| 5 | 16.173 |
| 8 | 跳过 |
| 合计 | 16.173 |

## A5-lite 建议

第 5 步里 14 题有 2 题是 1/3，所以一次重复不够看稳定性，三次能分开「稳定解出」「稳定失败」和「混合」。建议 lite 用 20 道 pilot 里镜像可用的题，变体只留 B0 和 B2，每题 3 次。按本轮每次约 0.39 CNY，20 × 2 × 3 = 120 次，约 47 CNY。django-13265 和三道没有 `/opt/repo` 的 pytest 先不要算进分母。
