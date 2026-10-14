# SOLID D1 污染方法论收尾（文件定位探针）

日期：2026-06-26
执行文档：`docs/SOLID-D1-CONTAMINATION-EXECUTION.zh-CN.md`
产出：`scripts/contamination_probe.py`、`reports/contamination_probe.md`（+ `.json`）、`docs/CONTAMINATION-NOTES.zh-CN.md`

---

## 1) 目标与结果

把"数据污染"从风险点做成**可量化、可复现**的方法论组件：复刻 *The SWE-Bench Illusion* 的无上下文文件定位探针，量化本项目 10 个 SWE-bench Lite 实例的 instance-level 记忆程度。

**稳健结论（5 次重复采样）**：本数据集存在**强 instance-level 记忆污染**。

| 指标 | 值 |
|------|----|
| 池化 exact 率 | **54.2%**（26/48 次） |
| basename-or-better | **68.8%** |
| 多数票定位实例（≥basename） | **7/10** |
| 逐轮 exact 波动 | 50%–60% |
| 总成本 | ~5.3 万 token（≈零成本） |

---

## 2) 实现：`scripts/contamination_probe.py`

- gold 文件从每个 `fixture_dir/.oracle/` 唯一 `.py` **离线实取**（不联网、不编造）。
- 只喂清洗后的 issue 文本 + repo 名（**不给文件树/代码**），`LLMClient` 单轮 `chat`。
- 三级判定：`exact` / `basename`（文件名对、路径前缀错）/ `wrong`。
- 输出 `reports/contamination_probe.md` + `.json`，含逐实例命中频率、distinct 预测分布、与 REWORK 双峰通过率的交叉印证、解读段。

### 实验暴露并修复的两个测量陷阱（方法学亮点）

1. **推理模型截断**：`deepseek-v4-pro` 先消耗 reasoning 预算再吐 `content`；初版 `max_tokens=256` 致 6/10 答案被截断、误记为"定位失败"。
   修复：`--max-tokens`（默认提到 2048）+ 把 `truncated`（`finish_reason=length` 或预算耗尽）**单列、不计入分母**。
2. **temp=0 非确定性**：同 prompt 两次给出不同答案（推理链长度随机，长推理时会绕错），单次结果在 50%–78% 间晃。
   修复：`--repeats N`（每实例重复采样，默认建议 ≥5）、按命中频率聚合、报告逐轮波动以暴露非确定性。
3. 附带：`--from-json` 支持从缓存原始数据**零成本重渲染**报告（改渲染逻辑无需重付 LLM）。

---

## 3) 关键发现（交叉印证）

- **双峰自洽**：恒过任务 `24213`（exact 5/5）、`flask-4992`（basename 5/5，知道是 `config.py` 只差 `src/` 前缀）都强定位，支撑"记得的就过、没记的就不会"。
- **定位 ≠ 会解**：`23117`、`24909` 定位 exact 5/5 但 baseline 恒 0/5——模型知道改哪个文件却写不出修复。说明"恒 0"一批**不全是污染缺失，而含难度/scaffold 天花板**，区分了"污染压缩区分度"与"真·能力失败"。
- **相对干净的任务**：`23262`、`23191`、`requests-3362` 定位一致失败，相对未被记忆。

---

## 4) 数字修订说明

- 首次单跑（`max_tokens=256`）报"exact 40%"，因 6/10 截断**作废**。
- ROADMAP 中早先填入的"exact 40%"已更正为稳健的"池化 exact 54.2% / 7-of-10 定位"。

---

## 5) 验证

- 探针运行：`python scripts/contamination_probe.py --dataset datasets/swebench_lite_tasks.json --config configs/baseline.yaml --out reports/contamination_probe.md --repeats 5`
- 重渲染：`python scripts/contamination_probe.py --from-json reports/contamination_probe.json --out reports/contamination_probe.md`
- 未触碰 `configs/`、scaffold、全量 `run_eval`；未开 `run_command`。

---

## 6) 边界 / 未做（移交下一步）

- **防作弊（组 0）仍未做**：当前 `write_file` 已启用 + 判定在 workspace 跑 pytest = 真实作弊面（agent 可改测试假通过）。属代码改动，待用户单独放行。
- 外部对照探针（收录 vs 未收录 repo 的 76% vs 53% 差值）未做，列入 NOTES 未来工作。
- SWE-bench-Live / Docker 治本路径列入未来工作，非主线。
