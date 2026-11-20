# EvoAgentBench code_implementation · ReasoningBank 小批量对照

原报告记录的是 Pi 1.5.0 + Qwen3.5-Plus 在官方训练划分上的 Vanilla 基线及 PowerShell 环境诊断。首批 5/5，扩展 20/20。此补充新增独立测试划分上的对照入口。

## 实验方法

1. 使用固定版本的 LiveCodeBench release_v6 与 EvoAgentBench 官方 182/86 划分。按发布文件顺序，从官方 test 中预选 easy、medium、hard 各一题，冻结题号与数据哈希。
2. 从五道训练题的已评分轨迹提炼可迁移的记忆。保存标题、适用条件、具体推理步骤、训练来源和训练文件哈希。提炼输入只允许 train 任务。现有初轮五题均解对，其中三题出现并修复了工具错误。可从这些轨迹提炼解题经验和工具错误反思。
3. 对每道测试题，以题面检索冻结记忆库。小批量实现使用 TF-IDF 余弦相似度，最多取一条，零相似度时不注入。提示只包含记忆正文。两组复用相同题面、模型、工具、环境说明、超时和官方判题器。每题、每组一次。测试期间不写回记忆库。
4. 记录每题通过状态、官方测试组、耗时、Token、工具错误、检索项和原始结果哈希。只在所有配对都有有效试验时计算通过率差。三题试跑只用于验证流程与初步观察。

该实现按 EvoAgentBench 的离线协议改造了 ReasoningBank。使用官方判题结果标注训练结局，并用稀疏检索，避免新增嵌入模型依赖。论文的 scaffold、模型和全量试验设置另见论文。此处是课程用 Pi 适配与三题试跑。

- [EvoAgentBench 论文与离线协议](https://arxiv.org/html/2607.05202v1)
- [ReasoningBank 原论文](https://arxiv.org/abs/2509.25140)
- [ReasoningBank 作者代码](https://github.com/google-research/reasoning-bank)
- [官方数据划分](https://github.com/EverMind-AI/EvoAgentBench/blob/main/benchmark/data/splits/README.md)

## 复现

先按 [基线 README](README.md) 准备 Windows 的 Pi、Python 和 Docker 判题镜像。以已有的训练基线输出目录作为 `$training`，目录下应包含逐题 `result.json` 和 `session.jsonl`。以下命令从 `baseline-code` 运行。

```powershell
python -X utf8 run_reasoning_bank.py select
python -X utf8 run_reasoning_bank.py distill --train-results "$training" --review-only
python -X utf8 run_reasoning_bank.py distill --train-results "$training"
python -X utf8 run_reasoning_bank.py evaluate
python -X utf8 run_reasoning_bank.py report
```

提炼预览与运行产物保存在 `runs/reasoningbank-pilot/`。可在当前 PowerShell 会话中配置 Thingo 凭据。提炼调用发送训练回答和工具轨迹片段及判题摘要。评测调用发送公开题面，并在记忆组附带检索记忆。仓库保留代码、方案和可分享的汇总，完整轨迹与题目数据存于本地运行目录。使用 `--pi-command` 指定 Pi 启动器，使用 `--lcb-repo` 复用已检出到固定版本的判题器。

## 验证状态

| 项目 | 状态 |
|---|---|
| 官方训练/测试隔离、记忆检索与注入、未完成配对汇总 | 代码测试通过 |
| 训练轨迹提炼输入 | 五道训练题的输入已在本地生成 |
| 独立测试题目 | 已冻结 abc319_c、abc320_a、abc324_f，见 [题号与数据哈希](results/reasoningbank-selection.json) |
| Vanilla 与 ReasoningBank 实测对照 | 等待运行，暂缺成绩 |
| RSI-Flow 中验证 skills | 等待原项目依赖恢复及实际集成验证 |

```powershell
python -X utf8 -m pytest test_pi_adapter.py test_reasoning_bank.py -q
```
