# HP-03 环境 allowlist 与 legacy 迁移

## 环境变量语义（迁移）

### 旧行为（HP-03 前）
- `env_whitelist == []` → `env=None` → **继承全部宿主环境**
- 非空白名单：白名单 ∪ 系统键（含 `HOME` / `USERPROFILE`）

### 新行为（HP-03）
- **空 allowlist**：只注入最小启动变量  
  - POSIX：`PATH`, `TMPDIR`, `LANG`, `LC_ALL`（若宿主存在）  
  - Windows：`PATH`, `PATHEXT`, `SystemRoot`/`SYSTEMROOT`, `WINDIR`, `COMSPEC`, `TEMP`, `TMP`
  - （`PATHEXT` 为 cmd 解析 `python`→`python.exe` 所必需；仍不注入 HOME/USERPROFILE）  
  - **不**默认注入 `HOME` / `USERPROFILE`
- **非空 allowlist**：最小启动变量 ∪ 明确列出的变量（大小写不敏感匹配）
- 可选 `controlled_tmpdir`：写入受控临时目录到 `TMP`/`TEMP`/`TMPDIR`
- 探针使用假凭据名（如 `HARNESS_FAKE_SECRET`）；禁止变量不得出现在子进程观察/trace

## execution_profile 迁移

| profile | 含义 | Windows | Linux |
|---|---|---|---|
| `controlled` | 要求可回收进程树 | **创建前 blocked** | session/group + TERM/KILL |
| `legacy_host` | 显式宿主执行，**无**树回收保证 | 允许（默认） | 允许但不推荐 |

配置字段：`policy.command.execution_profile`（默认 `legacy_host` 以保持既有 Windows 测试可跑）。

受控生产路径应设为 `controlled`，并在 Linux 上运行；Windows 受控任务应拒绝而非静默退回宿主。

## Subagent 迁移

- 旧：子 agent 独立 `Budget`，可能漏计模型费用
- 新：`runtime.subagents.enabled=true` **必须** `share_parent_budget=true`，且配置 `runtime.budget`（至少 `max_model_calls` 或 `max_tokens`）
- 否则 `build_agent` 抛错，避免静默漏计
