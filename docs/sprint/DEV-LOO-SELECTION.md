# dev 留一法选择（v4 interim）

每道源题只在其余卡片上检索。目标树是 harness receipt 旁的 `staging/original`。
没有改检索规则。`scikit-learn-10508` 还没有卡片。

结论：14 道题都选到了同仓库的其他卡，分数都高于 `min_score=1.0`，没有选到别的仓库，也没有一条都选不到的题。B3 拒绝的是符号不在这道题自己的原始树里，属于依赖检查。这一步不调整检索或 `min_score`。

## django__django-10914

- tree: `D:\crq\src\coding-harness\docs\upgrade\evidence\A5-harness-preflight-62-history-baseline-retry\tasks\django__django-10914\staging\original`
- rank: django-10924 6.9；django-11039 3.8
- B1: selected；django-10924 selected 6.9239 variant_without_gate；django-11039 selected 3.8101 variant_without_gate
- B2: selected；django-10924 selected 6.9239 variant_without_gate；django-11039 selected 3.8101 variant_without_gate
- B3: selected；django-10924 selected 6.9239 file_and_symbols_present；django-11039 selected 3.8101 file_and_symbols_present

## django__django-10924

- tree: `D:\crq\src\coding-harness\docs\upgrade\evidence\A5-harness-preflight-57-remaining16-baseline\tasks\django__django-10924\staging\original`
- rank: django-10914 9.5；django-11039 5.4
- B1: selected；django-10914 selected 9.4888 variant_without_gate；django-11039 selected 5.366 variant_without_gate
- B2: selected；django-10914 selected 9.4888 variant_without_gate；django-11039 selected 5.366 variant_without_gate
- B3: selected；django-10914 rejected_invalid 9.4888 validity_invalid,symbol_missing:test_file_upload_default_permissions;no_symbols:；django-11039 selected 5.366 file_and_symbols_present

## django__django-11039

- tree: `D:\crq\src\coding-harness\docs\upgrade\evidence\A5-harness-preflight-57-remaining16-baseline\tasks\django__django-11039\staging\original`
- rank: django-10924 5.1；django-10914 2.1
- B1: selected；django-10924 selected 5.138 variant_without_gate；django-10914 selected 2.0539 variant_without_gate
- B2: selected；django-10924 selected 5.138 variant_without_gate；django-10914 selected 2.0539 variant_without_gate
- B3: selected；django-10924 selected 5.138 file_and_symbols_present；django-10914 rejected_invalid 2.0539 validity_invalid,symbol_missing:test_file_upload_default_permissions;no_symbols:

## sympy__sympy-11400

- tree: `D:\crq\src\coding-harness\docs\upgrade\evidence\A5-harness-preflight-62-history-baseline-retry\tasks\sympy__sympy-11400\staging\original`
- rank: sympy-11870 7.9；sympy-11897 6.1
- B1: selected；sympy-11870 selected 7.9127 variant_without_gate；sympy-11897 selected 6.1366 variant_without_gate
- B2: selected；sympy-11870 selected 7.9127 variant_without_gate；sympy-11897 selected 6.1366 variant_without_gate
- B3: selected；sympy-11870 selected 7.9127 validity_unknown,no_symbols:sympy/simplify/fu.py;no_symbols:sympy/simplify/trigs；sympy-11897 selected 6.1366 file_and_symbols_present

## sympy__sympy-12171

- tree: `D:\crq\src\coding-harness\docs\upgrade\evidence\A5-harness-preflight-57-remaining16-baseline\tasks\sympy__sympy-12171\staging\original`
- rank: sympy-11400 3.7；sympy-11897 3.6
- B1: selected；sympy-11400 selected 3.7098 variant_without_gate；sympy-11897 selected 3.5869 variant_without_gate
- B2: selected；sympy-11400 selected 3.7098 variant_without_gate；sympy-11897 selected 3.5869 variant_without_gate
- B3: selected；sympy-11400 rejected_invalid 3.7098 validity_invalid,symbol_missing:_print_Xor;symbol_missing:_print_Relational,_pri；sympy-11897 selected 3.5869 file_and_symbols_present

## scikit-learn__scikit-learn-10297

