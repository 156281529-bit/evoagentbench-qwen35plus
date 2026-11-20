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
