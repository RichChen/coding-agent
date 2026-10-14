# A5 initial24：整仓环境与 baseline 预检

2026-09-22。最终证据为 `evidence/A5-harness-preflight-47-final-audit/`。

环境 **24/24** 通过；环境＋baseline **23/24** 通过。完整分母、canonical
handoff 和私有补丁均未变。最终审计 **173/173** 项通过，表示报告与原始证据
一致，不表示剩余那题的 baseline 被豁免。模型调用 0，付费 build/pilot 均未启动。

| 仓库 | 题数 | 环境通过 | baseline 通过 |
|---|---:|---:|---:|
| Django | 5 | 5 | 4 |
| SymPy | 5 | 5 | 5 |
| scikit-learn | 5 | 5 | 5 |
| pytest | 5 | 5 | 5 |
| Sphinx | 4 | 4 | 4 |
| 合计 | 24 | 24 | 23 |

20 个目标中 19 个 baseline 通过；4 个初始历史题全部通过。此前已独立审计的
4 个 pytest 收据按精确 source/image/collection/baseline 身份沿用；其余 20 题
各自拥有新 baseline/gold image。**40/40** 个新 image 的完整源码、文件内容、
mode、symlink 和环境清单已核验。所有运行的 cleanup 收据有效，最终 Docker
检查无 `coding-harness.h3=true` 容器残留。

## 唯一 baseline 阻塞

`django__django-13265`，固定 base commit
`b2b0711b555fa292751763c2df4fe577c396f265`，完整收集 14,078 项。
私有 F2P 声明四项，但实际 baseline 为两项失败、两项通过；gold 四项全部通过。

| `migrations.test_autodetector.AutodetectorTests` 中的测试 | baseline | gold |
|---|---|---|
| `test_add_model_order_with_respect_to_index_constraint` | fail | pass |
| `test_set_alter_order_with_respect_to_index_constraint_foo_together` | fail | pass |
| `test_add_model_order_with_respect_to_index_foo_together` | pass | pass |
| `test_supports_functools_partial` | pass | pass |

完整 `migrations.test_autodetector` 模块复跑仍得到相同的两项已通过，证据保留在
`evidence/A5-harness-preflight-28-django13265-module/`。最终逐题结果位于 attempt-32，
attempt-47 绑定其收据与两个 image digest。没有删题、删除 F2P、替换 base commit，
也没有把“全部 F2P 失败”降为“任一 F2P 失败”。要达到 24/24，需要先核验并版本化
解决该私有 F2P 合同不一致，再按新绑定重跑；当前记录不得覆盖。

## 已落地的环境修复

- 完整 image 源码复制到受限 workspace，保留原始权限和链接，避免 tmpfs 遮住镜像源码。
- baseline 为原仓＋同一私有 test patch；gold 在此基础上叠加修复 patch。Windows Git
  换行转换被禁用，patch 前后按完整 typed tree 检查越界修改。
- Django 使用各自的 `tests/runtests.py`、SQLite 和结构化 unittest 收据；docstring
  ID 通过精确 AST 文本与收集结果绑定，test-body 异常与 setup/import 错误分开。
- SymPy 跨测试文件精确绑定短名称；1.6 按其自带 native helper 初始化，保留完整 collection。
- Sphinx 按版本固定 Jinja2、Pygments 和扩展；8721 运行完整测试文件，保留 HTML→EPUB
  的共享 fixture 状态，避免孤立运行导致 baseline 假通过。
- scikit-learn 从各题源码编译，旧 0.20 使用独立旧依赖。编译器来自带日期的 Debian
  snapshot，依赖清单和 image digest 留存。gold 仅在完整非 Python 源树相同时复用
  native 编译产物。生成的 `.so` 从只读 image 加载并记录哈希，workspace 的 noexec
  保留；上游自带二进制 fixture 原样保留。

测试 runner、archive staging、精确 ID 绑定的四项回归测试通过；最终脚本编译检查通过。
失败/诊断 attempt 均保留，最终审计明确选择后续有效收据。没有使用 Flask 环境。

## 给 coding-agent 的消费边界

机器 handoff：`configs/a5/image-backed-handoff.json`。最终 readiness、逐题收据、
源码/环境审计引用、cleanup 和本轮实现 fingerprint 均在 attempt-47。

`environment_ready=24`、`environment_baseline_ready=23`、`grader_ready=4`、
`memory_build_eligible=false`。新 20 题的 F2P gold 通过不代替独立 grader 的完整
P2P、负例拒绝等校准。pytest-7432 的环境/F2P 已绿，但先前发现的五个截断私有
P2P node ID 仍是 grader 合同阻塞，未做模糊替换。

baseline/gold images 含私有补丁，仅供 grader；公开 source image 仍使用 attempt-23。
剩余 16 个 memory source 尚未预检，初始四个历史题不能替它们放行。model snapshot
与现价、独立 CNY build ledger、双方稳定后的 source fingerprint 重冻、B0–B3 收据
接线仍需各自证据。本轮实现 fingerprint 不是双方正式重冻。当前不得启动付费建池或 pilot。
