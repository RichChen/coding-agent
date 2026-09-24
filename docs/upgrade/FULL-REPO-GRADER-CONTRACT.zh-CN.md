# 整仓 pytest grader 与环境预检合同 v1

2026-09-21。用户授权本仓开展整仓grader和环境预检；另一侧负责正式pilot准备。本轮不调用模型、不启动正式pilot、不改loop/factory/context/schema、旧grader或旧证据。新增独立接口与CLI、测试、固定环境及新证据目录。参考项目指定路径本机不存在，沿用现有Docker执行边界。

## 目标与范围

把固定Python函数探针扩展为完整仓库候选上的固定pytest评测：以公开base字节快照＋候选允许修改构建新容器，grader测试仅在agent结束后注入。收集与结果必须来自冻结runner，测试身份和全分母由宿主冻结；零测试、少测、测试/配置变更、stdout假通过、无结果、依赖/收集失败、超时或清理失败均不能pass。不得把agent自报或exit=0直接当通过。

首个真实环境锚点为Flask SWE-bench实例 `pallets__flask-4992`，base `4c288bc97ea371817199908d0d9b12de9dae327e`，Python3.11。现有本地fixture经过裁剪（缺docs/examples等）且包含test patch，因此只作来源/测试补丁校验，不能称完整上游仓库。从固定commit归档获取完整树，保留归档hash和内容清单；禁止向agent公开 `.oracle`、gold或私有测试。已有fixture里的已知修复只在grader环境校准阶段作为私有阳性对照，不作为模型输入或正式pilot成绩。

盘点现有12个SWE-bench fixture的文件/字节规模、指定Python和依赖，以及现有8MiB/2048文件传输边界。超限或未配置的环境如实标记，不静默裁剪代码、不宿主降级、不把Flask环境套用于Requests/SymPy。首轮只承诺一个完整仓库的端到端环境验收和其余任务readiness清单，不宣称12个任务环境全可用。

## 执行/环境

基于固定digest的Python3.11 Linux镜像，单独预装精确依赖和固定pytest版本；记录构建Dockerfile、镜像ID/digest、pip freeze、Python版本。构建阶段可联网取公开归档/依赖；执行/收集/验证均network=none、无宿主挂载、非root、cap-drop ALL、只读rootfs、CPU/memory/pids/tmpfs限额，沿用已有Docker backend。项目安装在镜像构建时仅使用可信base；执行时必须从/workspace候选代码加载，不得误测镜像里的base副本。记录导入路径验证。

固定runner先导入镜像pytest再加入受控项目导入路径，禁用第三方pytest自动插件及环境PYTEST_ADDOPTS，固定独立config、测试路径、资源/时间上限（收集120秒、执行300秒），允许仓库已有且冻结的conftest。验证侧测试覆盖来自已存fixture的test patch文件，hash冻结。host receipt包含所有nodeid、setup/call/teardown、exit、collection errors；另留原始stdout/stderr，不解析“passed”关键词作为判据。无receipt或不完整退出单列失败/invalid_env，所有assigned保留。

这是对普通修复候选、测试/config篡改、运行失败的可靠性边界，不是对恶意Python程序的形式化防作弊隔离：候选与pytest在同一Python进程，可能主动篡改解释器/插件。不得声称自定义report或JUnit是不可伪造证明。该限制需在交接文档显式标注；高对抗场景仍需独立进程黑盒协议等更强边界。

## 预检、冻结与验收

1. 静态验证快照路径、权限、大小、base hash、私有测试与可编辑路径不交叉。候选只能改变预授权源码文件，新增/删除测试、配置、conftest、sitecustomize、runner等拒绝。首任务可编辑范围固定 `src/flask/config.py`。
2. 环境探针检查Python/pytest及关键依赖、候选包导入路径、Docker约束、全树传输。先用可信base+测试overlay收集全套tests；非空且唯一nodeid才冻结完整测试集合。该冻结在候选评分之前进行，不按候选结果筛测试。
3. 基线执行全套冻结tests，必须复现 `tests/test_config.py::test_config_from_file_toml` 缺陷。所有基线通过项成为回归集合；已有skip/xfail逐项保留，不计pass，且在spec中显式允许相同状态。其他基线失败完整列出，不以环境修复之名删去。
4. 私有已知修复阳性校准必须使目标缺陷转pass并保持全部基线通过项。若全套存在无关失败，报告partial及具体环境原因，不能将整仓绿色偷换成选取子集绿色；判定正式pilot readiness前修复环境并另记attempt。
5. 阴性验收：测试删除/篡改、伪造pytest入口/配置、新增绕过hook、零/少收集、跳过必测项、stdout假通过+exit0、缺依赖、超时/清理失败不能成功。离线单元验证计数/身份/报告再生；真实Docker至少验证base、known-good、篡改、假通过、缺依赖及超时。

成功意味着完整树、固定环境、独立收集/评分和错误拒绝链路可供正式pilot接线，不是agent修复成功率。新CLI接受任务spec、base/candidate快照和新输出目录，离线report重生成校验hash。私有数据留在独立目录，公开handoff仅含公开task/seed、镜像标识及接口说明，不含结果驱动修复提示。候选必须由调用方在agent停止和清理后冻结；新入口不自动回灌private结果到agent。

## 证据与并行工作

固定合同、源码/runner/input/image/test hashes、全assigned manifest、collection、baseline、阳性/阴性结果、清理状态、环境失败、日志和独立报告；每次尝试新目录，不覆盖旧失败。只新增grader相关模块，既有摘要/agent修改保留。新src文件会使全仓source fingerprint改变；正式pilot必须在两边改动稳定后重新冻结自身指纹，不能复用旧运行恢复。这是协作交接约束，不自动修改另一边配置或发送消息。
