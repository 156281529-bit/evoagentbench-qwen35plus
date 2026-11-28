# 在本目录启动和复现

成果入口为 https://github.com/156281529-bit/evoagentbench-qwen35plus/tree/main/week4-2 。
本次项目源码和说明集中在该目录。建议检出整个仓库后进入 week4-2。

## 环境

- Python 3.10 或以上。公开重放及 Python 执行器只使用标准库。
- Node.js 20.9 或以上及 npm。实际验证版本为 Node.js 24.22.3。
- 原生 RSI-Flow 模式另外需要 JDK 8、Maven 3.8 或以上及 Maven Central 网络。
- 重新取得隐藏测试的 Linux 判分还需要 Docker、LiveCodeBench 固定版本及原冻结数据。

## 先验证公开程序与保存的正式证据

从 week4-2 运行以下命令。输出文件放进忽略目录 reproduction-output。

```sh
mkdir reproduction-output
python replay.py --output reproduction-output/public.json
python new-four/audit.py
python new-four/replay.py
python native/verify.py
```

第一条重跑原十题的公开样例及反例。audit 验证新增四题代码哈希、Linux 通过向量和原生调用号。
new-four/replay.py 实际执行新增四题的前后代码，核对已公开的输入与输出。
native/verify.py 校验保存的十次原生调用与保留题回执。
以上公开重放产生新的本地执行结果，Linux 历史判分来源为保存的原始回执。

## 启动前端与执行器

终端一从 week4-2 启动执行器。

```sh
python batch_service.py --port 39913 --output reproduction-output/platform.json
```

终端二启动独立的 Next.js 前端。platform 已带 package.json、锁文件、App Router 布局及编排组件依赖。

```sh
cd platform
npm ci
npm run build
npm start
```

打开 http://127.0.0.1:3000/context-repair/batch ，点击运行十题。
浏览器通过同源 API 调用 39913 执行器，实际重放本目录的程序并保存逐节点结果。
原冻结批正式修复率是 8/10，另两题保留失败分支。十四道累计成绩见主说明及新增四题材料。

## 启动真实 RSI-Flow 节点

本目录 native/src 包含节点、注册查询和 Spring 启动类，native/resources 包含实际流程定义。
独立 Spring 入口与原 RSI-Flow 0.4.14 引擎在本目录构建。

从 week4-2 执行以下命令，需要 JDK 8、Maven 3.8 或以上及访问 Maven Central 的网络。

```sh
mvn -s native/maven-settings.xml -f native/pom.xml -DskipTests package
java -jar native/target/native-reproduction-1.0.0.jar --server.address=127.0.0.1 --server.port=39914
```

native/vendor/maven 收录未发布到 Maven Central 的原引擎及其运行依赖，附文件 SHA-256。
其他 Spring 等依赖从 HTTPS Maven Central 下载。独立适配器保持 flowId、params 及 result/status/data.value 契约，
实际调用原引擎的 register、run、retrieveFlowResults、release。释放操作在 finally 中执行。
历史运行使用原后端 Controller/Service，当前独立入口是本次为降低启动依赖新增的 HTTP 适配器。
原鉴权、数据库和完整平台模块不参与这项节点复现。原始后端来源为
https://github.com/ymxiong/rsi-flow-spring-boot ，原引擎源码来源为 https://github.com/ymxiong/rsi-flow 。

另一个终端启动原生模式执行器。

```sh
python batch_service.py --port 39915 --native-engine http://127.0.0.1:39914 --output reproduction-output/native-platform.json
```

打开 http://127.0.0.1:3000/context-repair/batch?native=1 ，点击运行十题。
JSON 中 native_registration 应包含 assembled=true，十题分别返回独立 invocation。
GET http://127.0.0.1:39914/week4/registration 可检查实际注册。

## 隐藏数据与正式判题

隐藏数据恢复方法、SHA-256 和判题版本见主说明第 5 节及 evidence/cohorts.json。
公开重放可以直接启动。Docker 模式须具备可访问的 Docker daemon，并下载或自行构建对应镜像。
原判分镜像身份保存在 evidence/official-after.json。未取得相同环境时应按公开重放结果与历史正式回执分别报告。

## 编排框架来源

前端采用原 visual-core 0.3.12，发布文件来自 ymxiong/rsi-flow-visual 的提交
43b8f53a7c77cbc6ea5f655820dfbe9336cb4452。为消除相邻本机目录依赖，未改动的 dist 和 types 收录在 platform/vendor/visual-core。
后端框架采用原 RSI-Flow 0.4.14。人工确认的业务编排、节点和前端调用的本次改动均位于本目录。
框架实现沿用上游，源码归属保留原作者信息。

## 本次实际验收（2026 年 11 月 28 日）

- 原十题公开重放、新增四题前后程序重放及代码哈希核验均通过。
- Next.js 16.2.6 生产构建、TypeScript 检查及生产服务启动通过。
- 页面实际点击“运行 10 题”，经 Next.js API、Python 执行器调用原 RSI-Flow，返回十个独立调用号。
- 独立 Spring 工程执行 Maven package 成功，使用新生成的 JAR 启动后，注册查询和十次真实节点调用通过。
- 本轮节点调用重新执行公开输入；隐藏组 Linux 判分读取与代码及数据哈希绑定的历史回执，未重新取得隐藏组判分。
- npm 网络安装中断后，构建复用了本机相同版本的 Next.js 及 SWC 依赖。锁文件已生成并提交，完全无缓存的 npm ci 尚未完成验证。
- 原完整上游后端构建受私有 auth 依赖阻碍，因此当前首选启动入口为本目录独立 Spring 工程。

独立后端保留业务节点和流程 JSON，增加 HTTP 适配器以保持已有请求响应契约。此次没有调用远端低代码平台 API 同步流程 JSON，
当前验证范围是本地 RSI-Flow 引擎的注册、装配与真实调度。
