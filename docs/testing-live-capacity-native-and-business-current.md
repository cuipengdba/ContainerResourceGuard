# 新容量候选：四格原生终态与业务失败边界

当前生产源37ca44e0e24a0eaa14e52b5c8bbbda54c76364b0。ARM64真实CPU下线/上线56项已通过，另四个原生VM组合在完整59项来源绑定下，104项自身容器控制和180项分区/恢复共284/284通过，所有归属夹具清理通过。这些是源/ELF准确对应的原生控制证据，不代替DBS/HISDBS业务或长稳。

## 原生284项

[run43761828877](https://github.com/cuipengdba/ContainerResourceGuard/actions/runs/43761828877)，验收代码1c9fb28dd2d66e2be0c9fb42fdc7b83657474f09；[冻结v2计划](test-plan-capacity-refresh-native-CI-v2.json)摘要 b971e185a4c0572fa56a78ac5d0bcdad7d4195d5adec647b3c4286ee18a732b4。每格26项自身容器与45项分区/旧已发布ELF恢复，原控制条件、驱动和归属清理不变。

| 架构 | 实际内核 | 检查 |
| --- | --- | --- |
| amd64 | 6.8.0-1070-azure | 71/71 |
| amd64 | 7.0.0-1017-azure | 71/71 |
| arm64 | 6.8.0-1070-azure | 71/71 |
| arm64 | 7.0.0-1017-azure | 71/71 |

[独立复算结论](test-results-live-capacity-native-CI-v2.json)、[32份准确原始成员及API/步骤元数据](test-evidence-live-capacity-native-CI-v2.json.gz)摘要 84614bf12c6c9eeda5c23406dde54ec60bc6c994a56dacbb30193cd27083f1ad。成员共186456字节，逐摘要/CRC核对；这是有界成员下载，未宣称完整大ZIP摘要校验。复算核对准确候选ELF、生产及测试/构建59绑定、实际内核/架构、内存high-only/外部硬上限/IOPS、旧发布包来源和八项恢复、最终归属清理。初轮50绑定漏列9项仍单独[保留](test-evidence-live-capacity-native-first-gap.json.gz)，不改写其来源门禁不完整结论。

## DBS完整600秒失败

原18项/两角色各600秒协议未改变。DBS角色600.336702秒原生负载，8项记录中7通过、1失败，第9项因第8项失败未执行。SQL299次中298成功、1错误，max5.004658635秒，p95桶0.001秒、采样覆盖99.67%；API121次全部成功，max0.009306852秒。原标准要求SQL/API零错误、max<=5秒，故整体不能通过；不能由良好p95、完整备份内容或原生284通过抵消。

[准确角色/原生/活动报告](test-evidence-live-capacity-DBS-first-failure.json.gz)、[本角色失败结论](test-results-live-capacity-DBS-first-failure.json)。原SQL工作线程只计数并吞掉异常，没有保存错误类型、明细和逐请求时刻；底层原因未知，也不能据此认定CPU刷新修复或CRG导致。不得虚构丢失异常或仅为得到绿灯静默重跑。

协调器按原协议清理DBS夹具并核对后继续HISDBS；截至21:12:03Z节点快照，新runner3165983/start171633500仍为原实例，HISDBS driver3309685/start171700428启动7项通过且600秒负载中。本页并非整个本轮终态或全局独立清理证明；待两角色结束后按冻结artifact-index下载全部原件、复算、独立确认namespace/父组/leaf与登记进程消失。新长稳未启动。

## 继续任务与边界

先拿本轮最终结果、保持失败和原SLA；对缺失的请求错误细节建立有界诊断再作隔离因果复验。全部13项活动输入保持原字节，不在运行中改测试或程序；不从头静默重启。之后仍需满足原路径业务及24h observe、同容器24h enforce、新七天、老化后故障/恢复/升级与最终稳定包身份门槛。此前ced/1396/1728/78均保留原来源与失败，不继承时钟。无额外厂商ARM/两独立物理盘的边界保持。原52项定义和18个既有范围完成声明不变，稳定1.0.0尚未接受。
