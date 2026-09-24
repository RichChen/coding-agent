# H3：受控 Docker 后端与独立评测

2026-09-20 实现并在本机 Docker Desktop / WSL2 Linux 上验收。此文更新 IMPLEMENTATION-PLAN 中历史环境记录；不改写当时“Docker 不可用”的事实。

## 实现范围

- `docker_linux` 是显式选择的执行 profile。每个 agent run 一个容器，六种工具（read/write/list/edit/search_replace/run_command）共享该容器。旧 host profile 不自动切换，旧 EvalRunner 拒绝用宿主 workspace 裁判 Docker 结果。
- 不挂宿主目录、Docker socket、home 或凭据。显式公开 seed 以有界数据复制到容器，默认网络关闭，固定镜像 digest、非 root、只读根文件系统、cap-drop ALL、no-new-privileges。Docker 不可用/镜像未预置时拒绝运行，不回退宿主。
- 默认 CPU 1、RAM 512 MiB（禁止额外 swap）、pids 128、workspace tmpfs 64 MiB、/tmp tmpfs 16 MiB。Docker 自带 /dev/shm 仍有其默认限额；这些 tmpfs 同时受容器内存总额约束。bridge 网络只表示显式开放网络，不是域名白名单。
- 文件工具单文件最多 1 MiB；公开 seed / 候选快照合计最多 8 MiB、2048 文件。拒绝 symlink、junction、特殊文件及不安全路径。忽略 `.env*`、`.git`、`.oracle` 等敏感目录，但任意命名的私有材料仍须由调用者放在公开 seed 之外。禁止直接将 harness 根目录用作 seed。
- 超时、取消、OOM、输出总额耗尽等使整个会话终止。先关闭并排空 Docker CLI 的附加管道，再销毁容器，最后查询 daemon 验证容器不存在；清理失败明确失败，不能复用会话。实测包含 setsid 脱离原进程组的后代。
- 正常完成导出有界候选字节快照，销毁容器后才落终态并验证候选。快照不是运行中文件系统的原子快照；grader 只评价已经冻结的字节，后台进程无法在 grader 启动后改它。超限或 symlink 导出失败时不产生成功候选。

## 验证信任边界

`PublicTask` 与 `EvaluationSpec` 是分开的输入。只有公开 DTO 进入模型消息。私有 spec、预期值及报告不进入 agent 容器。

首版采用 **固定 Python 函数黑盒用例**：私有 spec 固定测试 ID、模块路径、函数、JSON 参数和 JSON 预期值。每个用例从冻结 base 加允许改动重建到一个新容器，用固定 `python -I -S` runner 执行；预期结果只在宿主比较。采集数量来自宿主固定用例集合，零用例/重复 ID 被拒绝。候选自己的 pytest 配置、插件、stdout 通过标记、最终回答和 JUnit 不能决定测试数量或通过状态。输出必须与预期 JSON 完全一致且退出成功、未截断、清理成功。

所有非 editable_paths 的新增、改动、删除都会被记录并判失败，包含删测试与添加 conftest/pytest.py。base hash 不一致、容器不可用、候选缺失、清理失败为 invalid_env；执行缺依赖/异常/超时为未通过。整个测试集合必须完成才能 pass。

这不是通用 pytest 仓库适配器，不支持任意依赖安装、项目内 import graph、二进制补丁或文件权限变更。该限制是可信验证边界的一部分；不能据此声称已验证任意开源仓库。未来增加 pytest 适配时仍须解决被测代码与测试 runner 同进程的伪造风险。

## 入口与产物

```powershell
# 使用具备 Docker Desktop 访问权限的终端。镜像只需显式预置一次。
docker --context desktop-linux pull python@sha256:2f17fc044b579bab302c2e8054d3a686e2cb9a83de48e70534b94cd8ebbe06a9

# 实际模型调用入口：需自行配置模型及预算；本轮没有调用付费模型。
.\.venv\Scripts\python.exe scripts/run_h3.py --config configs/docker.yaml --public-task <public-task.json> --private-spec <private-spec.json> --workspace <public-seed> --output-dir <new-run-directory>

# 只复验冻结候选：assignments 内路径相对于 assignments 文件。
.\.venv\Scripts\python.exe scripts/run_grader.py --assignments docs/upgrade/evidence/H3/final/cli-assignments.json --output-dir <new-grader-directory>

# 离线重生成，不启动 Docker 或模型。
.\.venv\Scripts\python.exe scripts/run_grader.py --regenerate <grader-directory>
```

CLI 例子故意分配一条缺失私有 spec 的任务：应退出 2、成功率 50%，不能剔除失败任务变成 100%。私有 spec 示例见 `evidence/H3/final/private-spec.json`，公开 DTO 示例见 `evidence/H3/final/e2e/public-task.json`。base/candidate JSON 是路径到 base64 字节的映射，hash 基于原始字节，不归一化换行符。

`run_h3` 输出 public-task、manifest、base、candidate、run-result、evaluation-result 和独立 evaluation/manifest+results+report；session/ 中保留 SQLite 有序事件、原始输出和候选内容寻址 artifact。manifest 记录代码 hash（含未提交源码）、Git HEAD、config hash、公开/私有 spec hash、base hash、镜像、资源、主机、预算；结果记录候选 hash、改动路径、每个 case ID、输出及容器生命周期。token/cost 不明时保持未知。

输出目录必须为新目录，重跑保留旧失败。统计分母固定为全部 assigned task，invalid_env 和缺失结果均在分母中。报告重建校验 results hash，不执行候选。

`run_single.py --config configs/docker.yaml` 必须指定 `--session-dir` 保存候选；它只提供执行结果，不等于独立 grader 验收。

## 恢复边界

终态 session 可离线 replay，候选 artifact 校验 hash。Docker 中断 session 的自动 resume 尚不支持：明确拒绝从新容器重复执行旧操作。事件中先记容器名再创建；宿主进程被强杀、daemon 长期不可达时，不能保证自动回收容器，需按该 session 的准确容器名核对清理后建立新 run。正常协作式取消、工具超时与直接 task.cancel 已真实测试。未声称抵御内核漏洞、恶意 Docker daemon 或宿主控制进程被杀。

参考项目 `C:\Users\23500\Desktop\src\learn-Codex-main` 在本机不存在，本轮沿用当前仓库的 execution、session、artifact 契约完成实现，未声称读取到该参考实现。

## 验收证据

见 `evidence/H3/README.md`。H3 最小受控后端与黑盒独立验收链已落地；H4 策略接口、H5 真实模型修复和通用仓库测试适配不在本轮完成声明内。
