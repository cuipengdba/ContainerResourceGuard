# IO 百分比改为读写带宽（R10追加，2026-11-13）

当前交付范围见[preview.5已验证子集](testing-preview5-qualified-subset.md)：准确工程CI、两架构重复字节、新程序DBS20完整36项及95实例清理通过；完整20/30矩阵仍在运行。下文早期任务状态按原时点保留，原完整业务/长期与稳定门槛继续。

状态：用户已明确选择，下一版候选已实现；准确ced461705ebc27315a59aefe463f9b4af47130a3完整Linux/两架构包/可复现、原生ARM64、52项实际Cgroup及180项分区检查通过，新默认真机回归已运行，DBS20首轮17项通过，未终结。已发布preview.4仍是旧四轴语义，未原地替换其附件。

用户答复：“默认按读写带宽百分比限制，IOPS 留给手动模式”。因此io_percent默认20，只换算标定read_bps/write_bps；例如读100MiB/s、写50MiB/s的基准，20对应rbps20MiB/s和wbps10MiB/s。不是物理设备保证吞吐，也不按标定read_iops/write_iops生成默认IOPS硬限额。旧percent兼容入口采用相同新IO语义；CPU/内存独立百分比及各默认20、memory.high和每日30天/1GB日志保持。

```json
{"cpu_percent":20,"memory_percent":20,"io_percent":20}
```

手动模式仍支持limits.io_read_bps/io_write_bps/io_read_iops/io_write_iops及data_paths；只有手动填写IOPS才请求额外IOPS硬限额，省略轴保留原值。自动选最大合格本地可写文件系统、后台首次标定和稳定身份复用保持；profile继续保留原四项测量作为诊断/兼容数据，低IOPS测量不再因百分比不足1而阻止有效BPS设置。

## 外部限额与升级

“默认不增加IOPS限额”不等于清空Kubernetes/运行时/其它程序的既有IOPS。写入io.max仍使用可回读、可恢复的四轴规范值，riops/wiops取实际外部基线；上级约束继续由内核执行。没有外部IOPS时才是max；不能无条件echo riops=max wiops=max。

旧版已写四轴限额时，沿用现有journal迁移：同容器cgroup身份、同块设备稳定身份，完整当前四轴仍等于自有Applied或可恢复Pending，且无Conflict，才使用保存的Original计算新BPS并恢复原IOPS。任意轴被外部改动即拒绝覆盖、日志/状态降级，设备替换拒绝写；持久化意图、写前重读、身份复核、写后核对、崩溃恢复和disable还原保持。新Pod/容器ID会隔离旧journal，不从旧容器迁移值。profile暂缺时继续保留旧IO限额并报告，不能为了迁移盲目取消所有IO约束。

plan/status输出io_policy，build-info输出io_percent_policy；资源日志包含策略、设备、目标值及逐项状态。memory.high仅为回收/节流目标，允许超过，外部memory.max或系统内存不足仍可能OOM。

## 本次任务与验证

| 任务 | 实现/要求 | 当前状态 |
| --- | --- | --- |
| R10-BW.1 | 百分比仅换算两项BPS，保留外部IOPS | 已实现，本地及准确Linux/原生CI通过 |
| R10-BW.2 | 原自有四轴到带宽模式的安全journal迁移 | 沿用已存在保护；新增恢复/冲突/设备/意图失败/中断/observe回归通过 |
| R10-BW.3 | 手动IOPS保留；日志/CLI/构建信息可识别新语义 | 已实现，准确CI通过 |
| R10-BW.4 | 原生两架构及Linux6/7分区实际迁移与外部IOPS | 真实同容器手动27/11→百分比切换、重建后外部197/149保留：两架构/四分区格全部通过 |
| R10-BW.5 | 原真机默认20/30矩阵、备份/同步和故障回归 | 新准确源码默认20/30矩阵运行；17/144项首轮通过，完整业务仍待 |
| R10-BW.6 | 两架构包、完整性、可复现、GitHub下一版发布 | 准确源码CI两架构包通过；准备发布字节双架构重复构建一致，尚未发布 |

原手动对照74/144、历史失败及52项完整任务定义/完成声明保留。此次明确用户变更覆盖旧R10四轴口径，不降低任何业务时限、负载或长期/迁移门槛，也不把旧七天经过时间转给新源码。

[准确工程分析](test-results-IO-bandwidth-CI.json)及[28份精确成员](test-evidence-IO-bandwidth-CI.json.gz)已归档；[新默认真机四格](testing-bandwidth-percent-startup.md)单独验收，不能借用旧手动对照。
