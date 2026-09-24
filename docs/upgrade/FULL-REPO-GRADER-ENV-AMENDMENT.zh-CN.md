# 整仓 grader 环境修订记录

2026-09-21，`validation-01` 完成后、`attempt-02` 构建前。原合同评测集合、目标缺陷、允许修改路径、判分和资源边界不变；这是用户授权的环境准备正确性修复，非模型实验调参。

首轮484项收集成功，base与known-good均473通过、9失败、2正常skip。目标base失败为缺text参数，known-good失败为缺测试资源`tests/static/config.toml`；其余8项失败均涉及Werkzeug2.3.7的cookie/session接口或附加弃用warning。全部结果和首镜像保留，未声明ready。

新attempt复用同一完整归档字节和公开base hash：

1. 完整对比本地fixture tests与上游base tests，复制所有不同的测试补丁文件（严格断言为`tests/test_config.py`、`tests/static/config.toml`），不能只复制.py丢弃资源。这个资源此前已在已验证fixture中，不是根据候选结果新写的测试或预期值。
2. Werkzeug固定为2.2.2，符合该base声明的依赖下限、保留旧cookie_jar接口；其余精确依赖和Python3.11不变。全套tests继续运行，不修改测试以兼容新接口。

该修订影响新环境digest和private overlay hash，不改变源代码base。新的收集身份必须与首轮484项逐项相同；若不一致必须报告，不静默接受。已知修复只作私有校准，禁止进入agent侧。
