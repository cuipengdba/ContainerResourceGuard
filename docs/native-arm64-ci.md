# 原生ARM64 CI：范围与证据

P06/P09新增[原生工作流](https://github.com/cuipengdba/ContainerResourceGuard/blob/main/.github/workflows/native-arm64.yml)，[运行前计划](test-plan-native-arm64-ci.json)冻结在push触发前。当前仓库为public；[GitHub官方说明](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)提供`ubuntu-24.04-arm`标准ARM64 VM入口。先使用该入口验证源码原生执行，无需新增自托管节点。不能把标签或交叉编译结果当作已经通过。

工作流强制`uname`对应的机器架构及Go宿主/目标均为Linux/ARM64，固定Go1.27.3；记录实际内核和cgroup文件系统，运行vet、未缓存race、辅助程序故障/TERM脚本和集成补丁脚本。构建ELF时核对machine183，再实际执行build-info核对源码SHA；成功结果与环境、原生程序、race事件及脚本日志保存14天，失败时也上传已有证据。下载后另行长期归档摘要，不能仅依赖短期artifact。

这一步没有实际CPU/内存/IO控制写入，也不运行DBS/HISDBS厂商ARM64镜像。Go单测的隔离文件系统不能替代真实控制器和业务；P06的ARM64资源/故障恢复/业务、多设备和Linux6.x实际控制矩阵仍待验收。该CI既不修改既有节点的程序/配置/基线，也不替换已发布预览包。

## 首次实际结果

主线041aeb1与组合ccfe0f7均完成原生ARM64执行，三个Go包通过vet/race，分别有101和184条Go测试pass事件；原启动helper/集成补丁脚本及原生CLI成功。实际环境均为aarch64、Go1.27.3、cgroup2fs，**内核实际是7.0.0-1017-azure**，不按runner标签猜成6.x。[去标识结果及逐文件摘要](test-results-native-arm64-ci.json)记录源修订、ELF183、程序摘要和实际工作流。

两条普通构建CI首次在包内Markdown链接检查失败：新增文档的相对工作流链接指向未打包的`.github`目录。现仅改为仓库URL；包校验不删除、不放宽，原失败和后续修复CI分别留证。ARM原生任务成功不能冒充普通发布包CI已通过。

这比仅交叉编译多了实际原生运行证据，但仍没有ARM64实际资源控制、DBS/HISDBS业务或Linux6.x控制实测；已发布预览的ARM64产物不因后来不同源码的CI被追认为已验收。

P06原生基础CI之后的[实际容器控制器计划](plan-native-cgroup-ci.md)已归档，拟补AMD64/ARM64实际三项控制、自动百分比/新ID及权限回退。一次性驱动/双架构工作流在首次push前冻结；首轮分区失败和后续独占dm/loop实际控制88项通过分别归档，不关闭未测业务或硬件门槛。

包链接修复后的两线完整构建CI已通过：[main/c3bed5b](https://github.com/cuipengdba/ContainerResourceGuard/actions/runs/42825125118)、[组合/91b2f54](https://github.com/cuipengdba/ContainerResourceGuard/actions/runs/42825125168)。两次原链接失败保留；修复提交仅影响文档，与前述原生ARM任务的源修订分开记录。

原生控制器第二轮[AMD64/ARM64两线88项通过](testing-native-cgroup-dm-loop.md)：实际三项限额/节流/直接IO、独立自动百分比、新ID/profile复用、Agent崩溃恢复及真实只读降级和清理。存储为独占dm/loop；首轮分区四格失败保留，ARM厂商业务、物理多设备、6.x及长期门槛仍未关闭。
