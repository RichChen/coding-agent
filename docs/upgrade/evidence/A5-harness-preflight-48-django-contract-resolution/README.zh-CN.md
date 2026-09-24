# django-13265 合同处置

该题的四个 F2P 是方法级身份。完整模块复跑和四个精确方法复跑结果一致：两个方法复现缺陷并在 baseline 失败，`test_add_model_order_with_respect_to_index_foo_together` 与 `test_supports_functools_partial` 在 baseline 通过，gold 四个全通过。

因此这是可解释、可复核的合同语义结果，不是环境失败，也不是测试选择错误。旧收据保留；本处置不覆盖 `pilot-01`，不改 base commit、test patch、gold patch 或分母，不启动模型调用。
