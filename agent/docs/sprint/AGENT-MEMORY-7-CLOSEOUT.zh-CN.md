# coding-agent 收尾计划

日期：2026-09-29。执行者：挂在 `D:\crq\src\coding-agent` 的 Cursor agent。
配套：`D:\crq\src\coding-harness\docs\sprint\HARNESS-SPRINT-7-CLOSEOUT.zh-CN.md`。
大纲：`docs/sprint/A5-FINAL-REPORT-OUTLINE.zh-CN.md`（审计已写好，本轮按它成稿，不改结构、不改结论）。

## 0. 等 harness

**等 harness 写出 `docs/sprint/CHECKPOINT-7.md`，并写明"清单和案例数据已就绪"之后再开始第 1 步。** 第 0 步可以先做。

需要用到的 harness 文件（只读）：

- `docs/sprint/A5-MAIN-INVENTORY.md`
- `docs/sprint/A5-CASE-DATA.md`
- `docs/sprint/CHECKPOINT-6.md`
- `docs/sprint/A5-MAIN-FREEZE.md`
- `docs/PROJECT-HISTORY.zh-CN.md`

## 1. 本轮规则

1. 不调用模型。花费上限 0。
2. 不改 `scripts/analyze_a5_main.py`、卡片 jsonl、检索插件、预注册追加项。看到数据之后不改分析。
3. 不改 coding-harness 仓库。
4. 不删除旧证据（v2–v6 卡片、CHECKPOINT、RESULTS 全部保留）。
5. 小步提交。不 force push。
6. 最终报告里的数字只能来自大纲第 1 条列出的那些文件。对不上就停下，不要自己重算一套。
7. 不能写"记忆无效"。按预注册写"没有检出大于 X 个百分点的效应"。
8. 不贴 gold patch、test patch、F2P/P2P 原文。

进度追加到 `docs/sprint/PROGRESS.md`，标题用"第七轮 第 N 步"。完成后写进 `CHECKPOINT-7.md`，停下等审计。

## 2. 分步计划

### 第 0 步：入口和指针（现在就可以做）

1. 新建 `docs/PROJECT-HISTORY.zh-CN.md`，不要复制全文。写大约半页：本仓库是记忆侧；6 月到 7 月的 RepoSkillAgent 历程见 `docs/project-chronology.zh-CN.md`；9 月以后两个仓库合在一起的思路、问题和解决见 `D:\crq\src\coding-harness\docs\PROJECT-HISTORY.zh-CN.md`；A5-main 预注册结果见 `docs/sprint/A5-MAIN-RESULTS.zh-CN.md`；最终报告见 `docs/A5-FINAL-REPORT.zh-CN.md`（第 1 步才有）。
2. 在根目录 `README.md` 的 A5 相关段落上方加一小节「A5-main（2026-09）」：B0 对 B2，56 题，B0 解出率 68.5%，没有检出大于 13.1 个百分点的效应。链接到 RESULTS、最终报告（第 1 步之后会存在）、历程指针。旧的 240 矩阵、pilot、L5/L2 +9.4pp 叙述都保留，标明那是早期自建题集或未执行的计划。

提交后可以先停下，也可以直接等 harness 的 CHECKPOINT-7 再做第 1 步。

### 第 1 步：写最终报告

成稿路径：`docs/A5-FINAL-REPORT.zh-CN.md`。

严格按 `docs/sprint/A5-FINAL-REPORT-OUTLINE.zh-CN.md`：

- 标"草稿"的段落把要点写成连贯正文，可以改措辞，**不能改结论、不能改数字、不能删机制解释**。
- 标"填入"的段落从指定文件抄数字，注明来源。
- 案例分析以 harness `A5-CASE-DATA.md` 为准。大纲里若与数据文件有出入（例如重合组里"7 道"还是"8 道 d_t=0"），**以数据文件为准，并在报告里按数据文件写**。
- 附录 A 的复现命令从两边 PROGRESS / README 收集，写到能让人按 tag 找到输入文件为止，不必写成可一键重跑 392 次的脚本。
- 附录 B、C 从 `A5-MAIN-INVENTORY.md` 填。
- 附录 D 从 `A5-MAIN-RESULTS.zh-CN.md` 复制逐题表。
- 附录 E、F 用链接，不把案例数据和历程全文再贴一遍。

篇幅大约 8–12 页。提交这一步。

### 第 2 步：CHECKPOINT 与停下

`docs/sprint/CHECKPOINT-7.md` 写明：

- 最终报告路径和提交；
- 引用的清单 sha、案例数据核对行、RESULTS 未改；
- 测试：`python -m pytest -q`（本仓库）。如果本机没有独立 `.venv`，用 harness 的 `.venv` 并把本仓库放进 `PYTHONPATH`，在 CHECKPOINT 里写清命令。

**不要做同题重试、不要改卡片、不要新开实验。** 停下等审计。

## 3. 大纲和讨论已经写在哪里

最终报告第 7、8、10 节对应的内容，审计已经写在大纲里，不要换成另一套解释：

- 卡片很少指对文件（9/51），agent 几乎不按卡片走（5/153 打开、0 次最终改在那里）；
- 9673 / 9258 / 13964 三个案例；未注入题平均 d_t −0.20，说明 ±1/3 是噪声；
- 这种记忆无效的原因是任务不同质、记的是具体修法、瓶颈在细节、被动注入、天花板；
- 主流记忆（项目规则、会话记忆、同任务反思、跨任务策略、技能库）有效的前提，本场景基本不满足；
- 后续若做，优先同题重试记忆；本项目不做。
