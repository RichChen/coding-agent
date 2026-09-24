# H5 跨仓联调证据

完整说明见 [H5-INTEROP.zh-CN.md](../../H5-INTEROP.zh-CN.md)。

- `offline-01/`：不开模型的真实外部 adapter 离线 preflight，off/on 输出与 coding-agent 交接 fixture 一致。
- `offline-02/`：dispatcher 接线后的离线 preflight；配置固定为 `read_search`，未产生付费调用。
- `real-01/`：历史真实 DeepSeek Flash + Docker 两个 fresh run；off/on 各 4 次调用，私有 grader 均 4/4，dispatcher 尚未启用。
- `real-02/`：尝试启用 dispatcher 的预检目录；因当前执行沙箱无法访问 Docker named pipe，baseline 标记为 `invalid_env`，不能作为联调通过证据。
- `real-03/`：full-host off/on 执行已完成；旧验证脚本在读取 journal 前检查 receipt，留下完整运行证据但未生成最终摘要。
- `real-04/`：修正验证顺序后的 full-host dispatcher 联调；off/on 均 4/4，on 变体 receipt、journal、replay 和 key/canary 检查全部通过。
- `regression-final.xml`：联调代码后的最终全量回归，325 passed、6 skipped、0 failed。
- `regression-h3/`、`regression-h4/`：全量回归生成的独立 H3/H4 过程证据。

`real-01/` 保留 dispatcher 尚未启用时的历史证据；`real-02/invalid_env` 不计入成功联调。当前有效的 dispatcher 证据以 `real-04/` 为准；R1 总体收口见 [R1 收口记录](../../R1-CLOSEOUT.zh-CN.md)。
