# dev 留一法选择（v4 final）

每道源题只在其余卡片上检索。目标树是 harness receipt 旁的 `staging/original`。
B2 只注入 `validated_fix`。没有改检索规则。`pytest-5221` 不在这批卡里。失败卡被 B2 滤掉之后，有的题会变成 `no_relevant_memory`。这是过滤结果，不是调分。

## django__django-10914

- tree: `D:\crq\src\coding-harness\docs\upgrade\evidence\A5-harness-preflight-62-history-baseline-retry\tasks\django__django-10914\staging\original`
- rank: django-10924 5.1；django-11039 4.0
- B1: selected；django-10924 selected 5.0921 variant_without_gate；django-11039 selected 4.0125 variant_without_gate
- B2: selected；django-10924 selected 5.0921 variant_without_gate；django-11039 selected 4.0125 variant_without_gate
- B3: selected；django-10924 selected 5.0921 file_and_symbols_present；django-11039 rejected_invalid 4.0125 validity_invalid,symbol_missing:MigrateTests,test_sqlmigrate_for_non_transaction

## django__django-10924

- tree: `D:\crq\src\coding-harness\docs\upgrade\evidence\A5-harness-preflight-57-remaining16-baseline\tasks\django__django-10924\staging\original`
- rank: django-10914 10.2；django-11039 4.6
- B1: selected；django-10914 selected 10.1742 variant_without_gate；django-11039 selected 4.6243 variant_without_gate
- B2: selected；django-10914 selected 10.1742 variant_without_gate；django-11039 selected 4.6243 variant_without_gate
- B3: selected；django-10914 selected 10.1742 validity_unknown,no_symbols:django/conf/global_settings.py;no_symbols:docs/ref/s；django-11039 rejected_invalid 4.6243 validity_invalid,symbol_missing:MigrateTests,test_sqlmigrate_for_non_transaction

## django__django-11039

- tree: `D:\crq\src\coding-harness\docs\upgrade\evidence\A5-harness-preflight-57-remaining16-baseline\tasks\django__django-11039\staging\original`
- rank: django-10924 8.0；django-10914 1.1
- B1: selected；django-10924 selected 7.9654 variant_without_gate；django-10914 selected 1.1233 variant_without_gate
- B2: selected；django-10924 selected 7.9654 variant_without_gate；django-10914 selected 1.1233 variant_without_gate
- B3: selected；django-10924 selected 7.9654 file_and_symbols_present；django-10914 selected 1.1233 validity_unknown,no_symbols:django/conf/global_settings.py;no_symbols:docs/ref/s

## sympy__sympy-11400

- tree: `D:\crq\src\coding-harness\docs\upgrade\evidence\A5-harness-preflight-62-history-baseline-retry\tasks\sympy__sympy-11400\staging\original`
- rank: sympy-11870 9.1；sympy-11897 6.4
- B1: selected；sympy-11870 selected 9.0969 variant_without_gate；sympy-11897 selected 6.3878 variant_without_gate
- B2: no_relevant_memory
- B3: selected；sympy-11870 rejected_invalid 9.0969 validity_invalid,symbol_missing:_exptrig；sympy-11897 selected 6.3878 validity_unknown,no_dependencies

## sympy__sympy-12171

- tree: `D:\crq\src\coding-harness\docs\upgrade\evidence\A5-harness-preflight-57-remaining16-baseline\tasks\sympy__sympy-12171\staging\original`
- rank: sympy-11897 3.8；sympy-11400 2.3
- B1: selected；sympy-11897 selected 3.8208 variant_without_gate；sympy-11400 selected 2.3353 variant_without_gate
- B2: no_relevant_memory
- B3: selected；sympy-11897 selected 3.8208 validity_unknown,no_dependencies；sympy-11400 rejected_invalid 2.3353 validity_invalid,symbol_missing:test_ccode_sinc;symbol_missing:_print_sinc

## scikit-learn__scikit-learn-10297

