# 补 sphinx 记忆源

本轮没有本地 sphinx 历史轨迹，也没有带 `/opt/repo` 的 sphinx baseline 镜像。4 道 sphinx pilot 题因此没有记忆卡。这里只定规则。本轮不批量做，也没有新跑一道 sphinx 源题：构建镜像不在已有证据里，现场重建会超出本轮已经冻结的范围。

## 数据

用 SWE-bench 官方数据集，版本 `princeton-nlp/SWE-bench`，Hugging Face 上的 `test` split（或同一提交的官方 json）。下载：

`datasets.load_dataset("princeton-nlp/SWE-bench", split="test")`

每行只用 `instance_id`、`repo`、`created_at`、`base_commit`。不用 `patch`、`test_patch`、`FAIL_TO_PASS`、`PASS_TO_PASS` 来选题。

## 选题

1. `repo` 必须是 `sphinx-doc/sphinx`。
2. `created_at` 早于本仓库 4 道 sphinx pilot 题里最早的那一道。pilot 题是 `sphinx-doc__sphinx-8595`、`8713`、`8721`、`10451`。
3. 不在 `scripts/run_swe_task.py` 的 `HOLDOUT` 里，也不在 20 道 pilot 里。
4. 排序键固定为 `created_at` 降序，取最近的 1 道做试跑。不使用随机，也不看 gold 或测试。
5. 批量扩充留到第四轮，本文件不指定具体 instance id，避免在写规则时先看过 gold。

## 构建

源码包和镜像沿用 `scripts/preflight_a5_repo_baseline.py` 里 sphinx-doc 的依赖配置。流程与现有 baseline 相同：按 `base_commit` 打包，构建带 `/opt/repo` 的镜像，再用 `ImageGrader` 做空改动和 gold 校准。校准不过的题不进入记忆源。

## 花费

试跑 1 道：构建镜像不花模型钱；校准 0 CNY；1 次 B0 按第 5 步的平均约 0.39 CNY，单次上限 1 CNY。第四轮若做 N 道，按同样的单次均值估算，并单独设上限。
