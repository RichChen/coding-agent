# A5 Memory Pool S1-75 Smoke Report

日期：2026-09-22T10:57:19.416573+00:00

## 预算调整

- max_model_calls 6→24；context 32k→96k；max_steps 20→35

## 结果（主结果取 reverify）

- candidate=5: django__django-10914, django__django-10924, pytest-dev__pytest-5103, scikit-learn__scikit-learn-10297, sympy__sympy-11400
- failed=1: sympy__sympy-11870
- validated=0（待 provenance review，未自动升格）
- paid attempts=12, model_calls=282, spent_cny=3.366

## 说明

首轮加大预算后多数源已开始 edit，但因 docs 不在 allowlist / 写文件改 mode 导致 delta 导出失败。
修复 allowlist + export 前恢复 mode 后复验：5/6 candidate。sympy-11870 仍无 edit，停止原样重试。
