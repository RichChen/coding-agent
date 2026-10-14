# A5 harness preflight — blocked, offline

2026-09-21。该目录是 coding-harness 侧 A5 gate 的离线结果，不是 build/pilot 结果。没有 Docker、网络依赖安装、模型调用或付费动作。

- manifest：20 个目标题 + 4 个历史池题，B0–B3 × 3 repeats，240 planned task-runs；与 coding-agent 的 source-lock/public-review hash 绑定。
- 大仓传输：runtime 仍为 8 MiB/2048 files；大于限制必须完整 image-backed archive + content-addressed chunks，agent 只回传 allowlisted candidate delta。
- CNY 计划：总额 50.000，build 3.840，pilot 46.080，reserve 0.080；未知 usage 不释放 reservation。
- gate 输出：`readiness.json` 状态 `blocked`，model calls=0，paid_build_started=false，paid_pilot_started=false。

当前阻塞是有意的：model snapshot/current CNY price 尚未由宿主以 `verified=true` 绑定；24 道题没有各自的整仓 environment/baseline receipt；双方代码稳定后的双端 source fingerprint 尚未冻结。模板中的空 rows 不算环境失败预检，不会缩小分母。

验证命令：

```powershell
.venv\Scripts\python.exe -m pytest tests/test_a5_infrastructure.py tests/test_repo_grader.py tests/test_h3_grader.py -q --basetemp .tmp-a5-infra-03
# 45 passed
.venv\Scripts\python.exe scripts/a5_preflight.py --model-binding configs/a5/model-price-binding.pending.json --environments configs/a5/environment-preflight.template.json --fingerprint-manifest configs/a5/source-fingerprint.pending.json --output docs/upgrade/evidence/A5-harness-preflight-NEW
# expected exit 2 / blocked
```

只有替换完整、审核过的 model binding、24 行独立 baseline receipt 和双端 fingerprint 后，gate 才能进入下一阶段；即使 gate 变为 ready，也只允许另行审批的 4 个历史 build jobs，不能自动开始 240 条 pilot。
