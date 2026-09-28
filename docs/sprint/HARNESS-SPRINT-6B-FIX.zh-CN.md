# HARNESS R6 修订 2：低版本 Python 工具修复、Docker 错误归类、B0 重新开始

日期：2026-09-28。依据：CHECKPOINT-6a（B0 停止）审计。

## 审计结论

- **工具 bug 是运行时缺陷，不是题目难度。**
  - 容器内工具用了 `Path.is_relative_to`（Python 3.9 才有），在 3.6/3.8 镜像里 5 个结构化工具每次调用都失败。受影响的是 17 道题。
  - 已完成的 25 次运行里有 22 次受影响，这些结果和修复后的运行不可比。
- **dev 侧不受影响。** dev 的 14 个 clean image 都是 Python 3.9.19，dev 运行里没有这个报错，所以 v5 卡片、dev b0-v2 结果和 R5 的 B2 冒烟都有效。问题出在 R5 按 SWE-bench 规格重建 pool 镜像时，Python 版本变成了 3.6/3.8。
- **Docker 控制通道错误属于基础设施问题。** 这类错误（snapshot 失败、grader 在测试开始前超时）不能算作"未解出"或"改动丢失"。
- **已有的 25 次 B0 运行全部作废，B0 在修订 2 上从头开始。**
  - 作废规则只看"跑在修复之前的代码上"这一环境条件，和结果无关。其中有 2 次解出（django-13964 r2、sklearn-13142 r1），也一并作废。
  - 跑在 3.9 镜像上的 3 次运行虽然不受工具 bug 影响，也一起作废，这样整个实验都跑在同一份代码上。多花大约 1.7 元，换来口径统一。
  - 已花的 13.682 元记为作废开销，不计入实验。

执行顺序：G1 → G7，全部通过后不用停下，直接跑全量 B0，跑完后停在 CHECKPOINT-6a。

## G1 工具在 Python 3.6+ 上可用

1. 把 `is_relative_to` 换成 3.6 能用的写法（`relative_to` 加 `try/except ValueError`，或者 `os.path.commonpath`），语义不能变：路径越界照样拒绝。
2. 找出所有会在容器内用镜像 Python 执行的代码（`src/tools/` 里通过 docker exec 或 stdin 送进容器的脚本，以及 observer 或插件等），逐个检查 3.7 及以上才有的写法，全部改掉：
   - 语法：`:=`、`dict | dict`；
   - 方法：`str.removeprefix/removesuffix`、`functools.cache`；
   - 运行时生效的 `list[str]` 注解、`from __future__ import annotations`；
   - `subprocess.run(capture_output=/text=)`、`dataclasses`；
   - 其他 3.7 及以上才有的 API。
3. 在 `python:3.6.15-slim-buster` 里对上一步找出的全部容器内代码执行 `py_compile`，作为测试的一部分（可以用 docker 跑，没有 docker 时 skip，但本轮必须实际跑过一次）。

## G2 工具冒烟进入预检

`--preflight` 对每道合格题新增一步，零模型：

1. 在该题的 clean image 里按正式运行的方式启动 backend。
2. 依次调用 `read_file`、`list_dir`、`search_code`、`search_replace`、`edit_file`、`run_command` 各一次，使用固定、无害的参数：读取仓库里一个已知文件，在 `/workspace` 下的临时文件上执行编辑。
3. 每个调用都要求正常返回，不能有工具实现层的异常（traceback、`AttributeError`、`ImportError`、`SyntaxError`、`TypeError` 等）。
4. 冒烟改动不导出，也不进入任何评测。

**必须 56/56 通过。** 结果写进 `preflight.json`，并按镜像 Python 版本（3.6/3.8/3.9/3.11）汇总。

## G3 Docker 控制错误归类与重试

1. Docker 控制调用（snapshot、exec 启动、容器创建或销毁、grader 启动）遇到 `DockerUnavailable`、`ConnectionResetError`、连接超时时，自动重试 3 次，间隔 2/5/10 秒。每次重试都记录下来。
2. 重试之后仍然失败的，这次运行记为 `infra_error`，走现有的重跑规则：
   - 候选改动 snapshot 失败，一律 `infra_error`，**不允许按空改动评测**；
   - grader 在测试开始执行之前失败或超时（`execution_status` 为空）。

   测试已经开始执行后出现的超时，仍然按正常失败处理。
3. 加测试。

## G4 工具异常作为停止条件

1. summary 里新增 `harness_tool_errors` 计数，统计工具实现层的异常。文件不存在、参数不合法这类正常的工具结果不算在内。
2. runner 的停止条件新增：任何一次运行的 `harness_tool_errors > 0`，就停止启动新运行。
3. 第 1 步的 canary 检查项新增"`harness_tool_errors == 0`"。

## G5 并发与预算

1. `PARALLEL` 改为 3。B0 和 B2 相同。
2. 已完成运行的平均花费约 0.55 元，336 次约 185 元，原来的上限不够。新上限：
   - B0 软上限 110 元；
   - `TOTAL_CAP` 220 元。只统计 `runs/a5-main/` 下的花费，作废的运行不计入。

## G6 作废已有运行

1. 把 `runs/a5-main/` 下全部 25 次运行，连同 `b0-report.json`，整个移到 `runs/a5-main-void/r1-tool-py36/`，只移动，不删除。在该目录下写一个 `README.md`，内容包括：
   - 作废原因；
   - 每次运行的 id、所在镜像的 Python 版本、`harness_tool_errors` 数、是否解出、花费；
   - 作废规则："修订 2 之前的全部 B0 运行，不论结果"。
2. `runs/a5-main/` 清空之后，B0 从头开始。

## G7 冻结修订 2

1. 在 `A5-MAIN-FREEZE.md` 里新增"修订 2"一节，写明：
   - G1–G6 的提交；
   - 作废规则和作废的 25 次运行；
   - `PARALLEL`、预算的变化；
   - 预检结果（含工具冒烟 56/56）。
2. 全量测试通过后打 tag `a5-main-freeze-r2`，旧 tag 保留。

## 之后（不用停下）

1. **canary 按 Python 版本各取一道。** 每个镜像版本取按 `created_at` 排序后的中位题：3.6 一道，3.8 一道，3.9 一道，3.11 一道（没有的版本跳过）。各跑一次真实 B0 r1。

   检查项：原第 1 步的全部检查项，加上 `harness_tool_errors == 0`，并且没有因 Docker 控制错误导致的 `infra_error`。
2. 通过后跑全量 B0。
3. 以下情况停下，写 CHECKPOINT-6a：
   - 停止条件触发；
   - 预检或 canary 不通过；
   - B0 跑完。

   CHECKPOINT-6a 里要额外报告：Docker 重试的次数和发生时间，`harness_tool_errors` 的总数（应为 0）。

不要开始 B2。coding-agent 侧不需要任何操作，dev 卡片不受影响。
