# 整仓 grader 与环境预检交接

2026-09-21。当前 `pallets__flask-4992` 的完整仓库环境已 ready，可供正式 pilot 接线。新接口独立于现有函数探针 grader；没有修改另一侧的 pilot 配置、没有调用模型、没有启动正式 pilot。此处已知修复仅作私有 grader 校准，不能计入 agent 成功率。

## 已验证结果

完整上游 commit `4c288bc97ea371817199908d0d9b12de9dae327e`，250 文件、1,577,776 字节，保留 docs、examples、CI 等全部归档内容。不是原有裁剪 fixture。

| 验收项 | 结果 |
| --- | --- |
| 完整 tests 收集 | 484 个唯一 nodeid，与首轮顺序和身份完全相同 |
| 原始 base | 481 passed、1 failed、2 skipped；唯一失败为目标 TOML 配置缺陷 |
| 私有 known-good | 482 passed、0 failed、2 skipped；全部 481 项基线回归保留 |
| 阴性对照 | 篡改测试、伪造 pytest、stdout 假通过、缺依赖、超时，5/5 正确拒绝 |
| 隔离与清理 | 无网络/宿主挂载、非 root、只读 rootfs、资源限额；创建的容器均清理 |
| 独立 CLI | 已知修复 pass；缺失候选 invalid_env，仍保留 1 个任务/484 项分母 |
| 离线审计 | 22 项证据核验通过，报告重生成字节一致 |
| 针对性测试 | 56 passed，含旧 grader、输入合同、执行限额回归 |

两项 skip 为原仓 `TestGreenletContextCopying` 测试。上游 `requirements/tests.in` 在 Python >=3.11 不安装 greenlet；逐项冻结允许 skip，不计通过。首个 baseline 使用尚未允许 skip 的 initial spec，JSON 的 `failed=3` 意为 3 个“尚未满足判分要求”的项（1 真失败+2 skip），不是 3 个 pytest failed；真实状态看 receipt 和 cases。最终 spec 的必测项为 482。

## 正式 pilot 应使用的输入

证据根目录：`docs/upgrade/evidence/full-repo-grader/`。

公开交接清单：`audit-01/public-handoff.json`。agent 侧仅使用：

- `attempt-02/public/base.json`：`{仓库相对 POSIX 路径: base64 文件字节}`，解码函数 `src.eval.grader.decode_snapshot`。
- `attempt-02/public/task.json`：公开问题描述及允许修改路径。它是交接数据，需要调用方转换为自己的 TaskSpec，不是现有 runner 配置文件。
- 清单中的固定镜像。执行环境为本机 Docker `desktop-linux`，该本地镜像没有推送到 registry；其他机器须另行分发并核验，不能假设可远程 pull。

只允许修改 `src/flask/config.py`。不能把旧 fixture（含 test patch、.oracle、SETUP 元数据）当公开 base；不能把 evidence 根目录整体挂载或复制进 agent 容器。

固定镜像：

```text
coding-harness-flask4992-grader@sha256:2a19ad90214fcaf08388547c0a37deb209996c263a2358466da8aa4fa497f4e0
```

Python 3.11.16、pytest 7.2.1、Werkzeug 2.2.2。全部精确依赖在 `attempt-02/build/requirements.lock`；实测包版本、pip freeze、导入路径、镜像 ID、资源与清理证据在 `validation-04/*.json`。依赖在可信 base 上预安装，执行时 `/workspace` 候选覆盖同路径；已验证 Flask 从候选 `/workspace/src/flask/__init__.py` 加载。

## agent 停止后的私有评分接口

先停止 agent 和所有工具活动，完成候选快照并确认执行侧清理，再启动独立 grader。若通过容器 close 导出，须使用现有 backend 的受控快照生命周期；清理失败或缺失快照不得补成通过。此模块不自动接管 agent 的停止/导出，也不把私有结果回灌 agent。

`src.eval.repo_grader.RepositoryGrader.evaluate(base_bytes, candidate_bytes, spec)` 接收完整字节字典。`RepositorySpec.from_mapping` 加载 **宿主私有** `validation-04/private-spec.json`。此 spec 包含隐藏测试内容/身份/允许 skip；不能传给 agent。`attempt-02/private/known-good.json` 是校准答案，也不能用于生成候选或构造 prompt。

CLI 接收新 assignments 文件，路径相对于该文件：

```json
[
  {
    "task_id": "pallets__flask-4992",
    "spec": "validation-04/private-spec.json",
    "base": "attempt-02/public/base.json",
    "candidate": "pilot-candidate.json"
  }
]
```