- tree: `D:\crq\src\coding-harness\docs\upgrade\evidence\A5-harness-preflight-62-history-baseline-retry\tasks\scikit-learn__scikit-learn-10297\staging\original`
- rank: scikit-learn-10949 30.9；scikit-learn-11040 11.9；scikit-learn-11281 10.2
- B1: selected；scikit-learn-10949 selected 30.8913 variant_without_gate；scikit-learn-11040 selected 11.9467 variant_without_gate；scikit-learn-11281 over_budget 10.2358 variant_without_gate
- B2: selected；scikit-learn-10949 selected 30.8913 variant_without_gate；scikit-learn-11040 selected 11.9467 variant_without_gate；scikit-learn-11281 selected 10.2358 variant_without_gate
- B3: selected；scikit-learn-10949 selected 30.8913 file_and_symbols_present；scikit-learn-11040 rejected_invalid 11.9467 validity_invalid,symbol_missing:_check_n_neighbors,_check_radius；scikit-learn-11281 rejected_invalid 10.2358 validity_invalid,symbol_missing:fit_predict

## scikit-learn__scikit-learn-10949

- tree: `D:\crq\src\coding-harness\docs\upgrade\evidence\A5-harness-preflight-57-remaining16-baseline\tasks\scikit-learn__scikit-learn-10949\staging\original`
- rank: scikit-learn-10297 36.4；scikit-learn-11040 14.8；scikit-learn-11281 3.5
- B1: selected；scikit-learn-10297 selected 36.4004 variant_without_gate；scikit-learn-11040 selected 14.7787 variant_without_gate；scikit-learn-11281 over_budget 3.5136 variant_without_gate
- B2: selected；scikit-learn-10297 selected 36.4004 variant_without_gate；scikit-learn-11040 selected 14.7787 variant_without_gate；scikit-learn-11281 selected 3.5136 variant_without_gate
- B3: selected；scikit-learn-10297 selected 36.4004 file_and_symbols_present；scikit-learn-11040 rejected_invalid 14.7787 validity_invalid,symbol_missing:_check_n_neighbors,_check_radius；scikit-learn-11281 rejected_invalid 3.5136 validity_invalid,symbol_missing:fit_predict

## scikit-learn__scikit-learn-11040

- tree: `D:\crq\src\coding-harness\docs\upgrade\evidence\A5-harness-preflight-57-remaining16-baseline\tasks\scikit-learn__scikit-learn-11040\staging\original`
- rank: scikit-learn-10297 12.7；scikit-learn-11281 9.0；scikit-learn-10949 8.0
- B1: selected；scikit-learn-10297 selected 12.7058 variant_without_gate；scikit-learn-11281 selected 9.0163 variant_without_gate；scikit-learn-10949 selected 8.0314 variant_without_gate
- B2: selected；scikit-learn-10297 selected 12.7058 variant_without_gate；scikit-learn-11281 selected 9.0163 variant_without_gate；scikit-learn-10949 selected 8.0314 variant_without_gate
- B3: selected；scikit-learn-10297 selected 12.7058 file_and_symbols_present；scikit-learn-11281 rejected_invalid 9.0163 validity_invalid,symbol_missing:fit_predict；scikit-learn-10949 selected 8.0314 file_and_symbols_present

## scikit-learn__scikit-learn-11281

- tree: `D:\crq\src\coding-harness\docs\upgrade\evidence\A5-harness-preflight-57-remaining16-baseline\tasks\scikit-learn__scikit-learn-11281\staging\original`
- rank: scikit-learn-11040 6.1；scikit-learn-10297 1.6；scikit-learn-10949 1.3
- B1: selected；scikit-learn-11040 selected 6.111 variant_without_gate；scikit-learn-10297 selected 1.6484 variant_without_gate；scikit-learn-10949 over_budget 1.2806 variant_without_gate
- B2: selected；scikit-learn-11040 selected 6.111 variant_without_gate；scikit-learn-10297 selected 1.6484 variant_without_gate；scikit-learn-10949 selected 1.2806 variant_without_gate
- B3: selected；scikit-learn-11040 rejected_invalid 6.111 validity_invalid,symbol_missing:_check_n_neighbors,_check_radius；scikit-learn-10297 selected 1.6484 file_and_symbols_present；scikit-learn-10949 selected 1.2806 file_and_symbols_present

