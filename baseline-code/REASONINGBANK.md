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

提炼预览与运行产物保存在 `runs/reasoningbank-pilot/`。可在当前 PowerShell 会话中配置 Thingo 凭据。提炼调用发送训练回答和工具轨迹片段及判题摘要。程序先遮盖本机用户路径和常见令牌格式，运行前可通过 `--review-only` 在本地检查完整请求。评测调用发送公开题面，并在记忆组附带检索记忆。仓库保留代码、方案和可分享的汇总，完整轨迹与题目数据存于本地运行目录。使用 `--pi-command` 指定 Pi 启动器，使用 `--lcb-repo` 复用已检出到固定版本的判题器。

## 验证状态

| 项目 | 状态 |
|---|---|
| 官方训练/测试隔离、记忆检索与注入、未完成配对汇总 | 代码测试通过 |
| 训练轨迹提炼 | 五道训练题的轨迹生成并冻结 8 条记忆 |
| 独立测试题目 | 已冻结 abc319_c、abc320_a、abc324_f，见 [题号与数据哈希](results/reasoningbank-selection.json) |
| Vanilla 与 ReasoningBank 实测对照 | 六次评测全部完成，三组同题配对均有效 |
| RSI-Flow 中验证 skills | 等待原项目依赖恢复及实际集成验证 |

## 2026-11-20 实测结果

| 组别 | Pass@1 | 测试阶段 Agent 耗时 | 测试阶段总 Token | 工具错误 / 调用 |
|---|---:|---:|---:|---:|
| Vanilla | 1/3（33.3%） | 187.4 秒 | 131,495 | 0/15 |
| ReasoningBank | 1/3（33.3%） | 167.6 秒 | 132,098 | 0/15 |

两组同样只通过了 `abc320_a`，通过率差为 0 个百分点。记忆组的测试阶段 Agent 耗时少 19.8 秒，Token 多 603。记忆提炼另外消耗 23.8 秒和 12,178 Token。单次三题的耗时差不足以判断稳定的效率收益。[逐题指标与文件哈希](results/reasoningbank-comparison.json)

经核对六份会话，三组原始题面逐字一致，记忆组提示追加了冻结库中的检索结果。三题都命中同一条 `Sample Case Pattern Verification`，相似度依次为 0.288784、0.309085、0.231115。这次试跑验证了注入流程，检索结果的区分度有待更大的测试集检验。

| 题目 | Vanilla | ReasoningBank | 判题记录 |
|---|---:|---:|---|
| abc319_c（中等） | 未通过，0/1 组 | 未通过，0/1 组 | 两组首先遇到同一组小数比较差异，绝对差约 6.67×10⁻¹⁷ |
| abc320_a（简单） | 通过，9/9 组 | 通过，9/9 组 | 全部测试组通过 |
| abc324_f（困难） | 未通过，6/7 组 | 未通过，2/3 组 | 各自首个失败组的绝对差约 4.20×10⁻¹³、3.00×10⁻¹⁶ |

固定版本判题器逐行比较字符串或 `Decimal` 精确值，遇到首个不匹配即提前停止。表中的组数只统计实际执行到的组。四条首个失败记录的差值均落在 AtCoder 原题给出的容差以内。主表保留原判分，后续未执行到的用例没有复判。[固定版本判题逻辑](https://github.com/LiveCodeBench/LiveCodeBench/blob/28fef95ea8c9f7a547c8329f2cd3d32b92c1fa24/lcb_runner/evaluation/testing_util.py#L389-L424) · [abc319_c 原题](https://atcoder.jp/contests/abc319/tasks/abc319_c?lang=en) · [abc324_f 原题](https://atcoder.jp/contests/abc324/tasks/abc324_f?lang=en)

```powershell
python -X utf8 -m pytest test_pi_adapter.py test_reasoning_bank.py -q
```
