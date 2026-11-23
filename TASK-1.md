# 任务一 · EvoAgentBench 数据集与基线实验

我负责 EvoAgentBench 的代码实现方向。题目和判题用例来自 LiveCodeBench V6，EvoAgentBench 根据题目共享的解题能力组织训练与测试。本方向的官方划分包含 182 道训练题和 86 道测试题。本次用 Qwen3.5-Plus 和 Pi 1.5.0 评测其中的子集，每题尝试一次，以官方判题器给出的 Pass@1 衡量题目通过率。

## 做了什么

- 跑通无记忆基线，手工归纳了整除与最小代价、模运算与博弈、数位动态规划、前后缀去重统计、栈与字符串消除五类题型。补充 Windows PowerShell 环境说明后，首批五题的工具错误从 3 次降到 0 次。
- 从 5 道训练题的运行轨迹提炼并冻结 8 条 ReasoningBank 记忆。在官方测试划分中选三个难度各一道题。两组使用相同题目、模型和判题器，记忆组额外检索并加入一条相关经验。

## 结果

| 实验 | 结果 | 记录 |
|---|---|---|
| 首批训练基线 | v1 和 v2 均通过 5/5 道题 | [基线报告 PDF](https://github.com/156281529-bit/evoagentbench-qwen35plus/blob/1da29f9d461379ca2e03c3c876efa54d98ade090/reports/baseline-report.pdf) |
| 扩展训练基线 | 20/20 道题、281/281 个测试组通过，含首批 v2 五题 | [逐题指标](https://github.com/156281529-bit/evoagentbench-qwen35plus/blob/1da29f9d461379ca2e03c3c876efa54d98ade090/baseline-code/results/metrics.json) |
| 三题独立测试对照 | Vanilla 与 ReasoningBank 均通过 1/3 道题，迁移增益为 0 个百分点 | [逐题对照记录](https://github.com/156281529-bit/evoagentbench-qwen35plus/blob/1da29f9d461379ca2e03c3c876efa54d98ade090/baseline-code/results/reasoningbank-comparison.json) |
| 新增九题独立测试对照 | Vanilla 通过 7 题、判题失败 2 题。ReasoningBank 通过 7 题、判题失败 1 题、未判题 1 题 | [逐题对照及完整性说明](baseline-code/REASONINGBANK.md#九题扩样) |

三题试跑验证了检索和提示注入流程，样本量有限。两道小数输出题的首个失败记录涉及判题器的精确比较，表中保留原判分。 [方法、复现步骤与判题诊断](https://github.com/156281529-bit/evoagentbench-qwen35plus/blob/1da29f9d461379ca2e03c3c876efa54d98ade090/baseline-code/REASONINGBANK.md)

[仓库首页](README.md) · [任务二说明](TASK-2.md) · [提交 PR](https://github.com/156281529-bit/evoagentbench-qwen35plus/pull/1)
