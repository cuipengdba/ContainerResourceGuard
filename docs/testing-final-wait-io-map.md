# R235 失败后的真实路径与设备核对

[只读结果](test-results-final-wait-io-map.json)保留三次原始观察。两角色的DBS.log、真实PGDATA、pg_wal及basebackup均在同一XFS文件系统253:0（/dev/mapper/almalinux-root）；sysfs链为dm-0 → sda2(8:2) → sda(8:0)。这是同一后端，不能把253:0与8:0当成两块独立设备或相加统计，仍不满足原独立物理多设备验收。

第一步曾探测postgresql/data，目录不存在。随后读取原Pod的PGDATA及有界目录清单，确认真实值为/opt/postgresql/pgdata、目录含PG_VERSION，再对pgdata/pg_wal重新核对；**不得将错误猜测路径的不存在说成数据库目录不存在**，也不凭同一父目录替代实际WAL路径检查。若后续扩展PG线程的FD诊断，必须使用这个真实路径构造白名单；当前冻结R235观察的是API进程，已捕获的DBS.log路径不依赖旧/data猜测。

原IO profile摘要00e35e…保持，方法direct-sync-qdepth1-seq1m-random4k，三次每阶段3秒的中位数为读64700080B/s、写37470104B/s、4KiB随机读83IOPS/写135IOPS；本轮io_percent=100读回这些基准硬上限。这里的100%是此标定结果，不代表无上限，也不证明在混合业务、写回、备份竞争下仍满足延迟要求。未重新标定、改profile、队列调度器或控制文件。

现时sda队列报告mq-deadline、rotational=1、max_sectors_kb=256、write-through；缺失的dm/分区队列属性明确unknown。它们是失败后15:09:23Z的只读快照，不证明错误发生时的队列深度、介质饱和或限流根因，不将当前diskstats当成历史时间序列。

[PostgreSQL14官方等待事件说明](https://www.postgresql.org/docs/14/monitoring-stats.html#WAIT-EVENT-TABLE)将LWLock/WALWrite描述为等待WAL缓冲写入磁盘。实际R235请求窗口的5个样本只证明该等待，未识别其持有者，也不能把LWLock/WALWrite与IO/WALWrite、普通行锁混用。后续定位应同时记录原设备上的每秒提交计数、业务日志等待与WAL等待，再以单一变量冻结诊断对照，维持原数据/负载/时限及失败历史；不能临时放宽原验收配额或改变业务日志功能来宣布通过。

两角色原配置、profile原缺省状态与已发布ELF再次核对保持；本次没有新压测、SQL、进程信号或控制写入。原失败及全部稳定版条件继续。
