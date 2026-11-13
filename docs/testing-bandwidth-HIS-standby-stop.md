# 默认20%完整业务：HISDBS备用库停库日志补充

本次仅在原隔离fixture退出后读取固定日志文件，不改额度、PG、超时，不重启或重试。与[原完整业务终态](testing-bandwidth-default20-full600-terminal.md)同一job/plan/协调器哈希，另增7份完整文件、10380字节，不修改原22文件导出索引。

日志显示备用库容器内PID5029在2026-11-14 01:54:58.439 CST收到fast shutdown，01:55:30.136记录数据库完全关闭，相差31.697秒，仍超过原pg_ctl 30秒预算。checkpointer PID5409写14781个buffer，restartpoint总25.879秒，其中sync20.962秒，单文件最长11.501秒。独立恢复实例随后在约0.362秒内完成关闭，与超时备用库不是同一进程。

这是关库及同步耗时的直接证据，不能单独证明IO/cgroup因果。原16项记录/14通过/2失败、HIS native343.329秒中断及SQL18/API5错误均保留；不把最终退出当作30秒内成功，也不据此放宽门槛。

[绑定与资格结果](test-results-bandwidth-HIS-standby-stop.json)、[7份完整准确原件](test-evidence-bandwidth-HIS-standby-stop.json.gz)。