- tree: `D:\crq\src\coding-harness\docs\upgrade\evidence\A5-harness-preflight-62-history-baseline-retry\tasks\scikit-learn__scikit-learn-10297\staging\original`
- rank: scikit-learn-10949 37.0；scikit-learn-11040 14.4；scikit-learn-11281 10.1；scikit-learn-10508 9.1
- B1: selected；scikit-learn-10949 selected 37.0289 variant_without_gate；scikit-learn-11040 selected 14.4258 variant_without_gate；scikit-learn-11281 selected 10.1239 variant_without_gate；scikit-learn-10508 selected 9.1375 variant_without_gate
- B2: selected；scikit-learn-11040 selected 11.8037 variant_without_gate；scikit-learn-11281 selected 6.5211 variant_without_gate
- B3: selected；scikit-learn-10949 selected 37.0289 file_and_symbols_present；scikit-learn-11040 selected 14.4258 file_and_symbols_present；scikit-learn-11281 rejected_invalid 10.1239 validity_invalid,symbol_missing:BayesianGaussianMixture,GaussianMixture,fit_pred；scikit-learn-10508 selected 9.1375 file_and_symbols_present

## scikit-learn__scikit-learn-10949

- tree: `D:\crq\src\coding-harness\docs\upgrade\evidence\A5-harness-preflight-57-remaining16-baseline\tasks\scikit-learn__scikit-learn-10949\staging\original`
- rank: scikit-learn-10297 45.1；scikit-learn-10508 26.4；scikit-learn-11040 15.9；scikit-learn-11281 1.9
- B1: selected；scikit-learn-10297 selected 45.1357 variant_without_gate；scikit-learn-10508 selected 26.3619 variant_without_gate；scikit-learn-11040 selected 15.8961 variant_without_gate；scikit-learn-11281 selected 1.8907 variant_without_gate
- B2: selected；scikit-learn-10297 selected 38.4758 variant_without_gate；scikit-learn-11040 selected 14.601 variant_without_gate；scikit-learn-11281 selected 2.5043 variant_without_gate
- B3: selected；scikit-learn-10297 selected 45.1357 file_and_symbols_present；scikit-learn-10508 selected 26.3619 file_and_symbols_present；scikit-learn-11040 selected 15.8961 file_and_symbols_present；scikit-learn-11281 rejected_invalid 1.8907 validity_invalid,symbol_missing:BayesianGaussianMixture,GaussianMixture,fit_pred

## scikit-learn__scikit-learn-11040

- tree: `D:\crq\src\coding-harness\docs\upgrade\evidence\A5-harness-preflight-57-remaining16-baseline\tasks\scikit-learn__scikit-learn-11040\staging\original`
- rank: scikit-learn-10297 12.7；scikit-learn-11281 11.4；scikit-learn-10949 8.5；scikit-learn-10508 8.0
- B1: selected；scikit-learn-10297 selected 12.6669 variant_without_gate；scikit-learn-11281 selected 11.4111 variant_without_gate；scikit-learn-10949 selected 8.5158 variant_without_gate；scikit-learn-10508 selected 8.0454 variant_without_gate
- B2: selected；scikit-learn-10297 selected 11.4666 variant_without_gate；scikit-learn-11281 selected 8.3231 variant_without_gate
- B3: selected；scikit-learn-10297 selected 12.6669 file_and_symbols_present；scikit-learn-11281 rejected_invalid 11.4111 validity_invalid,symbol_missing:BayesianGaussianMixture,GaussianMixture,fit_pred；scikit-learn-10949 selected 8.5158 file_and_symbols_present；scikit-learn-10508 selected 8.0454 file_and_symbols_present

## scikit-learn__scikit-learn-11281

- tree: `D:\crq\src\coding-harness\docs\upgrade\evidence\A5-harness-preflight-57-remaining16-baseline\tasks\scikit-learn__scikit-learn-11281\staging\original`
- rank: scikit-learn-11040 7.2；scikit-learn-10508 2.7；scikit-learn-10297 2.3
- B1: selected；scikit-learn-11040 selected 7.2091 variant_without_gate；scikit-learn-10508 selected 2.6503 variant_without_gate；scikit-learn-10297 selected 2.27 variant_without_gate
- B2: selected；scikit-learn-11040 selected 3.7368 variant_without_gate
- B3: selected；scikit-learn-11040 selected 7.2091 file_and_symbols_present；scikit-learn-10508 selected 2.6503 file_and_symbols_present；scikit-learn-10297 selected 2.27 file_and_symbols_present

