# RSI-Flow 原生节点与独立启动

当前源码和启动命令见 [启动复现说明](../REPRODUCE.md)。
NativeApplication 注册 WEEK4_DIAGNOSE、WEEK4_ROUTE 两个节点和真实原引擎。
NativeFlowController 是本次独立 HTTP 适配器，流程入口保持 POST /api/engine/flow。
原十题的历史证据见 [原生调度验收](../NATIVE-SKILL.md)。

独立入口避免完整平台的鉴权和数据库依赖，使用随项目收录的引擎原始 JAR 及 Maven POM。
这些 JAR 是运行依赖，文件来源和 SHA-256 见 vendor/manifest.json。
引擎源码来自 https://github.com/ymxiong/rsi-flow 的提交 93cc223de5bc8f0510801796a46a8ae391725be9。
前后端 SDD 的流程契约、节点职责和错误处理作为实现参考。当前前端沿用 Next.js。

launch.py 保留原历史运行的 executable JAR 启动方式。新环境优先使用 pom.xml 构建独立入口。
