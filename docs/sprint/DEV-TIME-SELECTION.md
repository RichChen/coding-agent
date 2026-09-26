# dev 按时间留一法（v5 interim）

可注入的卡必须同仓库、created_at 更早、不是本题，并且是 validated_fix。
检索仍是原来的 BM25，min_score 仍是 1.0。没有改规则。

## django__django-10914

- created_at: 2019-01-30T21:13:20+08:00
- 可注入：无

## django__django-10924

- created_at: 2019-02-03T19:30:12+08:00
- 分数：django-10914 5.5
- 实际注入：django-10914

## django__django-11039

- created_at: 2019-03-01T18:24:38+08:00
- 分数：django-10924 8.0；django-10914 1.1
- 实际注入：django-10924、django-10914

## pytest-dev__pytest-5103

- created_at: 2019-04-14T00:17:45+08:00
- 可注入：无

## pytest-dev__pytest-5227

- created_at: 2019-05-08T04:27:24+08:00
- 可注入：无

## scikit-learn__scikit-learn-10297

- created_at: 2017-12-13T06:07:47+08:00
- 可注入：无

## scikit-learn__scikit-learn-10508

- created_at: 2018-01-20T02:00:29+08:00
- 分数：scikit-learn-10297 6.4
- 实际注入：scikit-learn-10297

## scikit-learn__scikit-learn-10949

- created_at: 2018-04-10T23:30:56+08:00
- 分数：scikit-learn-10297 15.8
- 实际注入：scikit-learn-10297

## scikit-learn__scikit-learn-11040

- created_at: 2018-04-28T15:18:33+08:00
- 分数：scikit-learn-10297 7.5
- 实际注入：scikit-learn-10297

## scikit-learn__scikit-learn-11281

- created_at: 2018-06-16T01:15:25+08:00
- 分数：scikit-learn-11040 3.7
- 实际注入：scikit-learn-11040

## sympy__sympy-11400

- created_at: 2016-07-16T05:40:49+08:00
- 可注入：无

## sympy__sympy-11870

- created_at: 2016-11-18T05:36:03+08:00
- 可注入：无

## sympy__sympy-11897

- created_at: 2016-12-03T22:40:51+08:00
- 可注入：无

## sympy__sympy-12171

- created_at: 2017-02-14T02:20:56+08:00
- 可注入：无
