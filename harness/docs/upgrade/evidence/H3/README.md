# H3 验收记录（2026-09-20）

结论：受控 Docker run 生命周期、容器文件/命令工具、宿主判定的独立黑盒 grader、全分母可重建报告已实现并实测。没有调用真实或付费模型；不把模拟模型成功当作 H5 证据。

## 最终检查

| 检查 | 实际结果 | 证据 |
| --- | --- | --- |
| Windows 全量回归（显式启用真实 Docker） | **285 passed、6 skipped，0 failed / errors**，59.47s | `windows-regression.xml`，291 项 |
| 其中 H3 新增测试 | 32 passed：公开契约 3、grader/快照/报告 16、真实 Docker 13 | 上述 JUnit 中 `test_h3_contracts`、`test_h3_grader`、`test_docker_execution` |
| Linux 专用进程树测试 | **6 passed**，24.51s；对应 Windows 的 6 项 skip | 下方固定镜像与实际命令 |
| CPU/RAM/pids | cgroup 观测 `50000 100000` / `134217728` / `24`；进程数和磁盘填满反例通过 | `final/isolation-limits.json` |
| OOM | 分配 256 MiB、限额 64 MiB，退出 137、会话销毁 | `final/oom.json` |
| cancel / timeout / task.cancel | 含 setsid 后代，容器销毁后 daemon 查询为空 | `final/cleanup-*.json` |
| 启动中取消、stdout/stderr 配额 | 正确清理；管道排空不会无限等待 | JUnit 对应用例 |
| 全部五种文件工具 | 实际在容器执行；路径越界拒绝，宿主未产生候选文件 | JUnit `test_all_file_tools_container_only_and_path_denials` |
| symlink、超限快照、清理失败 | 拒绝产生成功候选/继续复用会话 | JUnit 反例 |
| 独立 grader 正反例 | 正常候选通过；伪造通过标记、缺依赖均失败 | `final/grader-negative-and-positive.json` |
| 完整 run → 清理 → 独立 grader | 模拟模型 4 轮，容器修改 `answer.py`，宿主 seed 不变，隐藏用例通过 | `final/e2e/` |
| grader CLI 与离线重建 | 2 assigned / 1 pass / 1 invalid_env，报告 **50%**；离线重建退出成功 | `final/cli-evaluation/` |
| 遗留容器检查 | 按 `coding-harness.h3=true` 查询所有状态，无结果 | 最终 Docker 查询 |

环境：Windows Python 3.13.9；Docker Engine 29.8.0；context `desktop-linux`；Linux `6.18.33.2-microsoft-standard-WSL2`。生产执行镜像与资源值见每份 manifest。

## 复验

```powershell
$env:PATH='D:\crq\base\Anaconda3;D:\crq\base\Anaconda3\Scripts;' + $env:PATH
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONDONTWRITEBYTECODE='1'
$env:HARNESS_DOCKER_TESTS='1'
$env:HARNESS_H3_EVIDENCE='<new-evidence-directory>'
$env:HTTP_PROXY=$null; $env:HTTPS_PROXY=$null; $env:ALL_PROXY=$null
$env:NO_PROXY='127.0.0.1,localhost'
.\.venv\Scripts\python.exe -m pytest tests -q -p no:cacheprovider --tb=short --basetemp=tmp/<new-temp-directory>
```

Docker 测试不在 collection 阶段探测并静默跳过：未 opt-in 才 skip；显式启用但 Docker/镜像不可用时失败。受限工具沙箱访问 Docker 命名管道和部分 pytest 临时目录会被拒绝，本次真实验收使用了获准的宿主执行权限。

Linux 测试镜像由 `docker/h3-tests.Dockerfile` 构建，专用 dockerignore 只送入源码和这一个测试文件，不送入 `.env`、Git、workspace 或其他私有材料。实际运行的不可变 digest：

```text
coding-harness-h3-tests@sha256:18872d18b9bc347cf4441b1d9b53b9662ea719f057bd471c7d4cbfce4dc2e78e
```

实际命令：

```powershell
docker --context desktop-linux run --rm --name h3-linux-acceptance --label coding-harness.h3=true --read-only --network none --cap-drop ALL --security-opt no-new-privileges:true --user 1000:1000 --cpus 1 --memory 512m --memory-swap 512m --pids-limit 128 --tmpfs /tmp:rw,nosuid,nodev,size=64m,mode=1777 coding-harness-h3-tests@sha256:18872d18b9bc347cf4441b1d9b53b9662ea719f057bd471c7d4cbfce4dc2e78e
```

实际 stdout：`...... [100%]`、`6 passed in 24.51s`，exit 0。这是本机 WSL2 Docker Linux 的进程组证据，不扩大为其他 Linux 发行版、Windows 原生进程树或任意平台保证。容器与宿主没有 bind mount。

## 调试过程保留

- `attempt-01`：输出配额命中后，容器已去除，但宿主等待 CLI pipe 的路径卡住，测试主动中断，不能算通过。
- `attempt-02`：25 passed / 3 failed。两个测试问题是非 root 读取 root 目录应允许 PermissionError，以及 Windows seed 换行必须按字节冻结；执行器问题是先 rm 再断开饱和的 attach 管道会超时。
- 修复为先关闭/有界排空 CLI 管道，再销毁并核查会话。`attempt-03` 原 9 项 Docker 测试全部通过。
- `final`：补充所有文件工具、坏快照及故意清理失败反例后，13 项真实 Docker 测试随全量回归全部通过。保留前次证据，不覆盖失败。

## 明确限制

首版 grader 是固定 Python 函数/JSON 黑盒验证，不是通用 pytest 项目适配。候选总额 8 MiB、2048 文件，文本文件工具单文件 1 MiB。中断 Docker session 不自动 resume；强杀宿主进程或 daemon 持续不可达时，需要按已记录容器名人工核对清理。完整边界与入口见 `../../H3-IMPLEMENTATION.zh-CN.md`。
