# 最终 ELF：真实状态文件系统故障与中断恢复

2026-11-16 CST。本轮补充 P09.3/P10.3 的原生证据，原任务不缩减。
计划与执行器已开发，**完整实际结果尚待**，不能据此接受稳定版。

## 冻结任务与判据

产品仍为最终源码 `ced461705ebc27315a59aefe463f9b4af47130a3` 的准确 v1.0.0 ELF。
独立 GitHub VM 先验证50份产品源码与两个 ELF 摘要，再建立带唯一标签的临时单容器。
实际环境按计划分别为 amd64/Linux6.x 和 ARM64/Linux7.x；先独立复核试点再派发后者。
不读取或更改97上正在运行的DBS/HISDBS夹具。

每个容器一个Agent，测试策略只设置手动CPU，内存/IO等八项外部原值逐项核对。
状态目录位于本次独占的4MiB tmpfs（128 inode），业务占位PID1、有界fsync写盘任务和日志
分别使用独立位置。这里只填满状态文件系统，不填满VM根盘或真实业务盘。

| 场景 | 预定验证 |
| --- | --- |
| 实际ENOSPC | 写本次填充文件直至内核返回ENOSPC，保持至少30秒；活跃Agent与三次后续显式重试应拒绝新CPU策略、保留原日志和已有控制值 |
| 持续EACCES | 执行前移除Agent的DAC_OVERRIDE/DAC_READ_SEARCH有效及bounding能力，再撤销状态目录权限至少30秒；实际权限错误、三次失败重试、原业务存活必须可见 |
| 私有挂载EROFS | 仅将所属容器的/state绑定挂载改为只读至少30秒，验证真实只读错误及三次拒绝重试；不将宿主根文件系统改为只读 |
| 控制写入前SIGKILL | 真实fsync返回路径注入3秒退出延迟；观察已发布pending日志及仍旧的实际CPU值，再精确强杀登记的Agent，重启恢复必须回到原值 |
| 控制写入后SIGKILL | 观察准确新CPU值与仍pending的持久日志，再强杀同一Agent；后续恢复须识别中断写入并还原外部原值 |
| 延迟完成 | 在相同fsync延迟下完成变更和最终日志，再正常停止并恢复，核对所有原值 |

三种持续故障解除后，新策略须可成功应用，随后真实恢复八项原值。
每次操作前复核容器标签/完整ID、PID1及start_ticks、私有命名空间、cgroup路径与inode；
只向准确SHA256和登记PID/start的Agent发信号，最多一个Agent。
业务PID1及有界fsync任务保持连续，观测OOM计数不变。
失败原件和真实strace保留，不把延迟注入当物理慢盘，不把SIGKILL当掉电。

每个所属容器、cgroup、登记进程和准确私有挂载都必须独立确认清理；
容器身份或挂载身份发生变化时拒绝盲目删除。
执行器故障与产品故障均保留原失败，修订测试方案必须使用新身份。

## 工具与边界

[冻结计划](test-plan-final-v1-persistence-faults.json)、
[执行器](../tests/persistence-faults-v1/driver.py)、
[测试专用能力/挂载辅助器](../tests/persistence-faults-v1/helper.go)。
辅助器仅在显式隔离测试标志下执行：可为本容器/state挂载切换只读，
或去掉两项DAC绕过能力后exec准确候选；不包含在常驻Agent中。

本轮使用真实内核错误及真实cgroup，业务是占位PID1/有界写盘任务。
它不能代替厂商原路径、实际老化、高脏页业务压力、物理慢设备或真实掉电验收。
三次重试由测试明确发起，不把它们宣称为原Bash可选辅助程序的自动重试验收。
强杀可能留下尚未重命名的临时文件，本轮保留这些文件，检查恢复不采信未提交日志；
不承诺强杀后自动清理全部孤立临时文件。
原有普通文件模拟恢复单测、解析器模糊测试与已有维护证据继续保留各自范围。


## 首轮真实试点失败保留

[运行43745123083](https://github.com/cuipengdba/ContainerResourceGuard/actions/runs/43745123083)失败：
27项局部检查通过，真实ENOSPC和持续EACCES两组完成；第三组只读挂载准备返回EBUSY，
因为Agent持有的可写状态锁描述符阻止直接remountRO。未执行后续三组强杀/延迟完整验收，
不接受整套60项通过。[原始41成员ZIP](test-evidence-final-v1-persistence-first-pilot.json.gz)及
[失败摘要](test-results-final-v1-persistence-first-pilot-failure.json)保留，三所属容器/cgroup、
登记进程和私有状态挂载均确认清理。

[原v1计划](test-plan-final-v1-persistence-faults-before-readonly-overlay.json)不改写。
v2只修正测试挂载准备：在同一私有/state树上叠加新bind，再将新挂载只读，
并核对唯一新挂载及实际statvfs只读标志；已有打开的旧锁保持原inode。
另记录实际观察到的候选DAC能力值，便于离线独立复核。
产品50份源码、ELF、限额、持续30秒/3次重试和恢复/强杀判据均不变。
