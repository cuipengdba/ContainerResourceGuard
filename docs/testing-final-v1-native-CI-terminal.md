# 正式版本号固定ELF：原生284项终态

[实际GitHub运行](https://github.com/cuipengdba/ContainerResourceGuard/actions/runs/43685269337)四单元均成功，原生控制104项、分区180项，合计284/284通过。实际执行程序均与固定候选ELF摘要完全相同，嵌入v1.0.0/source ced4617；每单元使用固定Go1.27.3同时重建两架构，二进制摘要均匹配。Windows与原生Linux构建一致，不以同源码的不同版本程序代替。

| 原生VM | 架构 | 实际内核 | native | partition |
| --- | --- | --- | --- | --- |
| ubuntu-22.04-arm | arm64 | 6.8.0-1070-azure | 26/26 | 45/45 |
| ubuntu-24.04 | amd64 | 7.0.0-1014-aws | 26/26 | 45/45 |
| ubuntu-24.04-arm | arm64 | 7.0.0-1017-azure | 26/26 | 45/45 |
| ubuntu-22.04 | amd64 | 6.8.0-1070-azure | 26/26 | 45/45 |

原始26/45驱动摘要、实际CPU/high/IO控制、默认带宽/手动IOPS和外部IOPS保留、同设备兄弟分区共享预算及几何变更、准确旧发布程序恢复与完整清理逐项复核。原有外部memory.max只是保留并核对，不是候选新设置的内存策略。四组均确认自有容器/cgroup、镜像、映射/挂载/loop及私有测试目录清理。

[机器资格](test-results-final-v1-native-CI-terminal.json)、[32份准确原件与运行/附件元数据](test-evidence-final-v1-native-CI-terminal.json.gz)、[冻结计划](testing-final-v1-native-CI.md)。本地导出初次因全量GitHub运行元数据含无关公开提交邮箱而被隐私过滤拒绝，改成运行/任务字段白名单后导出；32份原件字节不改。工作流初次Windows换行摘要不一致已在调度前修正，工作流只实际调度一次，没有隐藏重试。

范围为临时原生VM控制器及同设备分区，不是ARM厂商业务、两个独立物理块设备或长期运行。厂商业务另见[固定ELF原路径18项终态](testing-final-v1-full600-terminal.md)。稳定1.0尚未接受，当前公开下载仍为preview.5，八项附件与标签保持不变。
