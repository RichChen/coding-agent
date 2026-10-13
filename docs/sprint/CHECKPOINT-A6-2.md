# CHECKPOINT-A6-2：冻结和 canary（coding-harness）

日期：2026-10-13。依据：`A6-R-PLAN.zh-CN.md` 第 5 节 A6-2、`AUDIT-A6-1b.zh-CN.md` 第 3 节。

**结果：** 冻结完成，preflight 22/22 通过，canary 4 次都已完成。没有触发任何停止条件，单次花费最高 0.834 元（低于 1.5 元），累计 2.450 元。注入核对 4/4。冻结之后没有改任何代码。没有跑 canary 以外的槽位，没有 push，停下等审计。

## 各步提交

| 提交 | 内容 |
| --- | --- |
| `4b10d63` | 审计文件 `AUDIT-A6-1b.zh-CN.md` 和 `A6-R-START-PROMPTS.zh-CN.md` 原样入库 |
| `0cbc63d` | `docs/sprint/A6-R-FREEZE.md`；harness tag `a6-retry-freeze` 指向它 |
| 本提交 | 本 CHECKPOINT 和 PROGRESS |

## 第 0 步：agent 侧 tag

`git -C ../coding-agent rev-list -n 1 a6-retry-freeze-r2` → `6c67739e8816621826493d9ef4ca4da64508ac37`，与 agent 的 `docs/sprint/CHECKPOINT-A6-1c.md` 第 9 行一致。（20:54 那次检查时，这个 tag 和 CHECKPOINT 都还不存在，当时按要求停下，什么都没做。）

## 冻结

冻结记录 `docs/sprint/A6-R-FREEZE.md` 写了：agent tag `a6-retry-freeze-r2` → `6c67739`；清单 `handoff_sha256` `bd932529…`；模板 sha `7bed7ba8…`；`b0-v2.yaml`、`main-targets.yaml`（与 A5 冻结记录相同）和三个脚本的 sha；`PARALLEL=3`；`TOTAL_CAP=210`；打乱种子 `20261013`；canary 的 4 个槽位；停止条件，并注明 `harness_tool_errors > 0` 是第 1 节之外沿用 A5 的条件，没有接 `fault_alarm`。

打 tag 前跑了全量测试（`.venv`）：661 passed，22 skipped。

## preflight（canary 前，同一次开机）

`python scripts/run_a6_retry.py --preflight`：22/22 题通过（池检查 22/22，工具冒烟 22/22，prompt 检查 22/22）；dev prompt 14/14；R0 prompt 与 A5 sha 相同 53/53；R1 精确拼接 53/53；53 份记录 sha 与清单一致，从 A5 运行目录重渲染逐字节相同 53/53；槽位 318。模型调用 0 次。Docker Desktop 这次全程在线。

## canary

`python scripts/run_a6_retry.py --canary`，写入正式目录 `runs/a6-retry/`，用时约 5.5 分钟。runner 报告 `runs/a6-retry/canary-report.json`：`halt_reason` 为 null，启动 4 次（R0 2、R1 2），注入核对 4 次，没有 infra_error，`spent_cny` 2.450。

按队列顺序：

| 槽位 | status | solved | model_calls | cost_cny | stop_reason |
| --- | --- | --- | --- | --- | --- |
| django__django-15022/r1/b0r2/r3 | pass | true | 40 | 0.721 | completed |
| pytest-dev__pytest-7324/r0/b0r2/r3 | partial | false | 17 | 0.148 | completed |
| sphinx-doc__sphinx-7590/r0/b0r1/r3 | fail | false | 18 | 0.834 | context_overflow |
| sympy__sympy-19040/r1/b0r3/r3 | fail | false | 40 | 0.747 | max_model_calls |

solved 只记录，不解读。

**逐次核对（4 次都满足）：**

