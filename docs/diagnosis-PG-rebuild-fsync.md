# 重建失败：PID 文件 fsync 等待 XFS 写回

[准确终态分析](test-results-PG-rebuild-process.json)和[八份原件及只读查询](test-evidence-PG-rebuild-process.json.gz)已归档。独立DBS20诊断格失败，原36项只记录11项通过、25项未执行；三次启动只创建两次，首次61.409秒就绪，重建未过原300秒。实际原UID liveness两次成功不能代替SQL/API。此项不替代原四格144项失败。

独立观察器保留87次采样、114条postgres进程记录，涉及两个不同时刻的PostgreSQL启动进程；这些记录均为D状态、syscall74/fsync FD3、folio_wait_writeback→xfs_file_fsync。时间范围是重建后20.44至431.95秒，不能把离散采样说成完整无间断跟踪。观察器无错误，最终因目标叶消失退出。

在重建后225.70/235.71秒的另两次只读查询中，对第一进程PID/startticks及自身cgroup重新核验；FD3的设备号/ inode与该夹具真实postgresql/pgdata/postmaster.pid完全相等，文件45字节，fdinfo位置45。只读取元数据，没有打开或消费FD内容，也没有读取应用内存或环境。故能确认该进程当时卡在自己的PID文件fsync，不能说是在执行数据库SQL或因业务内存达到high。

同窗口实际io.max为设备253:0 rbps12554471/wbps7746597/riops27/wiops11，均为此次首次自动三样本中位数的20%，重建前profile摘要保持。10.013秒内该叶设备写IO增100、写字节增8011776，即约9.987 IOPS、0.763MiB/s；小于7.388MiB/s写带宽上限。file_writeback约414.625MiB、file_dirty约89.277MiB，memory.current约720MiB，pgscan/pgsteal均0。IO统计是整个自身cgroup，不能当成PID文件的专属IO或宿主总IO；两个内存计数不能擅自相加当独立总量。

这为低IOPS额度下大量写回影响启动fsync提供强线索，但没有解除限额做A/B实验，仍不声称IOPS是唯一原因。解包命令几秒返回也不证明缓冲写已经落盘。当前产品仍按原四轴设置，原profile/资源/数据库/门槛均未变。

上游[PostgreSQL14.19启动源码](https://github.com/postgres/postgres/blob/REL_14_19/src/backend/postmaster/postmaster.c)在创建数据目录锁后才进行后续预加载、共享资源及日志收集初始化。这只能帮助理解为什么尚无新日志，厂商二进制未与上游源码逐字节比对；实际等待点以本次内核栈和FD元数据为准。

用户选择待定：为保持一个io_percent，已询问默认百分比是否只表达标定读写带宽，IOPS留给手动模式；另一选择是保留带宽和IOPS四轴同时按百分比限制并接受明显变慢。此为语义选择，不是已实现变更，也不会用新口径改写旧失败。三项独立百分比、memory.high、各默认20及只控制本容器保持。

节点12:36UTC独立复核：原runner/观察器/驱动均消失，登记48个进程实例、两个已创建父叶及本namespace均清理。八份387429字节原件按冻结源/计划/索引和逐文件摘要验证下载。一次完整清理查询传输超时后使用相同终态摘要的较小只读查询复核，未重启任务。preview.4发布附件未变，稳定1.0仍未满足条件。