## pytest-dev__pytest-5103

- tree: `D:\crq\src\coding-harness\docs\upgrade\evidence\A5-harness-preflight-62-history-baseline-retry\tasks\pytest-dev__pytest-5103\staging\original`
- rank: pytest-5227 3.5
- B1: selected；pytest-5227 selected 3.5241 variant_without_gate
- B2: selected；pytest-5227 selected 3.5241 variant_without_gate
- B3: rejected_invalid；pytest-5227 rejected_invalid 3.5241 validity_invalid,symbol_missing:test_log_cli_default_level,test_log_cli_level,te

## sympy__sympy-11870

- tree: `D:\crq\src\coding-harness\docs\upgrade\evidence\A5-harness-preflight-57-remaining16-baseline\tasks\sympy__sympy-11870\staging\original`
- rank: sympy-11897 5.3；sympy-11400 4.2
- B1: selected；sympy-11897 selected 5.2994 variant_without_gate；sympy-11400 selected 4.2267 variant_without_gate
- B2: no_relevant_memory
- B3: selected；sympy-11897 selected 5.2994 validity_unknown,no_dependencies；sympy-11400 rejected_invalid 4.2267 validity_invalid,symbol_missing:test_ccode_sinc;symbol_missing:_print_sinc

## sympy__sympy-11897

- tree: `D:\crq\src\coding-harness\docs\upgrade\evidence\A5-harness-preflight-57-remaining16-baseline\tasks\sympy__sympy-11897\staging\original`
- rank: sympy-11400 10.8；sympy-12171 4.2；sympy-11870 3.5
- B1: selected；sympy-11400 selected 10.828 variant_without_gate；sympy-12171 selected 4.1699 variant_without_gate；sympy-11870 selected 3.4978 variant_without_gate
- B2: no_relevant_memory
- B3: rejected_invalid；sympy-11400 rejected_invalid 10.828 validity_invalid,symbol_missing:test_ccode_sinc;symbol_missing:_print_sinc；sympy-12171 rejected_invalid 4.1699 validity_invalid,symbol_missing:_print_Derivative,_print_Float；sympy-11870 rejected_invalid 3.4978 validity_invalid,symbol_missing:_exptrig

## pytest-dev__pytest-5227

- tree: `D:\crq\src\coding-harness\docs\upgrade\evidence\A5-harness-preflight-57-remaining16-baseline\tasks\pytest-dev__pytest-5227\staging\original`
- rank: pytest-5103 1.9
- B1: selected；pytest-5103 selected 1.8751 variant_without_gate
- B2: no_relevant_memory
- B3: rejected_invalid；pytest-5103 rejected_invalid 1.8751 validity_invalid,symbol_missing:_visit_all_any

## scikit-learn__scikit-learn-10508

- tree: `D:\crq\src\coding-harness\docs\upgrade\evidence\A5-harness-preflight-57-remaining16-baseline\tasks\scikit-learn__scikit-learn-10508\staging\original`
- rank: scikit-learn-10949 29.5；scikit-learn-11040 13.6；scikit-learn-10297 10.7；scikit-learn-11281 10.4
- B1: selected；scikit-learn-10949 selected 29.4997 variant_without_gate；scikit-learn-11040 selected 13.6193 variant_without_gate；scikit-learn-10297 selected 10.7287 variant_without_gate；scikit-learn-11281 selected 10.4448 variant_without_gate
- B2: selected；scikit-learn-10297 selected 12.4579 variant_without_gate；scikit-learn-11040 selected 10.9374 variant_without_gate；scikit-learn-11281 selected 9.2058 variant_without_gate
- B3: selected；scikit-learn-10949 selected 29.4997 file_and_symbols_present；scikit-learn-11040 selected 13.6193 file_and_symbols_present；scikit-learn-10297 selected 10.7287 file_and_symbols_present；scikit-learn-11281 rejected_invalid 10.4448 validity_invalid,symbol_missing:BayesianGaussianMixture,GaussianMixture,fit_pred
