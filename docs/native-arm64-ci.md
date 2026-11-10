# 原生ARM64 CI：范围与证据

P06/P09新增[原生工作流](../.github/workflows/native-arm64.yml)，[运行前计划](test-plan-native-arm64-ci.json)冻结在push触发前。当前仓库为public；[GitHub官方说明](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)提供`ubuntu-24.04-arm`标准ARM64 VM入口。先使用该入口验证源码原生执行，无需新增自托管节点。不能把标签或交叉编译结果当作已经通过。

工作流强制`uname`对应的机器架构及Go宿主/目标均为Linux/ARM64，固定Go1.27.3；记录实际内核和cgroup文件系统，运行vet、未缓存race、辅助程序故障/TERM脚本和集成补丁脚本。构建ELF时核对machine183，再实际执行build-info核对源码SHA；成功结果与环境、原生程序、race事件及脚本日志保存14天，失败时也上传已有证据。下载后另行长期归档摘要，不能仅依赖短期artifact。

这一步没有实际CPU/内存/IO控制写入，也不运行DBS/HISDBS厂商ARM64镜像。Go单测的隔离文件系统不能替代真实控制器和业务；P06的ARM64资源/故障恢复/业务、多设备和Linux6.x实际控制矩阵仍待验收。该CI既不修改既有节点的程序/配置/基线，也不替换已发布预览包。
