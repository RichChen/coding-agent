你接手 `D:/crq/src/coding-harness` 的真实 240 pilot 前置工作。先读 `AGENTS.md`、`docs/upgrade/A5-REAL240-HARNESS-CONTRACT.zh-CN.md`，以及合同列出的当前 76-s2 evidence、240 assignments、model/price、source fingerprint、receipt/budget/session 源码。不要直接启动 provider、model、memory build 或 pilot。

先完成可以独立推进的 H0–H2：

1. H0：从 76-s2 的 11 条 `validated-memory-records.jsonl` 生成新的 cold `validated_lightweight` snapshot、manifest、hash 和 public/private boundary audit；保留 4 failed + 5 blocked 引用，不修改旧 evidence。
2. H1：审计并锁定 240 assignments、receipt schema、pilot ledger 和预算。矩阵必须是 20 targets × B0/B1/B2/B3 × repeats 42/43/44 = 240；B0 无 injection，B1–B3 需要真实 injection receipt。没有 target grader、model binding 或 fingerprint 就输出 blocked report。
3. H2：用 zero-model fixture 做 receipt/importer/ledger 的 fail-closed 接线测试，标 `fixture_only=true`、`model_calls=0`、`paid=false`。不要把 fixture 结果写成真实 pilot。

不要在 H0–H2 修改 target 清单、memory record 内容、agent 侧文件、旧证据或 loop/tool policy。允许修改范围仅为本仓新增 snapshot/receipt/ledger CLI、最小相关源码和定向测试；若 CLI 不存在，先实现最小接口并记录新 schema，不能用手改 JSON 或只跑 `py_compile` 代替验收。

H3 依赖 agent 侧完成：B0–B3 实际运行语义、20 target grader readiness、11 条 snapshot 消费 manifest、240 assignment 覆盖和双方 hash。收到这些文件后再做双端 hash/receipt 复核。H4 真实 240 必须等 H3 通过并获得明确 paid pilot authorization；建议 5 波、每波 48 runs，任何一波失败先停，不重放已完成 run。

每阶段交付新目录、输入和输出 hash、schema、artifact manifest、定向测试命令、成功/失败/停止条件和未决项。最终报告必须区分：轻量 memory snapshot 已冻结、pilot 接线已 fixture 验证、真实 240 尚未启动。不要声称 full-repo grader、因果效果或统计显著性已经成立。
