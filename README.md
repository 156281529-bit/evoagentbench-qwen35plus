# evoagentbench-qwen35plus
Qwen3.5-Plus + Pi 1.5.0 on EvoAgentBench: baseline reproduction and failure analysis.

本次提交整理 LiveCodeBench `code_generation_lite release_v6` 的基线实验，使用 EvoAgentBench 论文 train 划分。实验日期为 2026-11-20。

## 提交材料

- [实验报告 PDF](reports/baseline-report.pdf)
- [可编辑实验报告 Word](reports/baseline-report.docx)
- [基线代码与完整复现步骤](baseline-code/README.md)
- [逐题实验结果和汇总指标](baseline-code/results/metrics.json)
- [原始运行证据的 SHA256 清单](baseline-code/results/evidence-hashes.json)
- [五类问题的人工分析](baseline-code/data/tasks-metadata.json)
- [ReasoningBank 接入、独立测试对照与当前进度](baseline-code/REASONINGBANK.md)

## 第一个实验表

| 配置 | 通过题目 | 测试组 | Agent 总秒数 | 总 Tokens | 工具错误 / 调用 |
|---|---:|---:|---:|---:|---:|
| v1 初始环境 | 5/5 | 68/68 | 222.1 | 130996 | 3/14 |
| v2 PowerShell 环境说明 | 5/5 | 68/68 | 223.8 | 158683 | 0/18 |

五类问题依次为：整除与最小代价、模不变量与博弈、数位动态规划、前后缀去重统计、栈与字符串消除。对应题目为 `1883_C`、`1899_A`、`2757`、`2777`、`2800`。

初轮有 3/5 道题发生可恢复工具错误，根因是 PowerShell 的 `<` 输入重定向和 `&&` 兼容性。模型修复后仍全部通过，因此报告分别统计答题通过率和工具错误率。v2 在任务提示中附加固定环境说明，复核本批错误降至 0/18；Tokens 增加约 21.1%，不能声称效率提升。

v2 扩展批次为 20/20 题通过、281/281 测试组通过、0/60 次工具调用错误、845.4 秒、516693 Tokens。20 题包含前述 5 道 v2 题目。本批是小样本基线与环境适配诊断，不能代表全量基准表现；v1/v2 不是自进化前后对照。

在官方 test 划分另选三题完成 Vanilla 与 ReasoningBank 同题对照，两组均为 1/3，通过率差为 0 个百分点。五道训练轨迹生成 8 条冻结记忆。详见 [ReasoningBank 实测结果与失败诊断](baseline-code/REASONINGBANK.md#2026-11-20-实测结果)。

## 复现入口

在 Windows 主机准备 Python 3.12、Git、Node.js 和 Docker Desktop（Linux 容器），并在私有 Pi 配置中配置 `thingo/qwen3.5-plus`。进入代码目录后执行：

```powershell
cd baseline-code
python -m pip install -r requirements.txt
npm install -g @earendil-works/pi-coding-agent@1.5.0
python -X utf8 prepare.py
python -X utf8 run_experiment.py --variant v2
```

固定设置为每题一次、并发 1、重试 0、Agent 上限 600 秒。数据及判题器按固定版本下载；原始测试数据与密钥不包含在仓库中。依赖、参数和 v1 运行命令详见[代码说明](baseline-code/README.md)。完整原始轨迹随本地提交材料保存。

## 验证与来源

代码包保留上游许可、固定版本信息、模型原始提交和证据哈希。11 项适配器测试覆盖独立工作空间、中文 stdin、Windows npm 启动、超时、Token 统计和重试策略。详见 [LICENSE](baseline-code/LICENSE)、[第三方声明](baseline-code/THIRD_PARTY_NOTICES.md) 和 [sources.json](baseline-code/sources.json)。

本仓库当前为私有，查看者需要仓库访问权限。
