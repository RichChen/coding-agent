# Hardened Argv — Real Repo Tasks Eval

> Status: **real API-backed run** (2026-06-25).

```bash
python scripts/run_eval.py --dataset datasets/repo_tasks.json --configs hardened_argv --runs 1
```

Source: `reports/report_20260625T081432.md`

## Summary

| Config | Tasks | Passed | Success Rate | Avg Steps | Policy Blocks |
|--------|-------|--------|--------------|-----------|---------------|
| hardened_argv | 12 | 11 | **91.7%** | 5.9 | 6 |

## 安全边界要点

- `run_command` 支持 `argv` 非 shell 执行（opt-in）
- `CommandPolicy.check_argv` 仅校验 `argv[0]` basename
- `env_whitelist` 隔离子进程环境变量
- `command_executed` 事件含 `mode: shell|argv`

Config: `configs/hardened_argv.yaml`
