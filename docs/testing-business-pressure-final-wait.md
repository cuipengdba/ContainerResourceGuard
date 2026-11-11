# 完整压力的等待诊断及失败收尾接入

[冻结计划](test-plan-business-memory-pressure-final-wait.json)、[源码保全证明](test-freeze-business-pressure-final-wait.json)、[接入检查](test-results-final-wait-integration.json)及[固定启动快照](test-start-business-pressure-final-wait.json)已归档。R235 在独立 namespace 使用原 DBS/HISDBS 镜像和真实业务路径；启动观察时 runner/worker 均为同一 PID/start 实例，DBS 原生负载已绑定 pidfd、未发送 TERM，厂商镜像摘要匹配。**启动不是通过：两角色600秒及32项完整验收尚待实际终态。**

## 保持的业务要求

从摘要固定的 R203 完整工具另建新源码及计划，旧工具、计划、启动/失败报告原字节保持。完整业务方法 AST 比较仅允许在原生负载进入 running 后增加一次精确 worker 绑定；原32项、每角色600秒、11区间、真实30%→20%内存压力、同generation释放重试、SQL/API零错误/最大5秒/p95桶1秒、备库fast stop 30秒及命令45秒、全部CPU/内存/IO读回、64MiB校验、备份/同步/恢复和零OOM不变。失败保留数据，不通过删除历史夹具或缩小负载取得结果。

## 只读等待诊断

[资格结果](test-results-thread-wait-qualification.json)包含 Linux 24 项采集检查、原19项观察器检查和10项选取/预算检查。原始观察器反向字节证明保留原行为；新观察器只对初次样本中D状态线程追加有界诊断，最多8线程/8192额外字节，原64线程/1秒周期/900秒/32MiB报告上限保持。遇权限、身份变化、读边界、未知ABI或预算不足，记录unknown/omitted，不冒充可用或零等待。

仅对原生ELF64小端x86_64解码固定FD型syscall；不将futex地址当FD。读取/proc/task/syscall、kernel stack和FD链接；仅保留调用号/操作、适用FD编号、最多12个内核符号及允许的日志/PG/隔离临时路径，丢弃寄存器、地址、偏移和其他路径。不开FD目标、不读其内容、用户内存/栈、环境或任意参数，不ptrace、不改控制器、不向业务发信号。PID/start、syscall和FD链接前后复查仍不能使分开的/proc读取成为原子快照。

R229实际自建pipe child处于S状态；其read syscall/pipe FD及内核等待栈可读。R233将该真实S线程作为明确标注的合成D选取输入测试上限和竞态，不能算真实D业务证据。R232在既有DBS/HISDBS API进程上只读观察各15秒/16样本，均未出现D；两API/Agent实例、8控制值不变，观察器正常退出。完整原始SSH回执保存在[test-evidence/thread-wait232-observation.json.gz](test-evidence/thread-wait232-observation.json.gz)，摘要见资格JSON。这些短观察不替代压力业务验收。

语义依据：[Linux proc文档](https://docs.kernel.org/filesystems/proc.html)、[proc_pid_syscall](https://man7.org/linux/man-pages/man5/proc_pid_syscall.5.html)、[proc_pid_stack](https://man7.org/linux/man-pages/man5/proc_pid_stack.5.html)和[Linux5.14 x86_64 syscall表](https://raw.githubusercontent.com/torvalds/linux/v5.14/arch/x86/entry/syscalls/syscall_64.tbl)。R203的[离线时间相关性](pressure-native203-wait-correlation.md)只证明7次API超时与同一线程50个D样本重叠；未证明请求线程角色、文件操作或因果，不能归因为执行页换出。

## 提前失败时保留原生诊断

复用[已实际通过的pidfd最终清理资格](testing-native-final-flush.md)。一个Session只绑定本轮一个worker的cgroup/完整固定argv/run-id/源码/ELF/PID/start与pidfd，原业务失败后才允许一次TERM，最多120秒等待最终文件，不KILL、不延长可接受的业务测量。正常成功只关闭pidfd，不提前终止。收尾、采集、保存或关闭的第二个异常均不能遮蔽原业务异常对象。

新增12项接入检查使用明确测试替身覆盖成功零TERM、失败先drain后observer/collector、身份拒绝/超时/保存/关闭错误优先级，以及实际R203失败引擎起止归档。实际R220两镜像被中断的PG/请求诊断逐字节重放，均保留failed/interrupted/计数/原文件并因不足600秒拒绝；不将替身流程当成新的实际信号资格。失败引擎区间只用于诊断覆盖，不填入业务通过区间。

15项只读/拒绝检查核对冻结源码、计划、历史失败、所有资格和身份，缺显式执行标记不得建工作namespace。首个后台预检启动器存在换行转义语法错误，在执行预检前即退出；其PID确认不存在、未产生worker，原脚本/日志保持。新独立启动器在写入与运行前编译精确生成内容，实际预检退出0、两进程均不存在，完整记录见接入JSON。

## 原任务仍未完成

R203备库停库超过30秒、7次API内部超时和原生最终诊断缺失的原失败保持。R235接入允许取得更多证据，不自行证明资源策略或数据库问题已修复。两条真实七天任务、原正式24h+24h对照及其后置、ARM厂商业务和独立物理多设备等原52任务继续，不能凭短资格、预发布包或绿色CI宣布稳定1.0。


[R235完整压力终态](testing-business-pressure-final-wait-failure.md)已确认失败并清理：DBS实际600.292秒、SQL1/API5错（HIS未执行），13局部/11区间及引擎10内容检查不抵消业务失败。新诊断取得419请求/601PG样本、600线程样本；SQL对应5个LWLock/WALWrite样本，36个D样本均为DBS.log的write/XFS等待，5次原生API超时各重叠4个D样本。因果仍待设备/限额/日志关系核对；原预算/旧失败/52项和长期要求保持。
