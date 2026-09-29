# A5-main 案例数据（描述性，非预注册）

核对：c85886c，table/follow 与正文一致。

日期：2026-09-29。审计侧根据 `runs/a5-main/`、`docs/sprint/b2-predicted-injection.json` 和 v6 卡片整理。
gold 只取 `+++ b/` 的路径，不记录 patch 文本。卡片文件去掉测试路径。
coding-agent 写最终报告时引用本文件第 7 节，不要自己重新扫轨迹。

核对脚本：`.tmp/case_mem.py` 的 `table` / `follow` / `task`。收尾时复跑，数字必须一致。

## 1. 卡片文件与 gold 文件重合

注入至少 1 张卡的题 51 道。卡片非测试文件与 gold 文件有交集的 9 道，没有交集的 42 道。未注入的 5 道。

| 分组 | n | 平均 d_t |
| --- | --- | --- |
| 有重合 | 9 | −0.074 |
| 无重合 | 42 | +0.016 |
| 未注入 | 5 | −0.200 |

未注入的 5 道：`sklearn-9288`、`sphinx-7440`、`sympy-13757`、`sympy-11618`、`sympy-14248`。前三道从 3/3 掉到 2/3，后两道 d_t = 0。

### 有重合的 9 道

这 9 道的 B0 全部是 3/3 或 0/3。其中 8 道 d_t = 0，只有 sphinx-9673 从 3/3 掉到 1/3。

| 题 | B0 | B2 | 共享文件 | 注入卡片 |
| --- | --- | --- | --- | --- |
| django-11211 | 3/3 | 3/3 | `django/db/models/fields/__init__.py` | 10924, 10914 |
| django-13512 | 0/3 | 0/3 | `django/forms/fields.py` | 12276, 10924, 13109 |
| sympy-17655 | 3/3 | 3/3 | `sympy/geometry/point.py` | 11618, 16766, 13757 |
| sympy-22714 | 3/3 | 3/3 | `sympy/geometry/point.py` | 17655, 16766, 13757 |
| sklearn-13142 | 3/3 | 3/3 | `sklearn/mixture/base.py` | 12585, 11281, 9288, 10297 |
| sphinx-9461 | 0/3 | 0/3 | `sphinx/util/inspect.py` | 7910, 8120, 8459 |
| sphinx-9673 | 3/3 | 1/3 | `sphinx/ext/autodoc/typehints.py` | 8459, 7910, 8593 |
| pytest-7521 | 3/3 | 3/3 | `src/_pytest/capture.py` | 5262, 7490, 6202 |
| pytest-10081 | 3/3 | 3/3 | `src/_pytest/unittest.py` | 5262, 8399, 7521, 7982 |

## 2. agent 是否按卡片走

153 次注入了卡片的 B2 运行（51 道 × 3）。

- 打开过"卡片提到、不在 gold 范围内、并且该题三次 B0 都没打开过"的文件：5 次。
- 最终修改落在这类文件上：0 次。

| 题 | 槽位 | 打开的卡片独有文件 | 最终改在这里？ |
| --- | --- | --- | --- |
| django-13964 | r2, r3 | `django/db/models/fields/__init__.py` | 否 |
| sphinx-9258 | r1, r3 | `sphinx/ext/autodoc/typehints.py`、`sphinx/util/inspect.py` | 否 |
| sphinx-9673 | r1 | `sphinx/ext/autodoc/__init__.py` | 否 |

## 3. d_t ≠ 0 的题

| 题 | d_t | B0 | B2 | 卡片–gold 重合 | 注入 |
| --- | --- | --- | --- | --- | --- |
| sphinx-9673 | −0.67 | 3/3 | 1/3 | 是 | 8459, 7910, 8593 |
| django-13964 | −0.67 | 2/3 | 0/3 | 否 | 11211, 13109, 11039 |
| django-11749 | −0.33 | 3/3 | 2/3 | 否 | 11039, 10914 |
| sympy-13757 | −0.33 | 3/3 | 2/3 | 否 | 无 |
| sklearn-9288 | −0.33 | 3/3 | 2/3 | 否 | 无 |
| sphinx-7440 | −0.33 | 3/3 | 2/3 | 否 | 无 |
| sphinx-8459 | −0.33 | 3/3 | 2/3 | 否 | 7910, 7440, 8120 |
| sphinx-8593 | −0.33 | 3/3 | 2/3 | 否 | 8120, 8459, 7440 |
| django-15022 | −0.33 | 1/3 | 0/3 | 否 | 10924, 11211, 13109 |
| sympy-19040 | −0.33 | 1/3 | 0/3 | 否 | 17655, 11618, 13757 |
| sympy-13091 | +0.33 | 0/3 | 1/3 | 否 | 11618 |
| sympy-15599 | +0.33 | 0/3 | 1/3 | 否 | 13757, 11618 |
| sympy-23950 | +0.33 | 1/3 | 2/3 | 否 | 22714, 17655, 19040, 11618 |
| sklearn-10908 | +0.33 | 2/3 | 3/3 | 否 | 9288, 10297 |
| pytest-7490 | +0.33 | 2/3 | 3/3 | 否 | 5262, 7205, 6202 |
| sphinx-8120 | +0.67 | 1/3 | 3/3 | 否 | 7440, 7910 |
| sphinx-9258 | +0.67 | 1/3 | 3/3 | 否 | 8459, 8120, 7440 |

## 4. 三个细案例

### sphinx-9673

- gold 文件：`sphinx/ext/autodoc/typehints.py`。gold hunk 上下文：`def augment_descriptions_with_types(`。
- 卡片 8459 的依赖符号是 `record_typehints`，approach 是轨迹中途叙述。
- 6 次运行都改了 `augment_descriptions_with_types`。B0 r2 额外改了 `modify_field_list`。没有一次改 `record_typehints`。
- 新增行数：B0 三次分别 1、2、2 行（全解出）；B2 三次分别 1、2、1 行（只有 r2 解出）。
- B2 r1 打开过卡片提到的 `sphinx/ext/autodoc/__init__.py`，最终没改它。

### sphinx-9258

- gold 文件：`sphinx/domains/python.py`。
- 注入卡片：8459（typehints）、8120（locale）、7440（std glossary），都与 gold 文件无交集。
- B2 r1、r3 先打开了 `typehints.py` 和 `inspect.py`，最终在 `python.py` 解出。
- 提升不能归因于卡片内容。

### django-13964

- gold 文件：`django/db/models/base.py`。
- 注入卡片：11211（contenttypes UUID）、13109（ForeignKey.validate）、11039（sqlmigrate），都无关。
- B2 r2、r3 打开过卡片里的 `fields/__init__.py`，最终修改落在 `related_descriptors.py`，和 B0 解出的那次同一区域。
- B2 r3 删掉外键赋值分支，按 missing_regrade 记为普通失败。B0 r2 是 delta_lost（自己撤回）。
- 单次成功率大约一半，连续 3 次失败约 1/8。
