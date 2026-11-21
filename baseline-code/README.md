# LiveCodeBench 五类问题的 Pi Qwen 基线

本仓库对应 2026-11-20 的课程实验整理报告。分析对象为 LiveCodeBench `code_generation_lite` 的五道题，使用 EvoAgentBench 的论文 train 划分。五类分别是整除与最小代价、模不变量与博弈、数位动态规划、前后缀去重统计、栈与字符串消除。

## 已记录的实验

| 配置 | 通过题目 | 测试组 | Agent总秒数 | 总Tokens | 工具错误/调用 |
|---|---:|---:|---:|---:|---:|
| v1 初始环境 | 5/5 | 68/68 | 222.1 | 130996 | 3/14 |
| v2 PowerShell环境说明 | 5/5 | 68/68 | 223.8 | 158683 | 0/18 |

v2 的 20 题扩展验证：20/20 通过、281/281 测试组通过、工具错误 0/60、Agent总耗时845.4秒、总Tokens516693。扩展结果包含上述5道v2题目，不是额外20个独立样本。

这些是实际观测值，不是重跑保证。v2消除了本批观察到的工具语法错误，但Tokens增加，不能据此声称效率提升。v1/v2是环境适配对照，不是自进化对照。

## 环境

- Windows主机，Python 3.12，Git，Node.js，Pi `@earendil-works/pi-coding-agent@1.5.0`。
- Docker Desktop的Linux容器，用于原始LiveCodeBench Python判题器；容器Python为3.12。
- 已在用户私有Pi配置中设置 `thingo/qwen3.5-plus` 和有效API凭据。
- `THINGO_API_KEY` 只保存在运行终端的环境变量或Pi私有凭据配置中。仓库不包含凭据。

## 安装与数据准备

```powershell
python -m pip install -r requirements.txt
npm install -g @earendil-works/pi-coding-agent@1.5.0
python -X utf8 prepare.py
```

`prepare.py` 流式下载固定提交中的5条任务并校验SHA256，检出固定版本的LiveCodeBench源代码，再构建判题镜像。数据文件、公开/私有测试、依赖检出和新运行日志均被 `.gitignore` 排除。

也可以分步执行：

```powershell
python -X utf8 prepare.py --data-only
python -X utf8 prepare.py --judge-only
```

## 运行

先在安全终端配置模型密钥。不要将密钥作为命令参数，也不要粘贴到仓库或聊天。

```powershell
python -X utf8 run_experiment.py --variant v2 --prepare-only
python -X utf8 run_experiment.py --variant v2
python -X utf8 run_experiment.py --variant v1
```

Pi不在PATH时，用 `--pi-command` 指定 `pi.cmd` 或 `cli.js` 的路径。每个版本结果写入 `runs/v1` 或 `runs/v2`。重复执行会跳过已结束的试验；不会为了取得成功结果自动重试。要开展新的独立试验，请使用新的代码工作副本并记录试验编号。

固定设置：每题1次、并发1、重试0、Agent上限600秒、官方单组判题上限6秒、判题容器总上限240秒。v2只在原始任务提示后附加固定Windows PowerShell兼容性说明，避免不受支持的 `<` 和 `&&` 写法。

当前保存的是Windows主机配置。Linux容器仅承担判题；更换Agent运行操作系统应作为另一个harness版本单独记录。

## 文件说明

- `run_experiment.py`：可复现的5题v1/v2入口。
- `prepare.py`、`sources.json`：依赖和数据的固定版本及校验信息。
- `framework/src/agents/pi/pi.py`：新增Pi适配器。
- `framework/src/`：Apache-2.0许可的最小EvoAgentBench执行框架子集。
- `audit.py`：逐题分类完成状态、错答、超时、API错误、代码提取、判题异常和可恢复工具错误。
- `results/metrics.json`：报告中的实际实验数据；`results/evidence-hashes.json`：原始结果/会话/代码的SHA256。
- `results/environment.json`：实际运行环境的Python及主要依赖版本。
- `solutions/v1`、`solutions/v2`：模型提交给判题器的原始Python代码。
- `data/tasks-metadata.json`：五类问题的人工分析；算法类别不是上游自带标签。
- `data/paper-split.json`：论文train/test任务ID，182/86且不重叠。

原始会话和完整运行证据保存在本地提交材料的 `evidence/` 中，未将可能含有本机路径的完整轨迹上传到公共代码区。报告不改变或修正模型的原始提交。函数式任务由官方判题器提供统一导入和调用环境，单独执行某个提交文件不一定等价于官方判题。

## 验证

```powershell
python -m pip install -r requirements-dev.txt
python -X utf8 -m pytest test_pi_adapter.py -q
```

已运行11项适配器合同测试，覆盖独立工作空间、长中文stdin、Windows npm启动、超时、Token统计和重试策略；原项目完整测试33项通过。正式推理的单次结果会随模型采样和服务状态变化。

## 来源与许可

- EvoAgentBench：`948a17288782d5120778da16b4cf1cad9305d8b4`，Apache-2.0，保留 `LICENSE` 和 `THIRD_PARTY_NOTICES.md`。
- LiveCodeBench判题器：`28fef95ea8c9f7a547c8329f2cd3d32b92c1fa24`，作为外部依赖下载。
- 数据：LiveCodeBench `code_generation_lite` 的固定提交，详见 `sources.json`。不在此仓库重新分发原始测试数据。
- [LiveCodeBench项目](https://livecodebench.github.io/)
- [官方数据集](https://huggingface.co/datasets/livecodebench/code_generation_lite)
- [EvoAgentBench](https://github.com/EverMind-AI/EvoAgentBench)
