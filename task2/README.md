# 任务二 · RSI-Flow 循环结构

基于 [ymxiong/rsi-flow 的 dev_rsi](https://github.com/ymxiong/rsi-flow/tree/93cc223de5bc8f0510801796a46a8ae391725be9)，新增 `while` 节点。节点先判断条件，满足时执行同步子流程，并把声明的结果写回下一轮变量。条件为假时退出，到达上限且条件仍为真时报错。

| 演示输入 | 验收结果 |
|---|---|
| `count=0, stopAt=3` | 嵌套子流程执行三次，退出后输出 `count=3` |
| `count=5, stopAt=3` | 循环体执行零次，退出后输出 `count=5` |
| `count=0, stopAt=4`，上限为 3 | 执行三次后报出循环上限，之后可继续运行其他流程 |

在 Docker Java 8/Maven 环境中，5 项新增测试和 8 项已有顺序、分支、嵌套及异步流程回归全部通过。原构建的私服依赖由独立验证副本处理，真实定时调度和完整上游构建仍待可用依赖。

- [设计说明、讨论要点和验收记录](design-and-validation.txt)
- [循环实现与测试补丁](rsi-flow-while.patch)
- [13 项实测用例清单](test-results.json)
- [隔离验证脚本](verify.py)

在对应的 RSI-Flow 提交上运行 `git apply --check` 检查补丁，再运行 `git apply` 应用它。验证脚本支持通过 `--source` 指定改好后的源码、通过 `--easyfile` 指定作者公开的 easyfile 0.0.3 源码。用 `python verify.py --help` 查看其他选项。

## 补充验证 · 在 RSI-Flow 中回放 ReasoningBank skills

使用任务一冻结的 8 条记忆和 3 道保留测试题。Python 复用任务一的 TF-IDF 向量化，RSI-Flow 用新增 `while` 控制任务游标。每轮真正执行三个 Java 节点。

1. `RETRIEVE` 计算余弦相似度并选择 top-1。
2. `INJECT` 将记忆拼入基线提示并计算 SHA-256。
3. `RECORD` 保存检索分数、提示哈希和既有判题结果，推进游标。

测试核对三个 top-1 索引、相似度、重建提示哈希和既有分数。流程运行在禁网 Docker 中，模型调用次数为 0。这里的通过率沿用任务一实测分数，验证范围是工作流、检索和注入的可复现性。

实测三道题均命中与任务一相同的 top-1 记忆，三个重建提示的 SHA-256 均与原会话一致。包含回放的测试批次共 14 项，0 失败、0 错误、0 跳过。

- [离线回放补丁](rsi-flow-skills-replay.patch)
- [逐题回放记录](skill-replay-results.json)
- [从已完成试验生成本地回放输入](prepare-skill-replay.py)

先在 RSI-Flow 源码依次应用循环补丁和离线回放补丁。从本交付仓库根目录运行下列命令，把三个参数路径替换为本机路径。试验目录需有任务一完整的 `bank.json`、测试选择、评测计划、逐题 `result.json` 和 `session.jsonl`。

```powershell
python -X utf8 task2/prepare-skill-replay.py --run-dir PATH_TO_PILOT_RUN --output work/skill-fixture.json
python -X utf8 task2/verify.py --source PATH_TO_RSI_FLOW --easyfile PATH_TO_EASYFILE --skill-fixture work/skill-fixture.json
```

回放输入包含提示与冻结记忆，建议保存在本地。逐题记录仅包含任务号、哈希、相似度和既有分数。