该示例 assignments 和 `pilot-candidate.json` 位于证据根目录。候选格式与 base 相同，必须包含完整仓库，新增/删除/修改非授权路径均拒绝。每个 assignments 文件要求 task_id 唯一；同任务不同实验 arm 使用不同输出目录和独立调用，外层按预先冻结的实验 arm 汇总。

```powershell
.venv\Scripts\python.exe scripts/run_repo_grader.py --assignments docs/upgrade/evidence/full-repo-grader/pilot-assignments.json --output-dir docs/upgrade/evidence/full-repo-grader/pilot-evaluation-NEW
.venv\Scripts\python.exe scripts/run_repo_grader.py --regenerate docs/upgrade/evidence/full-repo-grader/pilot-evaluation-NEW/evaluation
```

输出目录必须全新。任何非 pass 返回非零；逐任务保留结果，缺候选也保留已冻结分母。最终 pass 要求全部必测项通过、完整测试身份一致、允许 skip 状态满足、进程和回执退出码一致、输入完整性检查成功、输出不截断、容器清理成功。终端打印 passed 或 exit=0 不足以通过。

grader 镜像须提供 `/usr/local/bin/python`、固定 pytest 和 `/opt/grader-environment.txt`；项目依赖预装。资源固定 1 CPU、1GiB 内存、128 pids、128MiB workspace tmpfs、64MiB /tmp，收集120秒/测试300秒。传输仍限 8MiB/2048 文件，未提高或绕过该边界。

## 其余任务与限制

全12项 inventory 见 `audit-01/readiness-inventory.json`。其中原 fixture 盘点字段保留原貌；Flask-4992 的 `grader_readiness=ready` 和 `full_source_*` 是新增整仓环境结果。

| 任务 | 状态 |
| --- | --- |
| Flask-4992 | 已完成完整源树、固定环境和正负验收 |
| Flask-4045、Flask-5063、Requests-3362 | 原 fixture 在传输限额内，但完整源树/各自固定环境尚未验收 |
| 8 个 SymPy 任务 | 原裁剪 fixture 已约27.9–35.8MB，超过8MiB传输限额；blocked_transfer_quota |

不能将 Flask 依赖镜像直接作为另外11项的已验证环境，也不能删文件使 SymPy 静默进入现有配额。

候选与 pytest 仍在同一个 Python 解释器内运行。固定测试、独立宿主判分和文件检查能防普通实现错误及测试/config 篡改，但不能证明恶意 Python 无法伪造插件/回执；运行后文件检查也不是对“修改后恢复”的不可伪造证明。该 grader 不应被宣传为强对抗防作弊边界。

本次新增 src 模块使全仓 source fingerprint 改变。验收指纹为 `35b06e5ed54c77d7260164a9ebe951485fda1801925742801e6a932749ea0b80`；正式 pilot 必须在双方代码稳定后重新冻结当时指纹，不能直接继承旧指纹或恢复旧运行。未修改或覆盖 `pilot-01`、`wrapper-01`。

## 复现与证据

合同 `FULL-REPO-GRADER-CONTRACT.zh-CN.md`，环境修订 `FULL-REPO-GRADER-ENV-AMENDMENT.zh-CN.md`，尝试历史见证据根目录 `README.md`。implementation 快照与逐项结果哈希保存在 `audit-01/`，只用于宿主审计。

```powershell
docker --context desktop-linux build --progress plain -t coding-harness-flask4992-grader:attempt-02 docs/upgrade/evidence/full-repo-grader/attempt-02/build
.venv\Scripts\python.exe scripts/preflight_repo_grader.py --source-dir docs/upgrade/evidence/full-repo-grader/attempt-02 --output-dir docs/upgrade/evidence/full-repo-grader/validation-NEW --image coding-harness-flask4992-grader@sha256:2a19ad90214fcaf08388547c0a37deb209996c263a2358466da8aa4fa497f4e0
.venv\Scripts\python.exe scripts/audit_repo_grader.py --source-dir docs/upgrade/evidence/full-repo-grader/attempt-02 --validation-dir docs/upgrade/evidence/full-repo-grader/validation-04 --previous-validation-dir docs/upgrade/evidence/full-repo-grader/validation-01 --output-dir docs/upgrade/evidence/full-repo-grader/audit-NEW
```

重建会因构建工具/attestation 产生不同 digest；先 inspect 实际新 digest，再作为新的环境记录重新验收，不能替换冻结证据里的镜像标识。离线 audit 会拒绝与验收时 source fingerprint 不一致的当前代码，这属于预期的漂移检测。
