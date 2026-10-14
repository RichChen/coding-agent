# A5 Memory Pool S1 Smoke Report

日期：2026-09-22T10:04:02.828253+00:00
attempt：`A5-memory-pool-74-s1-smoke`

## 结果

- 6/6 端到端 plumbing（4 families），均为 failed/no_candidate_changes
- candidate=0, validated=0
- paid attempts=12, model_calls=64, spent_cny=0.417

## 每源主结果（优先 reverify）

- `django__django-10914`: failed / no_candidate_changes / calls=6 / 0.038 CNY
- `django__django-10924`: failed / no_candidate_changes / calls=6 / 0.039 CNY
- `pytest-dev__pytest-5103`: failed / no_candidate_changes / calls=3 / 0.020 CNY
- `scikit-learn__scikit-learn-10297`: failed / no_candidate_changes / calls=5 / 0.035 CNY
- `sympy__sympy-11400`: failed / no_candidate_changes / calls=6 / 0.041 CNY
- `sympy__sympy-11870`: failed / no_candidate_changes / calls=5 / 0.029 CNY

## 修复与复验

1. 初跑全部 paid 但无 edit；11870 曾因 pycache export 失败。
2. 修复：强化 edit prompt + export 前清 pycache + 公开树校验。
3. 一次复验仍 no_candidate_changes；停止原样重试。

## 下一步

S2 在出现可验证 candidate delta 前 blocked。
