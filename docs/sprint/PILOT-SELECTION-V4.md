# pilot 离线选择（v4，只报告）

规则与第 5 步留一法之后相同，没有再改。目标树来自 `D:/crq/tmp/a5-targets` 里的 `source.tar.gz` 解压结果。
v3 对照摘自 CHECKPOINT-2。

| 目标题 | v4 排序 | v4 B2 注入 | v4 B3 |
|---|---|---|---|
| django-13265 | django-10924 65.4；django-11039 16.3；django-10914 2.0 | django-10924 selected；django-11039 selected；django-10914 selected | django-10924 selected；django-11039 selected；django-10914 rejected_invalid |
| django-15781 | django-10924 21.5；django-10914 6.5；django-11039 3.6 | django-10924 selected；django-10914 selected；django-11039 selected | django-10924 selected；django-10914 rejected_invalid；django-11039 selected |
| django-13590 | django-10924 8.8；django-10914 4.4；django-11039 1.9 | django-10924 selected；django-10914 selected；django-11039 selected | django-10924 selected；django-10914 rejected_invalid；django-11039 selected |
| django-13448 | django-11039 79.7；django-10924 66.4；django-10914 42.0 | django-11039 selected；django-10924 selected；django-10914 selected | django-11039 selected；django-10924 selected；django-10914 rejected_invalid |
| sympy-20154 | sympy-11897 5.7；sympy-11870 4.5；sympy-12171 1.3 | sympy-11897 selected；sympy-11870 selected；sympy-12171 selected | sympy-11897 selected；sympy-11870 selected；sympy-12171 rejected_invalid |
| sympy-24152 | sympy-12171 24.6；sympy-11400 8.6；sympy-11870 5.5；sympy-11897 5.0 | sympy-12171 selected；sympy-11400 selected；sympy-11870 selected；sympy-11897 over_budget | sympy-12171 rejected_invalid；sympy-11400 rejected_invalid；sympy-11870 selected；sympy-11897 selected |
| sympy-20442 | sympy-12171 2.9；sympy-11870 2.0；sympy-11400 1.8；sympy-11897 1.4 | sympy-12171 selected；sympy-11870 selected；sympy-11400 selected；sympy-11897 over_budget | sympy-12171 rejected_invalid；sympy-11870 selected；sympy-11400 rejected_invalid；sympy-11897 selected |
| sympy-18532 | sympy-12171 14.3；sympy-11897 6.9；sympy-11400 2.4 | sympy-12171 selected；sympy-11897 selected；sympy-11400 selected | sympy-12171 rejected_invalid；sympy-11897 selected；sympy-11400 rejected_invalid |
| scikit-learn-25747 | scikit-learn-10949 114.8；scikit-learn-10297 40.9；scikit-learn-11281 35.7；scikit-learn-11040 18.7 | scikit-learn-10949 selected；scikit-learn-10297 selected；scikit-learn-11281 selected；scikit-learn-11040 selected | scikit-learn-10949 selected；scikit-learn-10297 selected；scikit-learn-11281 selected；scikit-learn-11040 rejected_invalid |
| scikit-learn-25500 | scikit-learn-10949 54.1；scikit-learn-10297 39.4；scikit-learn-11281 34.4；scikit-learn-11040 10.8 | scikit-learn-10949 selected；scikit-learn-10297 selected；scikit-learn-11281 selected；scikit-learn-11040 selected | scikit-learn-10949 selected；scikit-learn-10297 selected；scikit-learn-11281 selected；scikit-learn-11040 rejected_invalid |
| scikit-learn-25638 | scikit-learn-10949 55.8；scikit-learn-10297 16.1；scikit-learn-11040 8.3；scikit-learn-11281 4.8 | scikit-learn-10949 selected；scikit-learn-10297 selected；scikit-learn-11040 selected；scikit-learn-11281 selected | scikit-learn-10949 selected；scikit-learn-10297 selected；scikit-learn-11040 rejected_invalid；scikit-learn-11281 selected |
| scikit-learn-25570 | scikit-learn-10949 81.9；scikit-learn-11281 33.2；scikit-learn-10297 32.3；scikit-learn-11040 19.2 | scikit-learn-10949 selected；scikit-learn-11281 selected；scikit-learn-10297 selected；scikit-learn-11040 selected | scikit-learn-10949 selected；scikit-learn-11281 selected；scikit-learn-10297 selected；scikit-learn-11040 rejected_invalid |
| pytest-8365 | pytest-5103 13.3；pytest-5227 13.0；pytest-5221 5.9 | pytest-5103 selected；pytest-5227 selected；pytest-5221 selected | pytest-5103 rejected_invalid；pytest-5227 selected；pytest-5221 selected |
| pytest-7432 | pytest-5103 11.4；pytest-5221 7.2；pytest-5227 4.0 | pytest-5103 selected；pytest-5221 selected；pytest-5227 selected | pytest-5103 rejected_invalid；pytest-5221 selected；pytest-5227 selected |
| pytest-9359 | pytest-5103 72.8；pytest-5221 15.0；pytest-5227 10.5 | pytest-5103 selected；pytest-5221 selected；pytest-5227 selected | pytest-5103 rejected_invalid；pytest-5221 selected；pytest-5227 selected |
| pytest-7220 | pytest-5103 40.8；pytest-5221 18.0；pytest-5227 10.5 | pytest-5103 selected；pytest-5221 selected；pytest-5227 selected | pytest-5103 rejected_invalid；pytest-5221 selected；pytest-5227 selected |
| sphinx-10451 | 无 | no_relevant_memory | no_relevant_memory |
| sphinx-8721 | 无 | no_relevant_memory | no_relevant_memory |
| sphinx-8595 | 无 | no_relevant_memory | no_relevant_memory |
| sphinx-8713 | 无 | no_relevant_memory | no_relevant_memory |

B3 至少注入 1 张卡的目标题：16 / 20。

看完这张表没有改检索或渲染规则。

## 和 CHECKPOINT-2 的 v3 对照

v3 的 B3：django 四题只注入 10914；sympy-20154 无；sympy 其余三题全拒绝；sklearn 四题只注入 11281（relocated）；pytest 四题只注入 5221；sphinx 四题无。

v4 的 B3：django 四题注入 10924 或 11039；sympy-20154 能注入 11897 和 11870；sympy 其余三题至少注入一张；sklearn 四题注入 10949、10297，多数还有 11281，11040 仍被拒绝；pytest 四题拒绝失败尝试 5103，注入 5221 和 5227；sphinx 四题仍然没有记忆。16/20 至少注入一张。
