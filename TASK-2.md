# 任务二 · RSI-Flow 循环结构设计与实现

我在 RSI-Flow 已有的顺序、分支和嵌套流程上加入了 `while` 节点。节点每轮先检查条件，成立时运行同步子流程，再把声明的结果写回给下一轮。达到迭代上限后会再检查一次，条件已为假就正常结束，仍为真则报超限。

## 循环验收

| 场景 | 结果 |
|---|---|
| 从 0 数到 3，上限 3 轮 | 执行三轮，正常结束 |
| 从 5 开始，循环条件是小于 3 | 执行零轮，保留计数 5 |
| 从 0 数到 4，上限 3 轮 | 三轮后报超限，之后仍可运行其他流程 |

在 Java 8 / Maven 的隔离环境中，5 项新增循环测试和 8 项已有流程回归全部通过。隔离构建处理了上游私服依赖，验证范围涵盖循环及回归用例。 [循环补丁](https://github.com/156281529-bit/evoagentbench-qwen35plus/blob/1da29f9d461379ca2e03c3c876efa54d98ade090/task2/rsi-flow-while.patch) · [13 项测试记录](https://github.com/156281529-bit/evoagentbench-qwen35plus/blob/1da29f9d461379ca2e03c3c876efa54d98ade090/task2/test-results.json)

## 用任务一的记忆做离线回放

循环每轮处理一道题，从任务一冻结的 8 条记忆中选出最相近的一条，重建提示并记录 SHA-256。三道题的检索结果和提示哈希均与任务一一致。回放复用原判题记录，模型调用为 0。加入回放后，隔离测试共 14 项，全部通过。 [回放补丁](https://github.com/156281529-bit/evoagentbench-qwen35plus/blob/1da29f9d461379ca2e03c3c876efa54d98ade090/task2/rsi-flow-skills-replay.patch) · [逐题回放与测试结果](https://github.com/156281529-bit/evoagentbench-qwen35plus/blob/1da29f9d461379ca2e03c3c876efa54d98ade090/task2/skill-replay-results.json)

[设计、验收与复现步骤](https://github.com/156281529-bit/evoagentbench-qwen35plus/blob/1da29f9d461379ca2e03c3c876efa54d98ade090/task2/README.md) · [仓库首页](README.md) · [任务一说明](TASK-1.md) · [提交 PR](https://github.com/156281529-bit/evoagentbench-qwen35plus/pull/1)
