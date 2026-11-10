# Linux6.x 原生控制器兼容性计划

P06增加手动触发的[Linux6工作流](https://github.com/cuipengdba/ContainerResourceGuard/blob/main/.github/workflows/linux6-cgroup.yml)，复用先前dm/loop控制器22项驱动和原预算，不改变产品代码或测试机业务。两条开发线分别运行AMD64/ARM64，源码/工作流摘要在[首次执行前冻结](test-plan-linux6-cgroup-ci.json)。

GitHub当前[AMD64镜像清单](https://github.com/actions/runner-images/blob/main/images/ubuntu/Ubuntu2204-Readme.md)与[ARM64镜像清单](https://github.com/actions/runner-images/blob/main/images/ubuntu/Ubuntu2204-Arm64-Readme.md)为22.04列出6.8内核，但镜像标签和文档不作为实测结果。任务先记录实际内核、架构、Docker和cgroup文件系统，并在任何设备或容器夹具前断言内核为6.*、文件系统为cgroup2fs；不符则保留失败，不放宽成其他内核。

新鲜原生VM执行vet/race和精确CLI，沿用真实CPU节流、内存值、直接读写/IOPS、一对一身份、Agent崩溃/恢复、自动三百分比、新ID/profile/日志复用及只读降级检查。仅创建专属临时文件、loop、dm-linear和ext4，逐层核验所有权后格式化自己的新设备；正常清理并验证，不能对现有磁盘操作。

本计划不是完成证明。即使通过，也只补实际记录的6.x内核、架构和Docker组合的占位容器/控制器证据；不接受厂商业务、物理多设备、分区映射、发布ARM资产或长期测试。22.04仅作一次兼容性探测入口，普通CI基础不变。
