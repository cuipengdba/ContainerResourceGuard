# 三项资源同时设置时的持久化故障与中断恢复

2026-11-16 CST。新增P09.3/P10.3验证任务；现阶段为冻结方案，未声称运行通过。

延续用户要求：每容器一个Agent，只管理CPU、内存、IO；内存写memory.high而不新设memory.max，辅助故障不得阻断原业务。
原先CPU单项的120检查不自动覆盖三项同时变更，本轮使用同一最终ELF、另立冻结计划与真实内核收据。

## 预定场景与判据

独立GitHub临时VM，先amd64/Linux6试点独立复核，再同方案ARM64/Linux7。准确最终源码/ELF保持。
每容器先由测试设置并捕获外部2CPU、512MiB硬上限、384MiB高水位及4096读写IOPS，
Agent只设置CPU0.5→0.75核、memory.high128→192MiB、读写BPS4→6MiB/s。
数据盘为独占2GiB稀疏文件的loop+唯一UUID dm-linear上的ext4，状态盘为4MiB tmpfs；不是独立物理盘。

1. 状态盘ENOSPC、撤销权限EACCES、私有挂载EROFS各保持至少30秒，各三次显式失败重试，三项原有策略及日志保持；解除后新策略可应用。
2. 分别在CPU、memory.high、io.max写入前与写入后精确强杀唯一Agent；必须先观察匹配持久pending日志、真实内核值，以及前序/后序资源准确状态。
3. 写入后强杀须先绑定尚未提交finalization临时JSON的准确名称/长度/SHA，原字节进入ZIP；恢复不采信该临时文件。
4. 同样fsync返回延迟下正常完成三项变更，再正常退出和恢复。

每场景核对八项外部原值恢复，PID1/有界fsync任务连续及观测OOM计数不变；准确所属容器/cgroup/登记PID/私有挂载/dm/loop清理。
所有真实失败和原件保留，不修改原52项定义或18项完成声明。

## 边界

本轮是同时三项手动策略，不是默认20%性能、厂商DBS/HISDBS业务、七天老化、物理慢盘或掉电验收。
fsync延迟为返回路径注入，SIGKILL不等于掉电；重试显式由测试执行，不是原Bash helper自动重试验收。
97原独占长期任务保持，不增加业务夹具、不重启、不改配额。稳定1.0仍待原全部门槛。

[计划](test-plan-final-v1-persistence-three-resources.json)、[执行器](../tests/persistence-three-resources-v1/driver.py)。
