# 题目池校准

已处理 60 道。合格 56 道。

| 仓库 | 合格 | 剔除 |
| --- | --- | --- |
| django/django | 11/12 | django-7530：empty_f2p_did_not_fail |
| sympy/sympy | 12/12 | 无 |
| scikit-learn/scikit-learn | 10/12 | scikit-learn-25232：numpy==1.19.2 has no Python 3.9 wheel; its source cannot be compiled with Cython 3.0.10；scikit-learn-25973：numpy==1.19.2 has no Python 3.9 wheel; its source cannot be compiled with Cython 3.0.10 |
| sphinx-doc/sphinx | 11/12 | sphinx-8721：empty_f2p_did_not_fail |
| pytest-dev/pytest | 12/12 | 无 |

## Django 测试 id

SWE-bench 把带 docstring 的测试记成 docstring 第一行。校准时在应用了测试补丁的源码树上用 `ast` 找到唯一匹配的测试方法，映射成 `module.Class.method`。零个或多个匹配算定位失败；F2P 定位失败的题排除（`f2p_unaddressable`），P2P 定位失败的丢弃。

| 题 | F2P 原始/使用/映射 | P2P 原始/使用/映射 | 丢弃 |
| --- | --- | --- | --- |
| django-11211 | 1/1/0 | 76/76/1 | 无 |
| django-11749 | 1/1/0 | 34/34/3 | 无 |
| django-12276 | 2/2/0 | 117/117/3 | 无 |
| django-13109 | 2/2/0 | 170/169/9 | P2P docstring_ambiguous 1 |
| django-13512 | 3/3/0 | 32/32/1 | 无 |
| django-13964 | 1/1/0 | 36/36/1 | 无 |
| django-14434 | 1/1/0 | 133/128/49 | P2P docstring_ambiguous 5 |
| django-15022 | 3/3/2 | 56/54/24 | P2P docstring_ambiguous 2 |
| django-15499 | 1/1/0 | 35/35/20 | 无 |
| django-15973 | 1/1/0 | 157/152/89 | P2P docstring_ambiguous 5 |
| django-16527 | 1/1/0 | 6/6/3 | 无 |
| django-7530 | 1/1/0 | 59/59/0 | 无 |

## 扫描排除的文件

合格题的全文件系统扫描里，下列命中按规则排除。`/opt/repo` 下和目标项目顶层包目录下的命中不适用这两条排除。

| 题 | 文件 | 排除理由 |
| --- | --- | --- |
| pytest-dev__pytest-5631 | `/usr/local/lib/python3.9/pickle.py` | 基础镜像里同一路径、同一 sha256，是 Python 自带文件，不是构建时写入的 |
| pytest-dev__pytest-5631 | `/usr/local/lib/python3.9/pickletools.py` | 基础镜像里同一路径、同一 sha256，是 Python 自带文件，不是构建时写入的 |
| pytest-dev__pytest-5631 | `/usr/local/lib/python3.9/runpy.py` | 基础镜像里同一路径、同一 sha256，是 Python 自带文件，不是构建时写入的 |
| pytest-dev__pytest-5631 | `/usr/local/lib/python3.9/site-packages/attr/_cmp.py` | sha256 与 pip RECORD 记录一致，是未改动的第三方依赖文件 |
| sphinx-doc__sphinx-8120 | `/usr/local/lib/python3.9/site-packages/babel/messages/mofile.py` | sha256 与 pip RECORD 记录一致，是未改动的第三方依赖文件 |
| sphinx-doc__sphinx-8120 | `/usr/local/lib/python3.9/site-packages/babel/messages/pofile.py` | sha256 与 pip RECORD 记录一致，是未改动的第三方依赖文件 |
