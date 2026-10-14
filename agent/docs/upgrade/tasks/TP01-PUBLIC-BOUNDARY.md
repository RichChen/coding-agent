# TP01 — PublicTask / EvaluationSpec 与数据隔离

执行更新：2026-09-19 已由本任务实施并离线验证，具体证据/限制见 [实施记录](../IMPLEMENTED-TP01-04.md)。下文保留原任务包说明。

状态：待用户启动；实施者可为本 Codex 任务或 Cursor Agent，验收一致。版本 v0.1，2026-09-18。

## 可直接转交的执行说明

在 `D:\crq\src\coding-agent` 先读 `docs/upgrade/IMPLEMENTATION-PLAN.md` 第 2/4 节、共享契约和本包，重新查项目指令/文件 hash。只实施 TP01，不顺手改 runtime、不跑付费模型、不下载 benchmark、不提交推送。存在用户新改动时保留并重新核对。本包目标是形成可审计的公开输入边界和离线装配验证，不能宣称实现了 OS 沙箱。

## 动机、范围与前置

当前 `reposkill_agent/core/contracts.py:11 TaskSpec`、`eval/task_spec.py:25 load_tasks`、`agents/contracts.py AgentContext` 混合公开/答案字段；`eval/graph_runner.py:391 _prepare_workspace` 整体复制；`llm/prompts.py:97 build_user_prompt` 直接放 expected_files。前置仅 A0 和实施前 allowlist 基线快照，不依赖另仓安装或真实模型。

允许新增 `reposkill_agent/protocol/`（public DTO、private eval DTO、serialization/validation）、`reposkill_agent/eval/public_export.py`（私有数据准备入口）、`tests/test_public_boundary.py` 和 `tests/fixtures/upgrade/public_boundary/`。旧 `TaskSpec` 保持 API/行为；若增加 mode 标记，集中改契约/加载入口与测试，不全面改 GraphRunner。本包不接入 LLM、router、memory，也不实现工具执行器/隐藏测试 runner。TP02 后再由 A1 集成步骤接新路径，不能把清空 expected_files 的旧 GraphRunner 当成 realistic runner。

## 输入输出与固定边界

- 输入（私有准备侧）：来源已审查的任务目录、公开 issue/context allowlist、固定 revision/hash、私有 EvaluationSpec、导出文件 manifest。
- 输出（agent）：版本化 PublicTask，对应共享 TaskEnvelope；`task_id, task_family, issue_text, repo_ref, public_context, workspace_id, allowed_tools, execution_profile_ref, budget, protocol_mode, seed, repeat_id`。budget 是宿主配置描述，不在此执行资源调度。
- 输出（私有）：EvaluationSpec 独立文件/对象，oracle metadata 和隐藏测试引用只在此；公开 export 清单与 audit 记录不含秘密原文。
- 内部样例（字段子集，非已实现 API）：`{"schema_version":"1.0","task_id":"opaque-01","task_family":"code_repair","issue_text":"调用 parse_config 失败","repo_ref":{"snapshot_hash":"<verified-sha256>"},"protocol_mode":"realistic"}`。完整 fixture 必须补齐其余 required 字段，禁止用该子集冒充完整验证样例。
- 错误：`oracle_field_present`、`unsafe_export_path`、`unsupported_schema_major`、`missing_repo_revision`；日志记录字段路径/hash，不把 gold 值回传。旧 diagnostic 走现有 TaskSpec 或单独 OracleContext，公共 TaskEnvelope 即便 diagnostic 也不添加 gold 字段。

## 行为验收（6 条）

1. 在 gold、expected_files、tags、嵌套 metadata、private filenames、未来轨迹放唯一 sentinel：公共序列化/export listing/index input/audit 公共投影均无泄漏；污染 realistic payload 被拒绝。不要只检查 prompt 字符串。
2. 固定公开输入，替换私有 metadata，不改变公共 export/hash（私有侧 audit 可变化）；公开 issue 本来出现的文件名正常保留。
3. 只导出 allowlist 文件，private 树、`.env`、链接/越界路径不能进入导出；输出不能覆盖输入或用户工作目录。更强 shell/OS 隔离留宿主 capability 测试，报告明确未验证。
4. 公私类型互不嵌套，插件测试拿不到 EvaluationSpec 引用；task ID 作为不透明键，family 不接受 benchmark 答案类别。诊断数据不可被无标签隐式升级为 realistic。
5. 未知 major 拒绝；已知 minor 新 optional wire 字段可兼容但不自动注入策略，禁止字段仍拒绝。新路径无模式时默认 realistic；旧入口明确标 legacy diagnostic，旧离线行为不变。
6. 两种 mode 的报告/fixture 分开，拼接汇总明确报错或分层展示，禁止一个平均值；不新建实际 paid run。

## 检查命令与产物

已运行并通过的当前回归基线（准确环境/命令见 `../VERIFICATION.md`）：完整 44 项 `pytest` 命令包含 `tests/test_contracts.py tests/test_planner.py`；`ruff check reposkill_agent tests scripts --no-cache`；`python -m reposkill_agent --help`（均使用明确的 Conda 解释器）。这些证明已有入口可用，不证明新功能通过。

新增后执行（尚无这些文件，不能标已通过）：

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PATH='C:\Users\Administrator\.conda\envs\coding-harness;C:\Users\Administrator\.conda\envs\coding-harness\Scripts;' + $env:PATH
& 'C:\Users\Administrator\.conda\envs\coding-harness\python.exe' -m pytest tests/test_public_boundary.py tests/test_contracts.py -q -o addopts='' -p no:cacheprovider
```

这条拟用命令不带固定 basetemp，避免复用清空本轮临时目录；实施时可改用新唯一绝对临时目录并记录。交付：代码/测试 fixture、public/private schema 文档、字段流向图、manifest/hash、逐项验收日志、before/after diff、未支持项。不要交真实 oracle 内容或 keys 到公开产物。

## 风险与退出条件

仅删除 prompt 字段无法解决 shell/索引/记忆泄漏；现有测试 command 可能本身指向 holdout 私有文件，不能自动当公开复现步骤。无法判定公开性的输入先拒绝，不临时猜测。发现需要改共享字段语义，写本仓 CONTRACT-CHANGE 补充而非改对方仓库；完成本包可测试边界后列联调阻塞。没有可用 Git 时交限定快照/diff，不 init 父目录。