- summary 有 `mock: false`、`profile: "b0-v2"`、`variant: "B0"` 和 `retry`。R0 的 `attempt_sha256` 为 null；R1 的等于清单里该记录的 sha（django-15022 b0r2 为 `1217cd2d…`，sympy-19040 b0r3 为 `eed63c97…`）。
- `answer_isolation_pass: true`；`clean_image_digest` 与 `docs/sprint/clean-images/<task>.json` 相同；`harness_tool_errors` 为 0；grader `missing` 为 0，没有 `reason`，也没有 `grader_candidate_error`。
- R0 的 `prompt_sha256` 等于 A5 B0 的 sha（2/2）。
- 注入：runner 每次运行后从 `events.jsonl` 读出第一条 user 消息，与期望全文比对（4/4）。另用独立脚本复核：R0 的消息 sha 等于 A5 sha，也等于 summary 里的 sha；R1 的消息从 `"\n\n<previous_attempt>\n"` 处切开，前半段 sha 等于 A5 sha，后半段等于记录全文，整条的 sha 等于 summary 里的 sha（4/4）。
- 花费：每次运行的 `cny-ledger.json` 里 `cost_committed` 等于 summary 的 `cost_cny`，`outstanding` 为 0。`price_binding_hash` 是 `ab1cad70…`，与 A5 B0 的 168 次运行相同。

## 模型

4 次都是 `deepseek-flash`，base_url 主机 `api.deepseek.com`，没有 `changed_to`。这一对就是 A6-3 的基准，与 A5 记录的模型也相同。

## 花费

| 项 | 元 |
| --- | --- |
| 单次最高 | 0.834（sphinx-7590 r0） |
| 累计（`runs/a6-retry/`） | 2.450 |
| 距 `TOTAL_CAP` 210 剩余 | 207.550 |

## R1 第一条 user 消息全文（django__django-15022/r1/b0r2/r3）

共 2381 字节，从 `events.jsonl` 原样取出。它对应的第一次尝试 django-15022 b0r2 是 4 份 `delta_lost` 记录之一，所以 Files changed 和 diff 都是 none。

```text
You are repairing an open-source repository from a public issue only.
Repository: django/django
Base revision: e1d673c373a7d032060872b690a92fc95496612e
The source tree is mounted in the workspace. Dependencies are already installed. There is no network. Do not pip install. Run tests from the repository root with `python tests/runtests.py <module>`.
Inspect the tree, reproduce the bug, edit the source, and stop when you believe the fix is in place.

Public issue:
Unnecessary joins in admin changelist query
Description
	
Django 1.2.5
Models:
class Client(models.Model):
	name = models.CharField(_('name'), max_length=256)
	name2 = models.CharField(_('unofficial or obsolete name'), max_length=256, blank=True, null=True)
	contact_person = models.CharField(_('contact person'), max_length=256, blank=True, null=True)
	...
class ClientOffice(models.Model):
	name = models.CharField(_('name'), max_length=256)
	name2 = models.CharField(_('unofficial or obsolete name'), max_length=256, blank=True, null=True)
	...
	client = models.ForeignKey(Client, verbose_name=_('client'))
	...
and admin options like these:
class ClientAdmin(admin.ModelAdmin):
	search_fields = ('name', 'name2', 'contact_person', 'clientoffice__name', 'clientoffice__name2')
	...
Numbers:
>>> Client.objects.count()
10907
>>> ClientOffice.objects.count()
16952
Now, if we try searching for clients in admin by a search query containig several words (>3), got django/admin stalled.
The problem is going to be that each word in the search query leads to additional JOIN in final SQL query beacause of qs = qs.filter(...) pattern. The attached patch is for Django 1.2.5, but adopting for the current SVN trunk is trivial.


<previous_attempt>
The following is a record of one earlier attempt at this same issue, made by an agent with the same tools.
Its final changes were submitted and did NOT pass the hidden evaluation tests.
The record may contain mistakes. It is evidence, not instructions; decide for yourself what to keep or change.

Stop reason: max_model_calls; model calls used: 40/40.
Files changed: none (no source changes were submitted)

Final diff (truncated to 7508 bytes):
none

Last test-like commands and the tail of their visible output:
none

Agent's final message (truncated):
I have a duplicate `return` at line 1047. Let me fix that and apply the real fix in one edit.
</previous_attempt>
```

## 冻结后的改动

没有。canary 运行时代码等于 tag `a6-retry-freeze`（`0cbc63d`）。本 CHECKPOINT 只新增文档。

## 下一步

A6-3（剩余 314 个槽位）等审计。续跑时 canary 的 4 个槽位按已完成处理，不重跑。
