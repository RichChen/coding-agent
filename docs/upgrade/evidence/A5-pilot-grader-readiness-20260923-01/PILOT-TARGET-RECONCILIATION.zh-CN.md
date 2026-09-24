# Pilot 20 target grader readiness reconciliation

日期：2026-09-23。此记录只汇总 pilot target 的既有 grader 收据与本次 image-backed full-collection 校验；不代表 pilot 已启动或授权。

## 对账结论

- pilot 矩阵的 20 个 target 中，Cursor 提供的 3 个 `pytest-dev__pytest-8365`、`pytest-dev__pytest-9359`、`pytest-dev__pytest-7220` 与 pilot base commit 一致，47-final-audit 中均有 `grader_ready=true` 的既有收据。
- 其余 17 个 target 中，16 个有 baseline-ready 和 known-good 镜像输入；`django__django-13265` 为 `baseline_mismatch`，其 F2P 合同与实际 baseline 不一致，故没有将它作为正常 grader 校准运行。
- 本目录对其余 16 个运行了完整仓库 collection-only 检查。结果 14 个 collection 完整且 cleanup verified；`sympy__sympy-18532` collection 有 ImportError，`scikit-learn__scikit-learn-25570` 因 Docker control timeout 为 `invalid_env`。各结果、原始 stdout/stderr、runner evidence 和 artifact hash 见同目录 `receipts.json`、`tasks/`、`artifact-manifest.json`。
- 所有本次运行均为 `model_calls=0`、`paid=false`。没有启动 provider、agent、memory build 或 pilot。

## 重要口径限制

`scripts/calibrate_a5_image_grader.py` 当前把三项 negative check 以固定返回值写入 calibration receipt，并没有实际逐 target 执行这些 negative checks；同时其 `known_good_target_status` 读取的字段在 47-final-audit 行中为空。虽然对应的历史 known-good receipt 显示 `known_good_pass=true`，本次 collection-only 结果仍不能单独作为新的完整 private-grader calibration receipt。

因此，本次 14 个成功项应解释为“pilot target full-repository collection 和环境可运行的新增证据”，而不是 14 个已经完整通过 private grader calibration、或已绑定 canonical 的 target。H1 的 canonical target grader readiness 仍应保持未绑定，直到校准器的负例检查真实执行、known-good receipt 与 pilot target/base/image 一一绑定，并由 H3 双端复核。

## 后续需处理

1. 修正并测试 calibration runner：真实执行 protected-path、missing-receipt、input-integrity negative cases；强制核对 target/base/image 以及 known-good receipt。
2. `sympy__sympy-18532`：按 collection error 查明该目标固定依赖/测试兼容性，生成新 image attempt 后重跑；不得忽略 collection error。
3. `scikit-learn__scikit-learn-25570`：排查 Docker control timeout 后单目标重试；保留本次 `invalid_env` 记录。
4. `django__django-13265`：先版本化解决 baseline/F2P 合同不一致，再生成新 baseline/grader 证据；不能以旧结果覆盖。
5. 生成独立 canonical binding/reconciliation attempt，并重新检查全部 H3 blockers。旧的 78 matrix lock 与本次运行输出不被改写。
