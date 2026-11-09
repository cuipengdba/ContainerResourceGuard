# 开发进展（2026-11-10）

本文件区分已发布、开发完成与仍需验收的事项。当前公开发布仍为 `v0.1.0-rc.2`，没有发布 RC3、v0.2 或 1.0。

## 已完成并有证据

- 重启身份设计及百分比/手动两种模式、五个额外可选参数已纳入 [46 项任务的十版规划](roadmap.md)。
- main 已实现双模式 CPU/内存/IO、可选 pids_max 和 cpu_weight；[22 项分阶段 Linux 验证](testing-dual-modes.md) 已归档，包含新 Pod 身份发现、真实硬限额和恢复原值。原失败记录保留。
- [next/safe-reload 分支](https://github.com/cuipengdba/ContainerResourceGuard/tree/next/safe-reload) 提前开发 v0.2。源码 8401515 的 [CI](https://github.com/cuipengdba/ContainerResourceGuard/actions/runs/42676218251)、Linux race/vet、辅助进程故障与建模强杀回归通过；13 项真实 cgroup 重载验证通过。见该分支的 [详细报告](https://github.com/cuipengdba/ContainerResourceGuard/blob/next/safe-reload/docs/testing-reload.md)。功能尚未合入 main 或发布。
- DBS/HISDBS 原镜像已只读导出到隔离测试节点，传输摘要与各自原镜像 config digest 核对通过。未把厂商镜像、业务数据或脚本纳入公开仓库。

## 当前开发与验收

原镜像隔离副本已建立，测试 Pod 的非回环网卡已关闭，并另设命名空间网络隔离策略。接下来验证原 start.sh、厂商数据库/API、原缓存程序和备份同步链。现有资源和重载结果使用占位业务命令，不能代替这些验收。

后续按十版安排继续补齐 IO 标定与权重、内存压力/Swap、环境回归、诊断、安装升级、构建来源和兼容契约。io_weight、memory_high、memory_swap_max 尚未实现，不能提前加入运行配置。

24h 基线/24h 限额运行、arm64 真机、实际多设备及 1.0 的至少 7 天目标业务验收均未完成。完成源代码、通过短测或创建版本标签都不能替代持续运行和真实业务证据。业务节点当前只读检查，未修改其部署和控制文件。
