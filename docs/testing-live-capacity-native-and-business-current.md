# 新容量候选：原生通过、原路径业务终态与后续任务

当前生产源37ca44e0e24a0eaa14e52b5c8bbbda54c76364b0，已合入集成分支。ARM64真实CPU热插拔56/56通过；完整59来源绑定下四格原生284/284通过。新ELF的DBS/HISDBS原路径完整600秒本轮已结束：HISDBS9/9通过，DBS7通过/1失败/1未执行；整体17项记录中16通过，原计划18项未全部通过。稳定1.0.0尚未接受，新长稳未启动。

## 原生与程序行为

同一Agent/PID1在4次实际CPU下线/上线后自动按当前在线核数重算20%配额，4核0.8核→3核0.6核→4核0.8核；紧外部上限、八项原值恢复、CPU掩码及归属清理通过。旧版六项失败、早期夹具问题和AMD64 sysfs下线EBUSY未覆盖边界[均保留](testing-live-cpu-capacity-refresh.md)。此非内存热插拔或厂商ARM证明。

四格[run43761828877](https://github.com/cuipengdba/ContainerResourceGuard/actions/runs/43761828877)，准确验收源1c9fb28dd2d66e2be0c9fb42fdc7b83657474f09；[冻结v2计划](test-plan-capacity-refresh-native-CI-v2.json)摘要 b971e185a4c0572fa56a78ac5d0bcdad7d4195d5adec647b3c4286ee18a732b4。amd64/arm64分别在Linux6.8.0-1070-azure和7.0.0-1017-azure，每格26项自身容器及45项分区/旧已发布ELF恢复，共284/284。原驱动/控制标准不变，所有归属清理通过。

[原生独立结论](test-results-live-capacity-native-CI-v2.json)、[32准确成员及API/步骤元数据](test-evidence-live-capacity-native-CI-v2.json.gz)摘要84614bf12c6c9eeda5c23406dde54ec60bc6c994a56dacbb30193cd27083f1ad，186456字节，逐摘要/CRC复核；有界成员下载，未宣称完整大ZIP校验。准确ELF/59来源、架构/内核、memory.high/外部硬上限/IOPS、旧发布包和八项恢复均核对。首轮50绑定漏列9项的[来源门禁缺口](test-evidence-live-capacity-native-first-gap.json.gz)保持原结论，未改写为完整通过。

## 原路径600秒最终结果

配置、负载、SQL/API零错误/max5秒/p95桶1秒/98%覆盖、备份周期包含关系、端口归属及删除时限等原条件未改。手动参考为7.2核、memory.high20001980416B、读写64MiB/s与4096IOPS；该结果不代表任意默认20%业务性能。

| 角色 | 原生负载 | SQL | API | 原角色检查 |
| --- | --- | --- | --- | --- |
| DBS | 600.336702秒 | 299次、1错误、max5.004658635秒 | 121次、0错误、max0.009306852秒 | 7通过/1失败/1未执行 |
| HISDBS | 600.367087秒 | 301次、0错误、max2.090419437秒 | 121次、0错误、max0.009226143秒 | 9/9通过 |

两角色数据完整、原主库未重启、负载线程正常退出；物理备份/同步/独立恢复各10项内容及PG端口归属原件独立核对，周期均在各自原生窗口内。DBS第8项因SQL错误及超过5秒失败，第9项未记录执行，不能因独立诊断可复算而补记为通过；良好p95或备份内容也不能抵消请求SLA失败。

[完整独立复算](test-results-live-capacity-business600-terminal.json)、[22准确原件/318943字节及终态、artifact-index](test-evidence-live-capacity-business600-terminal.json.gz)。22项独立证据核对通过，保持整体phase failed/exit1。两namespace、父组/leaf和所有61条进程登记（53个唯一PID/start实例）已独立确认消失，runner及两driver原实例均结束；不是仅凭delete退出码判断清理。活动13输入保持原字节，未静默重启。

[早期DBS失败原件](test-evidence-live-capacity-DBS-first-failure.json.gz)、[约300秒带日期快照](test-results-live-capacity-business-live.json)保留；这些早期快照不替代本次终态。

## 未知原因与后续开发任务

最新诊断开发：[有界SQL/API失败事件已实现并完成两平台故障验证，尚未进入厂商容器或新业务测试](development-sql-failure-diagnostics.zh.md)。原失败及全部发布门槛不变。

DBS出现一次SQL失败且耗时超过5秒。原工作线程只保存计数/直方图，吞掉请求异常，没有错误类型、明细或逐请求时间，不能恢复丢失的信息，也不能据此认定CRG或CPU容量刷新导致。当前不以“偶发”忽略、不放宽SLA、不静默重跑以掩盖失败。

本轮子任务归入原P02.1/P02.2/P06.3/P06.4/P10.2/P10.3；原52项定义与18项既有范围完成声明不变。后续明确任务：

1. 为隔离验收工作线程增加有界的SQL/API失败事件：时刻、阶段、错误类型/原因和耗时；限制数量、字段长度及总量，保护敏感信息。保持原SQL、采样周期、5秒/零错误和600秒条件。
2. 在独立冻结身份上核验诊断采集（包括权限/容量失败），不改已结束本轮原件或产品源37ca44e。当前有界诊断已实现并在Windows及原生Linux各26项故障验证通过；[代码、证据和后续任务](development-sql-failure-diagnostics.zh.md)。尚未完成厂商环境执行、受控注入或因果对照。
3. 用原镜像、路径、参数和准确ELF做隔离对照，保留每个失败、外部压力及备份/请求时间线，查明阻塞位置；不得仅靠重复到绿灯。若需要改变业务预算或验收语义，明确记录和评估，不能静默替换原标准。
4. 问题闭环后执行新候选两角色原18项及各600秒，分别独立复算和清理。全通过前不接受业务门槛。
5. 再从零执行24h observe、同容器24h enforce、新七天与原老化后故障/恢复/升级、稳定包身份门槛。旧ced/1396/1728/78保持原来源/失败，不继承时钟；无额外厂商ARM/两独立物理盘的边界保持。
