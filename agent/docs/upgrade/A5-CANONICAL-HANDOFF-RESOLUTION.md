# A5 canonical handoff 冲突解决记录

后续消费补充：新增 [宿主CLI兼容manifest](../../configs/a5/pilot20-harness-consumption-manifest.json)，SHA256=`33ab6922caf6909888d672a8d97df49f305ed4cdabb8c402dfca4bca88cb0180`，包含20-source/4-subset逐条ID映射，并将正确公开审查hash放在宿主读取的 `source_dataset.public_review_sha256` 中。canonical JSON及原jobs/attempts/assignments未改。已按最新指令通知harness任务消费此路径并重跑只读gate；下面“未发送协调消息、消费pending”属于上一轮快照，不作本轮完成声明。新回执存入 `reports/upgrade/a5-canonical-consumption-20260921/`，仍禁止paid build/pilot。

2026-09-21。本轮只收口交接；provider calls=0，paid build/pilot 均未启动，无新增 MemoryRecord。只读核对 harness gate、manifest、24 题模板及离线 gate 脚本；环境 rows=0。已固定的是计划 IDs，尚无 runnable freeze。

唯一消费入口：[canonical-handoff.json](../../configs/a5/canonical-handoff.json)。所有相对路径基于 `D:/crq/src/coding-agent`；该文件仅供宿主，不可挂载给 agent 或写入 memory index。旧 v12 jobs/attempts 字节保留，旧 handoff 不再作为独立执行授权。

## 三个集合与 canonical IDs

跨仓 canonical ID 使用 SWE-bench `source_instance_id`；本仓已有 `a5-task-*`、`a5-build-*` 和 job/attempt IDs 均原样保留，逐条对应及精确 repo/commit 在机器清单内。

| 仓库 | 正式 target tasks（共20） | memory-build sources（共20；标“预检”的4条为子集） |
| --- | --- | --- |
| django/django | `django__django-13265`<br>`django__django-15781`<br>`django__django-13590`<br>`django__django-13448` | `django__django-10914`（预检）<br>`django__django-10924`<br>`django__django-11001`<br>`django__django-11019`<br>`django__django-11039` |
| sympy/sympy | `sympy__sympy-20154`<br>`sympy__sympy-24152`<br>`sympy__sympy-20442`<br>`sympy__sympy-18532` | `sympy__sympy-11400`（预检）<br>`sympy__sympy-11870`<br>`sympy__sympy-11897`<br>`sympy__sympy-12171`<br>`sympy__sympy-12236` |
| scikit-learn/scikit-learn | `scikit-learn__scikit-learn-25747`<br>`scikit-learn__scikit-learn-25500`<br>`scikit-learn__scikit-learn-25638`<br>`scikit-learn__scikit-learn-25570` | `scikit-learn__scikit-learn-10297`（预检）<br>`scikit-learn__scikit-learn-10508`<br>`scikit-learn__scikit-learn-10949`<br>`scikit-learn__scikit-learn-11040`<br>`scikit-learn__scikit-learn-11281` |
| pytest-dev/pytest | `pytest-dev__pytest-8365`<br>`pytest-dev__pytest-7432`<br>`pytest-dev__pytest-9359`<br>`pytest-dev__pytest-7220` | `pytest-dev__pytest-5103`（预检）<br>`pytest-dev__pytest-5221`<br>`pytest-dev__pytest-5227`<br>`pytest-dev__pytest-5413`<br>`pytest-dev__pytest-5495` |
| sphinx-doc/sphinx | `sphinx-doc__sphinx-10451`<br>`sphinx-doc__sphinx-8721`<br>`sphinx-doc__sphinx-8595`<br>`sphinx-doc__sphinx-8713` | 无；保持缺口 |

因此首次 gate 的分母是 **20 targets + 4 preflight history = 24**，完整 memory source pool 是 **4 + 16 = 20**。4 条历史预检通过不能替其余16条过 gate。20 个 build jobs 均 `prepared_not_started`；40 个预留 attempts 保留原 `planned_not_started`（未执行）状态，每来源最多2次；不是40条记忆，也不是实际 provider attempts。

## 冲突与处理

| 冲突 | canonical 处理 | 当前状态 |
| --- | --- | --- |
| harness 把 `historical_pool=4` 写作完整历史池 | 仅解释为当前24题中的4条历史预检子集；完整20来源另列 | 本仓映射完成，待 harness 消费确认 |
| harness 仍描述总50/build3.840/pilot46.080 | 保留本仓 pilot cap50、参考46.080、memory build独立账本；本轮不改预算运行代码 | 宿主账本未对齐，禁止付费 |
| harness 的 public review hash 缺字符 | 实际文件 SHA256 为 `d1fe518b3b697eb3a992db6ba24a4786c98c7c5f04766c09286e2502d1773ebd`；旧值 `d1fe518b697eb3a992db6ba24a4786c98c7c5f04766c09286e2502d1773ebd` 不匹配 | 需宿主更正绑定，禁止按错误hash冻结 |
| 清单冻结被混同于可运行冻结 | `runnable_frozen=false`；environment/baseline/grader/trajectory/receipt 均不补造 | blocked |

已逐项核验20来源的 pinned dataset/revision、source row hash、公开 issue/DTO hash、repo/base、私有 spec 引用和目标去重（ID、repo+commit、原始/trimmed issue），且均早于同仓targets。语义近重复与逐来源许可证审查仍待完成，不把精确去重当完整语义审查。公开/私有字段边界逐条引用同一规则；target答案、隐藏测试、未来pilot轨迹及虚构procedure均禁止作记忆来源。Sphinx仍无合规历史来源，不增题、不凑数。

## harness 消费顺序与停止点

1. 消费 canonical清单，先核对现有24题模板，执行零模型、只读/离线preflight gate。每题自己的完整仓库、环境、collection、baseline/grader证据缺失时保持blocked，不能沿用Flask证明或删分母。本轮只审计模板，未执行仓库代码/环境预检。
2. 初始24题gate通过后，其余16个memory sources仍逐项完成自己的仓库/环境/baseline/grader预检。4条已有回执也只能用于精确匹配的来源。全部共享model/price/ledger/fingerprint/receipt条件仍必须满足；通过只产生对应来源的资格，本轮不自动执行。
3. 后续获得执行指令才进入paid build；只接收真实公开轨迹、公开验证、依赖映射及独立grader收据齐全且审查通过的MemoryRecord。失败/unknown/invalid_env留证留账，不能升格。之后才谈冻结memory snapshot与原样B0–B3/240-run pilot。

harness应读取：

- `D:/crq/src/coding-agent/configs/a5/canonical-handoff.json`（集合、ID映射、repo/commit、逐来源provenance/边界/状态及gate顺序）。
- `D:/crq/src/coding-agent/reports/upgrade/a5-canonical-handoff-20260921/identity-audit.json`（194+68个既有artifact的hash核对、输入hash和审查hash冲突）。
- `D:/crq/src/coding-agent/reports/upgrade/a5-funded-build-preparation-20260921-v12/build-jobs.json` 和 `build-attempt-plan.json`（原20 jobs/40 attempts，未重建）。
- `D:/crq/src/coding-agent/reports/upgrade/a5-pilot20-preparation-20260921-v4/assignments.json`（原240行，不变）。

本轮未改coding-harness、未发送协调消息。跨仓消费确认仍为pending；不能声称对方文件已同步。交付停在handoff等待，不运行provider或付费任务。
