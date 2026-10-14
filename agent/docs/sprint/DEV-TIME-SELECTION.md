# dev 按时间留一法（v5 final）

可注入的卡必须同仓库、created_at 更早、不是本题，并且是 validated_fix。
检索仍是原来的 BM25，min_score 仍是 1.0。没有改规则。

## django__django-10914

- created_at: 2019-01-30T13:13:20Z
- 可注入：无

## django__django-10924

- created_at: 2019-02-03T11:30:12Z
- 分数：django-10914 5.5
- 实际注入：django-10914

## django__django-11039

- created_at: 2019-03-01T10:24:38Z
- 分数：django-10924 8.0；django-10914 1.1
- 实际注入：django-10924、django-10914

## pytest-dev__pytest-5103

- created_at: 2019-04-13T16:17:45Z
- 可注入：无

## pytest-dev__pytest-5227

- created_at: 2019-05-07T20:27:24Z
- 可注入：无

## scikit-learn__scikit-learn-10297

- created_at: 2017-12-12T22:07:47Z
- 可注入：无

## scikit-learn__scikit-learn-10508

- created_at: 2018-01-19T18:00:29Z
- 分数：scikit-learn-10297 6.4
- 实际注入：scikit-learn-10297

## scikit-learn__scikit-learn-10949

- created_at: 2018-04-10T15:30:56Z
- 分数：scikit-learn-10297 15.8
- 实际注入：scikit-learn-10297

## scikit-learn__scikit-learn-11040

- created_at: 2018-04-28T07:18:33Z
- 分数：scikit-learn-10297 7.5
- 实际注入：scikit-learn-10297

## scikit-learn__scikit-learn-11281

- created_at: 2018-06-15T17:15:25Z
- 分数：scikit-learn-11040 3.7
- 实际注入：scikit-learn-11040

## sympy__sympy-11400

- created_at: 2016-07-15T21:40:49Z
- 可注入：无

## sympy__sympy-11870

- created_at: 2016-11-17T21:36:03Z
- 可注入：无

## sympy__sympy-11897

- created_at: 2016-12-03T14:40:51Z
- 可注入：无

## sympy__sympy-12171

- created_at: 2017-02-13T18:20:56Z
- 可注入：无