## pytest-dev__pytest-5103

- tree: `D:\crq\src\coding-harness\docs\upgrade\evidence\A5-harness-preflight-62-history-baseline-retry\tasks\pytest-dev__pytest-5103\staging\original`
- rank: pytest-5221 5.0；pytest-5227 4.7
- B1: selected；pytest-5221 selected 5.031 variant_without_gate；pytest-5227 selected 4.7234 variant_without_gate
- B2: selected；pytest-5221 selected 5.031 variant_without_gate；pytest-5227 selected 4.7234 variant_without_gate
- B3: selected；pytest-5221 selected 5.031 validity_unknown,no_symbols:src/_pytest/python.py；pytest-5227 selected 4.7234 validity_unknown,no_symbols:src/_pytest/logging.py

## pytest-dev__pytest-5221

- tree: `D:\crq\src\coding-harness\docs\upgrade\evidence\A5-harness-preflight-57-remaining16-baseline\tasks\pytest-dev__pytest-5221\staging\original`
- rank: pytest-5227 4.5；pytest-5103 2.3
- B1: selected；pytest-5227 selected 4.5312 variant_without_gate；pytest-5103 selected 2.2845 variant_without_gate
- B2: selected；pytest-5227 selected 4.5312 variant_without_gate；pytest-5103 selected 2.2845 variant_without_gate
- B3: selected；pytest-5227 selected 4.5312 validity_unknown,no_symbols:src/_pytest/logging.py；pytest-5103 selected 2.2845 file_and_symbols_present

## sympy__sympy-11870

- tree: `D:\crq\src\coding-harness\docs\upgrade\evidence\A5-harness-preflight-57-remaining16-baseline\tasks\sympy__sympy-11870\staging\original`
- rank: sympy-11897 5.6；sympy-11400 3.9
- B1: selected；sympy-11897 selected 5.5862 variant_without_gate；sympy-11400 selected 3.8881 variant_without_gate
- B2: selected；sympy-11897 selected 5.5862 variant_without_gate；sympy-11400 selected 3.8881 variant_without_gate
- B3: selected；sympy-11897 selected 5.5862 file_and_symbols_present；sympy-11400 rejected_invalid 3.8881 validity_invalid,symbol_missing:_print_Xor;symbol_missing:_print_Relational,_pri

## sympy__sympy-11897

- tree: `D:\crq\src\coding-harness\docs\upgrade\evidence\A5-harness-preflight-57-remaining16-baseline\tasks\sympy__sympy-11897\staging\original`
- rank: sympy-11400 10.4；sympy-12171 4.3；sympy-11870 3.6
- B1: selected；sympy-11400 selected 10.3796 variant_without_gate；sympy-12171 selected 4.2746 variant_without_gate；sympy-11870 selected 3.5527 variant_without_gate
- B2: selected；sympy-11400 selected 10.3796 variant_without_gate；sympy-12171 selected 4.2746 variant_without_gate；sympy-11870 selected 3.5527 variant_without_gate
- B3: selected；sympy-11400 rejected_invalid 10.3796 validity_invalid,symbol_missing:_print_Xor;symbol_missing:_print_Relational,_pri；sympy-12171 rejected_invalid 4.2746 validity_invalid,symbol_missing:_print_Derivative,_print_Float,test_Derivative;s；sympy-11870 selected 3.5527 validity_unknown,no_symbols:sympy/simplify/fu.py;no_symbols:sympy/simplify/trigs

## pytest-dev__pytest-5227

- tree: `D:\crq\src\coding-harness\docs\upgrade\evidence\A5-harness-preflight-57-remaining16-baseline\tasks\pytest-dev__pytest-5227\staging\original`
- rank: pytest-5221 5.1；pytest-5103 3.3
- B1: selected；pytest-5221 selected 5.085 variant_without_gate；pytest-5103 selected 3.3336 variant_without_gate
- B2: selected；pytest-5221 selected 5.085 variant_without_gate；pytest-5103 selected 3.3336 variant_without_gate
- B3: selected；pytest-5221 selected 5.085 validity_unknown,no_symbols:src/_pytest/python.py；pytest-5103 selected 3.3336 file_and_symbols_present
