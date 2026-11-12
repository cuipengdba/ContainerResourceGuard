# 当前组合候选 Linux 6.x 实际控制器结果

按[执行前冻结合同](test-plan-linux6-current-integration.json)，组合线文档冻结提交`de89f59db17ee788a6de559bd4bea98ad62fa61a`在原生AMD64/ARM64、实际Linux6.8.0-1070-azure和cgroup2fs上完成各22项、合计44项控制器检查。两格均为[同一次手动工作流](https://github.com/cuipengdba/ContainerResourceGuard/actions/runs/43134284481)的attempt1，未取消或重跑。50份生产源码和四份工作流/驱动与冻结摘要一致，未改原数值、时长、误差界限和22项次序。

| 架构 | 实际内核 | CPU平均核数（限0.5） | 直接读/写MiB/s（各限4） | 随机写IOPS（限256） | Go测试pass事件 |
|---|---|---|---|---|---|
| amd64 | 6.8.0-1070-azure | 0.502556 | 3.996 / 4.002 | 252.380 | 212 |
| arm64 | 6.8.0-1070-azure | 0.499835 | 3.998 / 4.001 | 252.519 | 212 |

已核对实际CPU节流、128MiB内存上限与安全32MiB分配、直接读写与随机IOPS、原PID1和单Agent身份；Agent崩溃后内核限制保持，同journal恢复；显式disable还原八项原值。另有CPU10%/内存1%/IO20%独立换算、真实自动标定、新容器ID/profile复用、每日日志追加、撤销能力和真实只读cgroup降级。三份含测试的Go包全部pass；三份负载辅助包无单元测试，Go终态明确为skip，不把skip计为测试通过。其中load和native-holder的原生ELF在本次控制器测量中实际执行；partition-load仅编译，未在本次执行。

两格均确认专属容器/cgroup、镜像、挂载、dm、loop和私有目录正常清理。存储为单个专属稀疏文件/loop/dm-linear/ext4，不是独立物理多设备或真实分区测试；内存检查不是耗尽/OOM业务。程序为该提交的native-controller-ci构建，保留独立ELF摘要，不冒充已发布资产执行记录。

[结构化报告](test-results-linux6-current-integration.json)包括逐项实际值、源码、ELF、GitHub归档摘要和清理。[精确原件](test-evidence/linux6-current-integration.json.gz)保存冻结计划、终态工作流、两架构环境/报告/build-info/原生Go事件及下载回执，逐文件保留UTF8和SHA256。下载曾有55秒及240秒本地观察超时；保留原记录与已收字节后，用HTTP206续取尾部并核对完整GitHub归档摘要。仅读取同一已成功任务，没有改动或重跑测试。

主线生产源码、脚本、模块和本驱动至今与[旧Linux6报告](testing-linux6-cgroup-ci.md)对应来源一致，本次没有重跑主线，也没有重写旧报告来源。组合分区实现此前的真实GPT结果仍属于原提交；本次只补当前组合候选在6.8上的整盘控制与恢复。

[原七天任务只读快照](test-progress-seven-day-during-linux6-current-integration.json)记录服务器UTC 2026-11-12T01:20:23Z：原R57约101188/101179秒，精确发布ELF的R78约87673/87671秒，均5周期、SQL/API错误0；原runner/worker、campaign、Agent/cache/native实例与起始ticks保持，未重启。未满604800秒及原后置/故障，不计七天通过。

本结果不关闭ARM厂商业务、独立物理多设备、原32项双角色压力业务、24h配对、实际七天及后置、两个已发布旧次版本迁移；不改默认20%业务失败或已发布preview.3资产，稳定1.0仍待原条件。
